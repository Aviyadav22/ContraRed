import pytest

@pytest.mark.asyncio
async def test_create_playbook(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    response = await client.post("/api/v1/playbooks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Playbook", "description": "A test playbook"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Playbook"

@pytest.mark.asyncio
async def test_list_playbooks(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    await client.post("/api/v1/playbooks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Playbook", "description": "Test"},
    )
    response = await client.get("/api/v1/playbooks/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_playbook_requires_auth(client):
    response = await client.get("/api/v1/playbooks/")
    assert response.status_code == 401
