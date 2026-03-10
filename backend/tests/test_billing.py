import pytest

@pytest.mark.asyncio
async def test_list_plans(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    response = await client.get("/api/v1/billing/plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) >= 2

@pytest.mark.asyncio
async def test_get_subscription(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    response = await client.get("/api/v1/billing/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
