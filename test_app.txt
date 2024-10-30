import asyncio
import pytest
import pytest_asyncio
from aiohttp import web
from unittest.mock import AsyncMock, patch
from app import app

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a new event loop for the session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest_asyncio.fixture(autouse=True)
async def mock_tortoise_orm():
    """Mock the Tortoise ORM methods used in the app."""
    with patch("tortoise.Tortoise.init", new_callable=AsyncMock), \
         patch("tortoise.Tortoise.generate_schemas", new_callable=AsyncMock), \
         patch("tortoise.Tortoise.close_connections", new_callable=AsyncMock), \
         patch("tortoise.connection.ConnectionHandler.close_all", new_callable=AsyncMock), \
         patch("models.Item.create", new_callable=AsyncMock) as mock_create_item, \
         patch("models.Item.get_or_none", new_callable=AsyncMock) as mock_get_or_none, \
         patch("models.Item.all", new_callable=AsyncMock) as mock_all_items:

        # Mock item objects with the required attributes
        mock_item_1 = AsyncMock()
        mock_item_1.id = 1
        mock_item_1.name = "Item 1"
        mock_item_1.description = "Desc 1"

        mock_item_2 = AsyncMock()
        mock_item_2.id = 2
        mock_item_2.name = "Item 2"
        mock_item_2.description = "Desc 2"

        # Set the mocked ORM methods to return appropriate values
        mock_all_items.return_value = [mock_item_1, mock_item_2]
        mock_create_item.return_value = mock_item_1
        mock_get_or_none.side_effect = lambda id: mock_item_1 if id == "1" else None

        yield

@pytest_asyncio.fixture(autouse=True)
async def mock_redis_client():
    """Mock the Redis client methods used in the app."""
    with patch("app.redis_client", autospec=True) as mock_redis:
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=None)
        mock_redis.delete = AsyncMock(return_value=None)
        yield

@pytest_asyncio.fixture
async def client(aiohttp_client):
    """Create and return a test client for the app."""
    client = await aiohttp_client(app)
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_create_item(client):
    payload = {"name": "New Item", "description": "A new item"}
    response = await client.post("/items", json=payload)
    assert response.status == 201
    json_response = await response.json()
    assert json_response["id"] == 1
    assert json_response["name"] == "Item 1"

@pytest.mark.asyncio
async def test_get_item(client):
    response = await client.get("/items/1")
    assert response.status == 200
    json_response = await response.json()
    assert str(json_response["data"]["id"]) == '1'
    assert json_response["data"]["name"] == "Item 1"

    response = await client.get("/items/999")
    assert response.status == 404
    json_response = await response.json()
    assert json_response["error"] == "Item not found"

@pytest.mark.asyncio
async def test_get_all_items(client):
    response = await client.get("/items")
    assert response.status == 200  # Ensure the request succeeds
    json_response = await response.json()
    assert len(json_response["data"]) == 2
    assert json_response["data"][0]["name"] == "Item 1"
    assert json_response["data"][1]["name"] == "Item 2"

@pytest.mark.asyncio
async def test_update_item(client):
    payload = {"name": "Updated Item", "description": "Updated description"}
    response = await client.put("/items/1", json=payload)
    assert response.status == 200
    json_response = await response.json()
    assert json_response["message"] == "Item updated"

    response = await client.put("/items/999", json=payload)
    assert response.status == 404
    json_response = await response.json()
    assert json_response["error"] == "Item not found"

@pytest.mark.asyncio
async def test_delete_item(client):
    response = await client.delete("/items/1")
    assert response.status == 200
    json_response = await response.json()
    assert json_response["message"] == "Item deleted"

    response = await client.delete("/items/999")
    assert response.status == 404
    json_response = await response.json()
    assert json_response["error"] == "Item not found"