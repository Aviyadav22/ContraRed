"""Authentication scope and JWT claim regression tests."""

import pytest

from app.core.security import create_access_token, decode_token
from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_mfa_setup_token_cannot_access_general_authenticated_route(
    client,
    test_user_data,
):
    access_token = await register_and_login(client, test_user_data)
    access_claims = decode_token(access_token)
    assert access_claims is not None

    setup_token = create_access_token({
        "sub": str(access_claims.user_id),
        "email": access_claims.email,
        "role": access_claims.role,
        "org_id": access_claims.organization_id,
        "type": "mfa_setup",
        "mfa_setup_required": True,
    })
    setup_claims = decode_token(setup_token, expected_type="mfa_setup")
    assert setup_claims is not None
    assert setup_claims.token_type == "mfa_setup"

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {setup_token}"},
    )

    assert response.status_code == 401
    assert "only be used for MFA endpoints" in response.json()["detail"]
