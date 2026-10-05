# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .PluginModels                import MainPageResult, SearchResult, MovieInfo, SeriesInfo
from .PluginCache                 import PluginCacheMixin
from .PluginEnrichment            import PluginEnrichmentMixin
from .PluginResults               import PluginResultsMixin
from .PluginExtraction            import PluginExtractionMixin
from ..Media.MediaHandler         import MediaHandler
from ..Extractor.ExtractorManager import ExtractorManager
from ..Extractor.ExtractorModels  import ExtractResult
from ..Helpers.FallbackClients    import FallbackHTTPX, FallbackCF
from ..Helpers                    import fix_url
from abc                          import ABC, abstractmethod
import httpx, curl_cffi


class PluginBase(PluginCacheMixin, PluginEnrichmentMixin, PluginResultsMixin, PluginExtractionMixin, ABC):
    name        = "Plugin"
    language    = "tr"
    main_url    = "https://example.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "No description provided."

    main_page                = {}
    method_cache_ttl         = 3600
    method_cache_max_entries = 512
    cached_methods           = ("search", "get_main_page", "load_item")

    subtitle_processor = None
    result_processor   = None

    async def url_update(self, new_url: str):
        self.favicon   = self.favicon.replace(self.main_url, new_url)
        self.main_page = {url.replace(self.main_url, new_url) : category for url, category in self.main_page.items()}
        self.main_url  = new_url
        if hasattr(self, "_cf_session"):
            self._cf_session.main_url = new_url
        if hasattr(self, "httpx"):
            self.httpx.main_url = new_url

    def __init__(self, proxy: str | dict | None = None, ex_manager: str | ExtractorManager = "Extractors"):
        # curl_cffi - for bypassing Cloudflare TLS/HTTP2 fingerprints
        self._cf_session          = FallbackCF(impersonate="firefox", timeout=3)
        self._cf_session.main_url = self.main_url
        self._cf_session.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        if proxy:
            proxy_str                = proxy if isinstance(proxy, str) else (proxy.get("https") or proxy.get("http"))
            self._cf_session.proxies = {"http" : proxy_str, "https" : proxy_str}

            cf_fallback = curl_cffi.AsyncSession(impersonate="firefox", timeout=3)
            cf_fallback.headers.update(self._cf_session.headers)
            self._cf_session.set_fallback(cf_fallback)

        # Convert dict proxy to string for httpx if necessary
        httpx_proxy = proxy
        if isinstance(proxy, dict):
            httpx_proxy = proxy.get("https") or proxy.get("http")

        # httpx - lightweight and safe for most HTTP requests
        self.httpx = FallbackHTTPX(
            timeout          = 3,
            follow_redirects = True,
            proxy            = httpx_proxy,
        )
        self.httpx.main_url = self.main_url
        self.httpx.headers.update(self._cf_session.headers)
        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        if httpx_proxy:
            httpx_fallback = httpx.AsyncClient(timeout=3, follow_redirects=True)
            httpx_fallback.headers.update(self.httpx.headers)
            self.httpx.set_fallback(httpx_fallback)

        self.media_handler = MediaHandler()

        # If an instance is passed, use it; otherwise create a new one
        if isinstance(ex_manager, ExtractorManager):
            self.ex_manager = ex_manager
        else:
            self.ex_manager = ExtractorManager(extractor_dir=ex_manager)

        self.failed_extractions : list[dict] = []
        self._last_loaded_item               = None

        # Subclass'ın metotlarını dinamik olarak sarmalla (otomatik TMDB & Altyazı zenginleştirmesi)
        self._wrap_plugin_methods()

        self._cache_namespace = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self._setup_default_method_caches()

    @abstractmethod
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        """Ana sayfadaki popüler içerikleri döndürür."""
        pass

    @abstractmethod
    async def search(self, query: str) -> list[SearchResult]:
        """Kullanıcı arama sorgusuna göre sonuç döndürür."""
        pass

    @abstractmethod
    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        """Bir medya öğesi hakkında detaylı bilgi döndürür."""
        pass

    @abstractmethod
    async def load_links(self, url: str) -> list[ExtractResult]:
        """
        Bir medya öğesi için oynatma bağlantılarını döndürür.

        Args:
            url: Medya URL'si

        Returns:
            ExtractResult listesi, her biri şu alanları içerir:
            - url (str, zorunlu): Video URL'si
            - name (str, zorunlu): Gösterim adı (tüm bilgileri içerir)
            - referer (str, opsiyonel): Referer header
            - subtitles (list[Subtitle], opsiyonel): Altyazı listesi

        Example:
            [
                ExtractResult(
                    url  = "https://example.com/video.m3u8",
                    name = "HDFilmCehennemi | 1080p TR Dublaj"
                )
            ]
        """
        pass

    async def async_cf_get(self, url: str, **kwargs):
        """
        curl_cffi.AsyncSession ile Cloudflare bypasslı GET isteği.
        Cloudflare korumalı sitelerde kullanılır.
        """
        return await self._cf_session.get(url, **kwargs)

    async def async_cf_post(self, url: str, **kwargs):
        """
        curl_cffi.AsyncSession ile Cloudflare bypasslı POST isteği.
        Cloudflare korumalı sitelerde kullanılır.
        """
        return await self._cf_session.post(url, **kwargs)

    async def close(self):
        """Close HTTP client."""
        await self.httpx.aclose()
        await self._cf_session.close()

    def fix_url(self, url: str) -> str:
        return fix_url(url, self.main_url)

    async def play(self, **kwargs):
        """
        Varsayılan oynatma metodu.
        Tüm pluginlerde ortak kullanılır.
        """
        extract_result           = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)
