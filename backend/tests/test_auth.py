import pytest
from tests.conftest import register_and_login

@pytest.mark.asyncio
async def test_register_success(client, test_user_data):
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]

@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user_data):
    await client.post("/api/v1/auth/register", json=test_user_data)
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    # Anti-enumeration: returns 201 for duplicates too (AUDIT FIX H2)
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_login_success(client, test_user_data):
    await client.post("/api/v1/auth/register", json=test_user_data)
    response = await client.post("/api/v1/auth/login", data={
        "username": test_user_data["email"],
        "password": test_user_data["password"],
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user_data):
    await client.post("/api/v1/auth/register", json=test_user_data)
    response = await client.post("/api/v1/auth/login", data={
        "username": test_user_data["email"],
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_authenticated(client, test_user_data):
    token = await register_and_login(client, test_user_data)
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == test_user_data["email"]

@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_password_validation_weak(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "weak@test.com",
        "password": "weak",
        "name": "Weak User",
    })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_change_password(client, test_user_data):
    token = await register_and_login(client, test_user_data)
    response = await client.post("/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": test_user_data["password"], "new_password": "NewPassword456!"},
    )
    assert response.status_code == 200
