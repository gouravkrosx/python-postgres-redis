# test_app.py

import json
import pytest
from aiohttp.test_utils import AioHTTPTestCase
from unittest import mock

import os

# Mock environment variables if needed
os.environ["REDIS_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "postgres://user:password@localhost:5432/mydb"

class TestApp(AioHTTPTestCase):
    async def get_application(self):
        # Import inside the method to ensure it's using the same event loop
        from app import create_app

        # Create the app with register_db=False to prevent database initialization
        app = create_app(register_db=False)

        # Mock the Redis client and attach it to the app
        self.redis_client_mock = mock.AsyncMock()
        app["redis_client"] = self.redis_client_mock

        return app

    @mock.patch("app.Item")
    async def test_get_item_cache_hit(self, mock_item):
        # Set up the Redis client mock to return cached data
        cached_item = {"id": "1", "name": "Cached Item", "description": "Cached Description"}
        self.redis_client_mock.get.return_value = json.dumps(cached_item)

        resp = await self.client.request("GET", "/items/1")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"data": cached_item}

        # Ensure Redis get was called
        self.redis_client_mock.get.assert_awaited_with("item:1")
        mock_item.get_or_none.assert_not_called()

    @mock.patch("app.Item")
    async def test_get_item_cache_miss_item_found(self, mock_item):
        # Redis cache miss
        self.redis_client_mock.get.return_value = None

        # Mock Item.get_or_none to return an item
        mock_item_instance = mock.Mock()
        mock_item_instance.id = "1"
        mock_item_instance.name = "Test Item"
        mock_item_instance.description = "Test Description"

        # Mock get_or_none as an AsyncMock
        mock_item.get_or_none = mock.AsyncMock(return_value=mock_item_instance)

        resp = await self.client.request("GET", "/items/1")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"data": {"id": "1", "name": "Test Item", "description": "Test Description"}}

        # Ensure Redis set was called
        self.redis_client_mock.set.assert_awaited_with("item:1", mock.ANY)

    @mock.patch("app.Item")
    async def test_get_item_cache_miss_item_not_found(self, mock_item):
        # Redis cache miss
        self.redis_client_mock.get.return_value = None

        # Mock get_or_none as an AsyncMock returning None
        mock_item.get_or_none = mock.AsyncMock(return_value=None)

        resp = await self.client.request("GET", "/items/1")
        assert resp.status == 404
        data = await resp.json()
        assert data == {"error": "Item not found"}

    @mock.patch("app.Item")
    async def test_get_all_items_cache_hit(self, mock_item):
        # Set up the Redis client mock to return cached data
        cached_items = [{"id": "1", "name": "Cached Item", "description": "Cached Description"}]
        self.redis_client_mock.get.return_value = json.dumps(cached_items)

        resp = await self.client.request("GET", "/items")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"data": cached_items}

        # Ensure Redis get was called
        self.redis_client_mock.get.assert_awaited_with("items:all")
        mock_item.all.assert_not_called()

    @mock.patch("app.Item")
    async def test_get_all_items_cache_miss(self, mock_item):
        # Redis cache miss
        self.redis_client_mock.get.return_value = None

        # Mock Item.all() to return a list of items
        mock_item_instance = mock.Mock()
        mock_item_instance.id = "1"
        mock_item_instance.name = "Test Item"
        mock_item_instance.description = "Test Description"

        # Mock all() as an AsyncMock
        mock_item.all = mock.AsyncMock(return_value=[mock_item_instance])

        resp = await self.client.request("GET", "/items")
        assert resp.status == 200
        data = await resp.json()
        expected_data = {"data": [{"id": "1", "name": "Test Item", "description": "Test Description"}]}
        assert data == expected_data

        # Ensure Redis set was called
        self.redis_client_mock.set.assert_awaited_with("items:all", mock.ANY)

    @mock.patch("app.Item")
    async def test_create_item(self, mock_item):
        # Mock Item.create() to return a new item
        mock_item_instance = mock.Mock()
        mock_item_instance.id = "1"
        mock_item_instance.name = "New Item"

        # Mock create() as an AsyncMock
        mock_item.create = mock.AsyncMock(return_value=mock_item_instance)

        resp = await self.client.request(
            "POST", "/items", json={"name": "New Item", "description": "New Description"}
        )
        assert resp.status == 201
        data = await resp.json()
        assert data == {"id": "1", "name": "New Item"}

        # Ensure Redis delete was called
        self.redis_client_mock.delete.assert_awaited_with("items:all")

    @mock.patch("app.Item")
    async def test_update_item_found(self, mock_item):
        # Mock Item.get_or_none() to return an existing item
        mock_item_instance = mock.Mock()
        mock_item_instance.id = "1"
        mock_item_instance.name = "Old Name"
        mock_item_instance.description = "Old Description"

        # Mock get_or_none as an AsyncMock
        mock_item.get_or_none = mock.AsyncMock(return_value=mock_item_instance)
        # Mock save() as an AsyncMock
        mock_item_instance.save = mock.AsyncMock()

        resp = await self.client.request(
            "PUT", "/items/1", json={"name": "Updated Name", "description": "Updated Description"}
        )
        assert resp.status == 200
        data = await resp.json()
        assert data == {"message": "Item updated"}

        # Ensure Redis operations were called
        self.redis_client_mock.set.assert_awaited_with("item:1", mock.ANY)
        self.redis_client_mock.delete.assert_awaited_with("items:all")

    @mock.patch("app.Item")
    async def test_update_item_not_found(self, mock_item):
        # Mock get_or_none as an AsyncMock returning None
        mock_item.get_or_none = mock.AsyncMock(return_value=None)

        resp = await self.client.request(
            "PUT", "/items/1", json={"name": "Updated Name", "description": "Updated Description"}
        )
        assert resp.status == 404
        data = await resp.json()
        assert data == {"error": "Item not found"}

    @mock.patch("app.Item")
    async def test_delete_item_found(self, mock_item):
        # Mock Item.get_or_none() to return an existing item
        mock_item_instance = mock.Mock()
        mock_item_instance.id = "1"

        # Mock get_or_none as an AsyncMock
        mock_item.get_or_none = mock.AsyncMock(return_value=mock_item_instance)
        # Mock delete() as an AsyncMock
        mock_item_instance.delete = mock.AsyncMock()

        resp = await self.client.request("DELETE", "/items/1")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"message": "Item deleted"}

        # Ensure Redis delete was called
        self.redis_client_mock.delete.assert_any_await("item:1")
        self.redis_client_mock.delete.assert_any_await("items:all")

    @mock.patch("app.Item")
    async def test_delete_item_not_found(self, mock_item):
        # Mock get_or_none as an AsyncMock returning None
        mock_item.get_or_none = mock.AsyncMock(return_value=None)

        resp = await self.client.request("DELETE", "/items/1")
        assert resp.status == 404
        data = await resp.json()
        assert data == {"error": "Item not found"}
