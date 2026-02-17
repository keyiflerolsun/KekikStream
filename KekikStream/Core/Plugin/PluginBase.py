# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI                       import konsol
from abc                          import ABC, abstractmethod
from cloudscraper                 import CloudScraper
from httpx                        import AsyncClient
from .PluginModels                import MainPageResult, SearchResult, MovieInfo, SeriesInfo
from ..Media.MediaHandler         import MediaHandler
from ..Extractor.ExtractorManager import ExtractorManager
from ..Extractor.ExtractorModels  import ExtractResult, Subtitle
from urllib.parse                 import urljoin
import asyncio

class PluginBase(ABC):
    name        = "Plugin"
    language    = "tr"
    main_url    = "https://example.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "No description provided."

    main_page   = {}

    async def url_update(self, new_url: str):
        self.favicon   = self.favicon.replace(self.main_url, new_url)
        self.main_page = {url.replace(self.main_url, new_url): category for url, category in self.main_page.items()}
        self.main_url  = new_url

    def __init__(self, proxy: str | dict | None = None, ex_manager: str | ExtractorManager = "Extractors"):
        # cloudscraper - for bypassing Cloudflare
        self.cloudscraper = CloudScraper()
        if proxy:
            self.cloudscraper.proxies = proxy if isinstance(proxy, dict) else {"http": proxy, "https": proxy}

        # Convert dict proxy to string for httpx if necessary
        httpx_proxy = proxy
        if isinstance(proxy, dict):
            httpx_proxy = proxy.get("https") or proxy.get("http")

        # httpx - lightweight and safe for most HTTP requests
        self.httpx = AsyncClient(
            timeout          = 10,
            follow_redirects = True,
            proxy            = httpx_proxy
        )
        self.httpx.headers.update(self.cloudscraper.headers)
        self.httpx.cookies.update(self.cloudscraper.cookies)
        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        self.media_handler = MediaHandler()

        # If an instance is passed, use it; otherwise create a new one
        if isinstance(ex_manager, ExtractorManager):
            self.ex_manager = ex_manager
        else:
            self.ex_manager = ExtractorManager(extractor_dir=ex_manager)

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
                    url="https://example.com/video.m3u8",
                    name="HDFilmCehennemi | 1080p TR Dublaj"
                )
            ]
        """
        pass

    # ========================
    # YARDIMCI METOTLAR
    # ========================

    def collect_results(self, results: list[ExtractResult], data: ExtractResult | list[ExtractResult] | None):
        """
        extract() dönüşünü (tekil, liste veya None) sonuç listesine ekler.
        28+ plugin'de tekrar eden pattern'i ortadan kaldırır.

        Kullanım:
            data = await self.extract(url)
            self.collect_results(results, data)
        """
        if data:
            results.extend(data if isinstance(data, list) else [data])

    @staticmethod
    def deduplicate(results: list[ExtractResult], key: str = "url") -> list[ExtractResult]:
        """
        Sonuç listesinden tekrar eden URL'leri kaldırır.

        Args:
            results: ExtractResult listesi
            key: Deduplicate anahtarı ("url" veya "url+name")
        """
        seen    = set()
        uniques = []
        for res in results:
            k = (res.url, res.name) if key == "url+name" else res.url
            if k and k not in seen:
                uniques.append(res)
                seen.add(k)
        return uniques

    @staticmethod
    async def gather_with_limit(tasks: list, limit: int = 5):
        """
        Semaphore ile rate-limited paralel çalıştırma.

        Kullanım:
            tasks   = [self.extract(url) for url in urls]
            results = await self.gather_with_limit(tasks, limit=5)
        """
        sem = asyncio.Semaphore(limit)
        async def limited(coro):
            async with sem:
                return await coro
        return await asyncio.gather(*(limited(t) for t in tasks))

    async def async_cf_get(self, url: str, **kwargs):
        """
        cloudscraper.get() için async wrapper.
        Cloudflare korumalı sitelerde kullanılır.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.cloudscraper.get(url, **kwargs))

    async def async_cf_post(self, url: str, **kwargs):
        """
        cloudscraper.post() için async wrapper.
        Cloudflare korumalı sitelerde kullanılır.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.cloudscraper.post(url, **kwargs))

    @staticmethod
    def new_subtitle(url: str, name: str = "Altyazı") -> Subtitle:
        """Hızlı Subtitle nesnesi oluşturur."""
        return Subtitle(name=name, url=url)

    @staticmethod
    def sync_subtitles(results: list[ExtractResult]) -> list[ExtractResult]:
        """
        Tüm ExtractResult'lardaki altyazıları birleştirir ve her sonuca dağıtır.

        - Aynı URL'ye sahip altyazılar tekrarlanmaz.
        - Aynı isme sahip farklı URL'ler "İsim", "İsim (2)" şeklinde numaralandırılır.
        - Engine tarafından her load_links çağrısından sonra otomatik uygulanır.
        """
        if not results:
            return results

        # 1. Tüm altyazıları URL'ye göre topla (dedup)
        seen_urls: dict[str, Subtitle] = {}
        for res in results:
            for sub in res.subtitles:
                if sub.url not in seen_urls:
                    seen_urls[sub.url] = sub

        if not seen_urls:
            return results

        # 2. Aynı isimli farklı URL'leri numaralandır
        merged     = list(seen_urls.values())
        name_count: dict[str, int] = {}
        for sub in merged:
            name_count[sub.name] = name_count.get(sub.name, 0) + 1

        name_idx: dict[str, int] = {}
        final_subs: list[Subtitle] = []
        for sub in merged:
            if name_count[sub.name] > 1:
                idx              = name_idx.get(sub.name, 0) + 1
                name_idx[sub.name] = idx
                label            = sub.name if idx == 1 else f"{sub.name} ({idx})"
                final_subs.append(Subtitle(name=label, url=sub.url))
            else:
                final_subs.append(sub)

        # 3. Birleşik listeyi tüm sonuçlara ata
        for res in results:
            res.subtitles = list(final_subs)

        return results

    async def close(self):
        """Close HTTP client."""
        await self.httpx.aclose()

    def fix_url(self, url: str) -> str:
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url.replace("\\", "")

        url = f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)
        return url.replace("\\", "")

    async def extract(
        self,
        url: str,
        referer: str = None,
        prefix: str | None = None,
        name_override: str | None = None
    ) -> ExtractResult | list[ExtractResult] | None:
        """
        Extractor ile video URL'sini çıkarır.

        Args:
            url: Iframe veya video URL'si
            referer: Referer header (varsayılan: plugin main_url)
            prefix: İsmin başına eklenecek opsiyonel etiket (örn: "Türkçe Dublaj")
            name_override: İsmi tamamen değiştirecek opsiyonel etiket (Extractor adını ezer)

        Returns:
            ExtractResult: Extractor sonucu (name prefix ile birleştirilmiş) veya None

        Extractor bulunamadığında veya hata oluştuğunda uyarı verir.
        """
        if referer is None:
            referer = f"{self.main_url}/"

        extractor = self.ex_manager.find_extractor(url)
        if not extractor:
            konsol.log(f"[magenta][?] {self.name} » Extractor bulunamadı: {url}")
            return None

        try:
            data = await extractor.extract(url, referer=referer)

            # Liste ise her bir öğe için prefix/override ekle
            if isinstance(data, list):
                for item in data:
                    if name_override:
                        item.name = name_override
                    elif prefix and item.name:
                        if item.name.lower() in prefix.lower():
                            item.name = prefix
                        else:
                            item.name = f"{prefix} | {item.name}"
                return data

            # Tekil öğe ise
            if name_override:
                data.name = name_override
            elif prefix and data.name:
                if data.name.lower() in prefix.lower():
                    data.name = prefix
                else:
                    data.name = f"{prefix} | {data.name}"

            return data
        except Exception as hata:
            konsol.log(f"[red][!] {self.name} » Extractor hatası ({extractor.name}): {hata}")
            return None

    async def play(self, **kwargs):
        """
        Varsayılan oynatma metodu.
        Tüm pluginlerde ortak kullanılır.
        """
        extract_result = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)
