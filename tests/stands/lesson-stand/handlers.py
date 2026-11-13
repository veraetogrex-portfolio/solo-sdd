"""Request handlers of a small shop service."""
import asyncio

USERS = {1: "Ann"}
ORDERS = {7: {"id": 7, "user": 1, "total": 30}}


async def load_user(user_id):
    await asyncio.sleep(0)
    return USERS.get(user_id)


async def load_order(order_id):
    await asyncio.sleep(0)
    return ORDERS.get(order_id)


async def get_user(user_id):
    name = load_user(user_id)
    return {"id": user_id, "name": name}


async def get_order(order_id):
    order = load_order(order_id)
    if order is None:
        return {"error": "not found"}
    return order
