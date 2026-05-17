# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Extractor.ExtractorModels import ExtractResult
from urllib.parse                import urlparse
from curl_cffi.requests          import AsyncSession
import httpx, asyncio, time

class PlayabilityHelper:
    # İstemcileri (Client) sınıf seviyesinde tutuyoruz (Connection Pooling)
    _httpx_client = None
    _cf_session   = None

    # --- ÖNBELLEK (CACHE) SİSTEMİ ---
    _cache     = {}  # url -> (timestamp, (bool, str))
    _cache_ttl = 600  # Cache'te tutulma süresi (Saniye) - Şu an 10 Dakika
    _locks     = {}  # Aynı anda gelen aynı link isteklerini sıraya sokmak için

    @classmethod
    def _get_httpx(cls):
        """Bağlantıları açık tutan paylaşımlı HTTPX istemcisi"""
        if cls._httpx_client is None:
            limits            = httpx.Limits(max_keepalive_connections=20, max_connections=50)
            cls._httpx_client = httpx.AsyncClient(timeout=3.0, follow_redirects=True, verify=False, limits=limits)
        return cls._httpx_client

    @classmethod
    def _get_cf(cls):
        """Bağlantıları açık tutan paylaşımlı Cloudflare Bypass istemcisi"""
        if cls._cf_session is None:
            cls._cf_session = AsyncSession(impersonate="firefox", timeout=4.0)
        return cls._cf_session

    @classmethod
    async def is_url_playable(cls, link: ExtractResult) -> tuple[bool, str]:
        """URL'nin oynatılabilir olup olmadığını kontrol eder (Cache destekli)."""
        url = link.url
        if not url:
            return False, "URL boş"

        # 1. Önbellekte (Cache) varsa ve süresi dolmamışsa direkt sonucu dön
        now = time.time()
        if url in cls._cache:
            timestamp, result = cls._cache[url]
            if now - timestamp < cls._cache_ttl:
                return result

        # 2. Kilit (Lock) oluştur: Aynı link aynı anda gelirse çift istek atmasını engeller
        if url not in cls._locks:
            cls._locks[url] = asyncio.Lock()

        async with cls._locks[url]:
            # Kilidi beklerken başka bir işlem (örneğin extractor) sonucu bulup cache'e yazmış olabilir, tekrar kontrol edelim
            if url in cls._cache:
                timestamp, result = cls._cache[url]
                if time.time() - timestamp < cls._cache_ttl:
                    return result

            # 3. Cache'te yok, ağa bağlanıp kontrol et
            result = await cls._check_url_network(link)

            # 4. Sonucu önbelleğe kaydet (Başarısız olsa bile kaydederiz ki bozuk linke sürekli istek atılmasın)
            cls._cache[url] = (time.time(), result)

            # Hafıza şişmesini önlemek için işlem bitince kilidi temizleyebiliriz
            cls._locks.pop(url, None)

            return result

    @classmethod
    async def _check_url_network(cls, link: ExtractResult) -> tuple[bool, str]:
        """Asıl HTTP isteklerini yapan arka plan fonksiyonu"""
        url = link.url

        if "youtube.com" in url or "youtu.be" in url:
            return True, "YouTube Embed / Fragman"

        if not url.startswith(("http://", "https://")):
            return False, f"Geçersiz URL şeması: {url[:50]}"

        # Header hazırlama
        headers = {
            "Accept"          : "*/*",
            "Accept-Language" : "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent"      : link.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        if link.referer:
            # Hotlink koruması olan/Referer istemeyen sunucular için başlığı atla
            skip_referer = any(x in url.lower() for x in ["yandex", "googleusercontent", "twimg", "googleapis"])
            if not skip_referer:
                headers["Referer"] = link.referer
                try:
                    parsed = urlparse(link.referer)
                    if parsed.scheme and parsed.netloc:
                        headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
                except Exception:
                    pass

        if link.extra_headers:
            headers.update(link.extra_headers)

        httpx_client = cls._get_httpx()

        try:
            # 1. Hızlı HEAD isteğiyle kontrol et
            req_headers = headers.copy()
            req_headers["Range"] = "bytes=0-1024" # Videoların tamamını indirmeyi engeller

            response = await httpx_client.head(url, headers=req_headers)

            # HEAD Cloudflare dönerse GET ile zaman kaybetmeden hemen curl_cffi'a geç
            if response.status_code in [403, 503] or "cloudflare" in response.headers.get("server", "").lower():
                raise httpx.HTTPStatusError("Cloudflare / Access Blocked", request=response.request, response=response)

            if response.status_code in [200, 206]:
                content_type = response.headers.get("content-type", "").lower()
                if content_type and "html" not in content_type:
                    return True, f"HEAD Başarılı ({response.status_code}, {content_type})"

            # 2. HEAD başarısızsa GET ile ilk 1024 baytı çek
            response = await httpx_client.get(url, headers=req_headers)

            # Range desteklemeyen sunucularda 416 hatası dönebilir, Range olmadan tekrar dene
            if response.status_code == 416:
                req_headers.pop("Range")
                response = await httpx_client.get(url, headers=req_headers)

            if response.status_code in [403, 503] or "cloudflare" in response.headers.get("server", "").lower():
                raise httpx.HTTPStatusError("Cloudflare", request=response.request, response=response)

            if response.status_code not in [200, 206]:
                return False, f"HTTP Hata Kodu: {response.status_code}"

            # Yanıt gövdesini ve tipini incele
            content_type = response.headers.get("content-type", "").lower()
            text_preview = response.text[:500].lower() if response.text else ""

            if "#extm3u" in text_preview or "mpegurl" in content_type or "apple.mpegurl" in content_type:
                return True, "HLS Stream (m3u8) Playable"

            if "html" in content_type:
                if any(x in text_preview for x in ("forbidden", "unauthorized", "cloudflare", "error", "dns", "yasak", "hata", "bulunamadı")):
                    if "cloudflare" in text_preview or "forbidden" in text_preview:
                        raise httpx.HTTPStatusError("Cloudflare Blocked (HTML)", request=response.request, response=response)
                    return False, f"Hata Sayfası Döndü (HTML): {text_preview[:80].strip()}"
                return False, "Video beklenirken HTML sayfası döndü"

            if "video" in content_type or "octet-stream" in content_type or response.content:
                return True, f"Video Stream ({content_type or 'unknown'}) Playable"

            return False, f"Belirsiz İçerik Tipi: {content_type}"

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, Exception) as primary_err:
            # Cloudflare veya bağlantı hatası durumunda curl_cffi (Firefox) ile bypass etmeyi dene
            cf_session = cls._get_cf()
            try:
                # DİKKAT: curl_cffi için de Range ekliyoruz. Yoksa videonun tamamını indirir, kilitlenir.
                req_headers = headers.copy()
                req_headers["Range"] = "bytes=0-1024"

                response = await cf_session.get(url, headers=req_headers, allow_redirects=True)

                # Eğer Range hatası (416) verirse, başlık olmadan son bir kez deneriz
                if response.status_code == 416:
                    req_headers.pop("Range")
                    response = await cf_session.get(url, headers=req_headers, allow_redirects=True)

                if response.status_code in [200, 206]:
                    content_type = response.headers.get("content-type", "").lower()
                    text_preview = response.text[:500].lower() if response.text else ""

                    if "#extm3u" in text_preview or "mpegurl" in content_type or "apple.mpegurl" in content_type:
                        return True, "HLS Stream (m3u8) Playable (CF Bypass)"

                    if "html" in content_type:
                        if any(x in text_preview for x in ("forbidden", "unauthorized", "cloudflare", "error", "dns", "yasak", "hata", "bulunamadı")):
                            return False, f"Hata Sayfası Döndü (HTML/CF): {text_preview[:80].strip()}"
                        return False, "Video beklenirken HTML sayfası döndü (CF)"

                    if "video" in content_type or "octet-stream" in content_type or response.content:
                        return True, f"Video Stream ({content_type or 'unknown'}) Playable (CF Bypass)"

                    return False, f"Belirsiz İçerik Tipi (CF): {content_type}"
                else:
                    return False, f"HTTP Hata Kodu (CF): {response.status_code}"
            except Exception:
                pass

            if isinstance(primary_err, httpx.TimeoutException):
                return False, "Zaman Aşımı (Timeout)"
            elif isinstance(primary_err, httpx.ConnectError):
                return False, "Sunucuya Bağlanılamadı (Connection Error)"
            return False, f"Bağlantı Hatası: {str(primary_err)}"
