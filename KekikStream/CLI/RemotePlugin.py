# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, ExtractResult
import urllib.parse

class RemotePlugin(PluginBase):
    def __init__(self, name: str, base_api_url: str, plugin_data: dict, ex_manager=None):
        # We assign instance variables. We'll also ensure __class__ isn't blindly overwritten.
        # However, PluginBase reads some from self, so assigning to self is usually enough unless it explicitly checks class vars.
        self.name        = name
        self.language    = plugin_data.get("language", "tr")
        self.main_url    = plugin_data.get("main_url", "")
        self.favicon     = plugin_data.get("favicon", "")
        self.description = plugin_data.get("description", "")
        self.main_page   = plugin_data.get("main_page", {})

        self.base_api_url = base_api_url

        # Sunucu kendi cache mekanizmasını kullanacağı için lokal cache yapmaya gerek yok
        self.method_cache_ttl = 0
        self.cached_methods   = ()

        super().__init__(ex_manager=ex_manager)

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        url      = urllib.parse.unquote_plus(url)
        category = urllib.parse.unquote_plus(category)
        req      = await self.httpx.get(
            f"{self.base_api_url}/get_main_page",
            params  = {"plugin": self.name, "page": page, "encoded_url": url, "encoded_category": category},
            timeout = 5
        )
        req.raise_for_status()
        data = req.json().get("result", [])
        return [MainPageResult(**item) for item in data] if data else []

    async def search(self, query: str) -> list[SearchResult]:
        query = urllib.parse.unquote_plus(query)
        req   = await self.httpx.get(
            f"{self.base_api_url}/search",
            params  = {"plugin": self.name, "query": query},
            timeout = 5
        )
        req.raise_for_status()
        data = req.json().get("result", [])
        return [SearchResult(**item) for item in data] if data else []

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo | None:
        url = urllib.parse.unquote_plus(url)
        req = await self.httpx.get(
            f"{self.base_api_url}/load_item",
            params  = {"plugin": self.name, "encoded_url": url},
            timeout = 5
        )
        req.raise_for_status()
        data = req.json().get("result")
        if not data:
            return None

        if "episodes" in data:
            return SeriesInfo(**data)
        return MovieInfo(**data)

    async def load_links(self, url: str) -> list[ExtractResult]:
        url = urllib.parse.unquote_plus(url)
        req = await self.httpx.get(
            f"{self.base_api_url}/load_links",
            params  = {"plugin": self.name, "encoded_url": url},
            timeout = 5
        )
        req.raise_for_status()
        data = req.json().get("result", [])
        return [ExtractResult(**item) for item in data] if data else []
