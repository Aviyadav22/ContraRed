import pytest

@pytest.mark.asyncio
async def test_analyze_requires_auth(client):
    response = await client.post("/api/v1/documents/analyze", json={"text": "test"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_analyze_text_too_long(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    long_text = "x" * 600000
    response = await client.post("/api/v1/documents/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": long_text},
    )
    assert response.status_code == 422  # Pydantic validation error for max_length

@pytest.mark.asyncio
async def test_analyze_file_too_large(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    # Create a file that exceeds 10MB
    large_content = b"x" * (11 * 1024 * 1024)
    response = await client.post("/api/v1/documents/analyze-file",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.docx", large_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 413

@pytest.mark.asyncio
async def test_analyze_file_invalid_format(client, test_user_data):
    reg = await client.post("/api/v1/auth/register", json=test_user_data)
    token = reg.json()["access_token"]
    response = await client.post("/api/v1/documents/analyze-file",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.docx", b"not a zip file", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
