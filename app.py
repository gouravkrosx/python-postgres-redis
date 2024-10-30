import os
from aiohttp import web
from models import Item
from tortoise.contrib.aiohttp import register_tortoise
import redis.asyncio as redis
import json
import time

# Get Redis host and database URL from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://user:password@localhost:5432/mydb")

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

async def get_item(request):
    item_id = request.match_info["id"]
    cached_item = await redis_client.get(f"item:{item_id}")

    if cached_item:
        return web.json_response({"data": json.loads(cached_item)}, status=200)

    item = await Item.get_or_none(id=item_id)
    if item:
        item_data = {"id": item.id, "name": item.name, "description": item.description}
        await redis_client.set(f"item:{item_id}", json.dumps(item_data))
        return web.json_response({"data": item_data}, status=200)

    return web.json_response({"error": "Item not found"}, status=404)

# async def get_all_items(request):
#     cached_items = await redis_client.get("items:all")
#     if cached_items:
#         return web.json_response({"data": json.loads(cached_items)}, status=200)

#     items = await Item.all().values("id", "name", "description")
#     items_list = list(items)
#     await redis_client.set("items:all", json.dumps(items_list))

#     return web.json_response({"data": items_list}, status=200)

async def get_all_items(request):
    cached_items = await redis_client.get("items:all")
    if cached_items:
        return web.json_response({"data": json.loads(cached_items)}, status=200)

    # Remove the .values() call and just return a list of items
    items = await Item.all()  # No need to call .values()
    items_list = [{"id": item.id, "name": item.name, "description": item.description} for item in items]

    await redis_client.set("items:all", json.dumps(items_list))
    return web.json_response({"data": items_list}, status=200)

async def create_item(request):
    data = await request.json()
    item = await Item.create(name=data["name"], description=data["description"])
    await redis_client.delete("items:all")
    return web.json_response({"id": item.id, "name": item.name}, status=201)

async def update_item(request):
    item_id = request.match_info["id"]
    data = await request.json()
    item = await Item.get_or_none(id=item_id)

    if not item:
        return web.json_response({"error": "Item not found"}, status=404)

    item.name = data["name"]
    item.description = data["description"]
    await item.save()
    item_data = {"id": item.id, "name": item.name, "description": item.description}
    await redis_client.set(f"item:{item_id}", json.dumps(item_data))
    await redis_client.delete("items:all")

    return web.json_response({"message": "Item updated"}, status=200)

async def delete_item(request):
    item_id = request.match_info["id"]
    item = await Item.get_or_none(id=item_id)

    if not item:
        return web.json_response({"error": "Item not found"}, status=404)

    await item.delete()
    await redis_client.delete(f"item:{item_id}")
    await redis_client.delete("items:all")

    return web.json_response({"message": "Item deleted"}, status=200)

app = web.Application()

# Register routes
app.router.add_get("/items/{id}", get_item)
app.router.add_get("/items", get_all_items)
app.router.add_post("/items", create_item)
app.router.add_put("/items/{id}", update_item)
app.router.add_delete("/items/{id}", delete_item)

# Register Tortoise ORM
register_tortoise(
    app,
    db_url=DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)

if __name__ == "__main__":
    print("Waiting for 5 seconds to ensure PostgreSQL is ready...")
    time.sleep(5)  # Blocking sleep to ensure the DB is up before starting
    web.run_app(app, host="0.0.0.0", port=8080)