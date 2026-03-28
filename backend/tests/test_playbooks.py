import pytest
from tests.conftest import register_and_login

@pytest.mark.asyncio
async def test_create_playbook_requires_admin(client, test_user_data):
    """REVIEWER role cannot create playbooks (requires playbook.admin permission)."""
    token = await register_and_login(client, test_user_data)
    response = await client.post("/api/v1/playbooks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Playbook", "description": "A test playbook"},
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_list_playbooks(client, test_user_data):
    token = await register_and_login(client, test_user_data)
    response = await client.get("/api/v1/playbooks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_playbook_requires_auth(client):
    response = await client.get("/api/v1/playbooks/")
    assert response.status_code == 401
