import unittest
import asyncio
from providers.net79 import Net79Provider
from providers.generic import GenericProvider
from providers.ott_drm import OTTDRMProvider
from providers.zee5 import Zee5Provider

class TestProviders(unittest.TestCase):
    def setUp(self):
        self.net79 = Net79Provider()
        self.generic = GenericProvider()
        self.drm = OTTDRMProvider()
        self.zee5 = Zee5Provider()

    def test_can_handle(self):
        async def run_test():
            self.assertTrue(await self.net79.can_handle("https://net79.cc/video/123"))
            self.assertTrue(await self.net79.can_handle("https://netmirror.app/watch/456"))
            self.assertTrue(await self.drm.can_handle("https://www.sonyliv.com/shows/karrle-tu-bhi-mohabbat-1790007858/..."))
            self.assertTrue(await self.drm.can_handle("https://www.hotstar.com/movies/..."))
            self.assertTrue(await self.zee5.can_handle("https://www.zee5.com/movies/details/abc/123"))
            self.assertTrue(await self.generic.can_handle("https://example.com/stream.m3u8"))
            self.assertTrue(await self.generic.can_handle("https://example.com/video.mp4"))
            self.assertFalse(await self.generic.can_handle("invalid-url"))

        asyncio.run(run_test())

    def test_net79_search(self):
        async def run_test():
            results = await self.net79.search("Panchayat")
            self.assertTrue(len(results) > 0)
            self.assertEqual(results[0]["title"], "Panchayat")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
