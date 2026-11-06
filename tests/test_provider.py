import unittest
import asyncio
from providers.generic import GenericProvider

class TestGenericProvider(unittest.TestCase):
    def setUp(self):
        self.provider = GenericProvider()

    def test_can_handle(self):
        async def run_test():
            self.assertTrue(await self.provider.can_handle("http://example.com/video.mp4"))
            self.assertTrue(await self.provider.can_handle("http://example.com/stream.m3u8"))
            self.assertFalse(await self.provider.can_handle("http://example.com/page.html"))

        asyncio.run(run_test())

    def test_get_metadata(self):
        async def run_test():
            meta = await self.provider.get_metadata("http://example.com/video.mp4")
            self.assertEqual(meta["title"], "video.mp4")
            self.assertEqual(meta["provider"], "Generic")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
