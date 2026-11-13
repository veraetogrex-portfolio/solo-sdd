import unittest

from handlers import get_order, get_user


class Handlers(unittest.IsolatedAsyncioTestCase):
    async def test_get_user(self):
        self.assertEqual(await get_user(1), {"id": 1, "name": "Ann"})

    async def test_get_order(self):
        self.assertEqual(await get_order(7), {"id": 7, "user": 1, "total": 30})


if __name__ == "__main__":
    unittest.main()
