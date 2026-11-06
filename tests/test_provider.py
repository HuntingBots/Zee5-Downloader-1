import unittest
import asyncio
from providers.net79 import Net79Provider

class TestNet79Provider(unittest.TestCase):
    def setUp(self):
        self.provider = Net79Provider()

    def test_can_handle(self):
        async def run_test():
            self.assertTrue(await self.provider.can_handle("https://net79.cc/video/123"))
            self.assertFalse(await self.provider.can_handle("https://example.com/video"))

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
