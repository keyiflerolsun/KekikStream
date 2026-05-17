# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Extractor.ExtractorModels import ExtractResult
from urllib.parse                import urlparse
from curl_cffi.requests          import AsyncSession
import httpx

class PlayabilityHelper:
    @staticmethod
    async def is_url_playable(link: ExtractResult) -> tuple[bool, str]:
        """URL'nin oynatılabilir (playable) olup olmadığını kontrol eder."""
        url = link.url
        if not url:
            return False, "URL boş"

        # YouTube veya fragman linklerini doğrudan kabul et
        if "youtube.com" in url or "youtu.be" in url:
            return True, "YouTube Embed / Fragman"

        if not url.startswith(("http://", "https://")):
            return False, f"Geçersiz URL şeması: {url[:50]}"

        # Header hazırlama
        headers = {
            "Accept"          : "*/*",
            "Accept-Language" : "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        if link.referer:
            headers["Referer"] = link.referer
            try:
                parsed = urlparse(link.referer)
                if parsed.scheme and parsed.netloc:
                    headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

        if link.user_agent:
            headers["User-Agent"] = link.user_agent
        else:
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Varsa ek header'ları ekle (Cookie vb.)
        if link.extra_headers:
            headers.update(link.extra_headers)

        try:
            # SSL doğrulamasını devre dışı bırakarak ve redirect'leri takip ederek bağlanalım
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False, limits=limits) as client:
                # 1. Hızlı HEAD isteğiyle kontrol et
                try:
                    response = await client.head(url, headers=headers)
                    if response.status_code in [200, 206]:
                        content_type = response.headers.get("content-type", "").lower()
                        if content_type and "html" not in content_type:
                            return True, f"HEAD Başarılı ({response.status_code}, {content_type})"
                except Exception:
                    pass

                # 2. HEAD başarısızsa GET ile ilk 1024 baytı çek
                headers["Range"] = "bytes=0-1024"
                response = await client.get(url, headers=headers)

                # Range desteklemeyen sunucularda 416 hatası dönebilir, Range olmadan tekrar dene
                if response.status_code == 416:
                    headers.pop("Range")
                    response = await client.get(url, headers=headers)

                # Cloudflare/403/503 durumunda curl_cffi ile tekrar dene
                if response.status_code in [403, 503] or "cloudflare" in response.headers.get("server", "").lower():
                    raise httpx.HTTPStatusError("Cloudflare / Access Blocked", request=response.request, response=response)

                if response.status_code not in [200, 206]:
                    return False, f"HTTP Hata Kodu: {response.status_code}"

                # Yanıt gövdesini ve tipini incele
                content_type = response.headers.get("content-type", "").lower()
                text_preview = response.text[:500].lower() if response.text else ""

                # m3u8 playlist check (Check this before HTML check because some providers serve m3u8 as text/html)
                if "#extm3u" in text_preview or "mpegurl" in content_type or "apple.mpegurl" in content_type:
                    return True, "HLS Stream (m3u8) Playable"

                # Eğer HTML dönüyorsa ve hata ifadeleri içeriyorsa oynatılamazdır
                if "html" in content_type:
                    if any(x in text_preview for x in ("forbidden", "unauthorized", "cloudflare", "error", "dns", "yasak", "hata", "bulunamadı")):
                        # Cloudflare engeline takılmış olma ihtimali için hata fırlatıp curl_cffi'a geçelim
                        if "cloudflare" in text_preview or "forbidden" in text_preview:
                            raise httpx.HTTPStatusError("Cloudflare Blocked (HTML)", request=response.request, response=response)
                        return False, f"Hata Sayfası Döndü (HTML): {text_preview[:80].strip()}"
                    return False, "Video beklenirken HTML sayfası döndü"

                # Video content check
                if "video" in content_type or "octet-stream" in content_type or response.content:
                    return True, f"Video Stream ({content_type or 'unknown'}) Playable"

                return False, f"Belirsiz İçerik Tipi: {content_type}"

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, Exception) as primary_err:
            # Cloudflare veya bağlantı hatası durumunda curl_cffi (Firefox) ile bypass etmeyi dene
            try:
                async with AsyncSession(impersonate="firefox") as session:
                    # session.headers'ı güncelle
                    session.headers.update(headers)
                    # curl_cffi ile istek at
                    response = await session.get(url, timeout=8.0, allow_redirects=True)
                    if response.status_code in [200, 206]:
                        content_type = response.headers.get("content-type", "").lower()
                        text_preview = response.text[:500].lower() if response.text else ""

                        # m3u8 playlist check (Check this before HTML check)
                        if "#extm3u" in text_preview or "mpegurl" in content_type or "apple.mpegurl" in content_type:
                            return True, "HLS Stream (m3u8) Playable (CF Bypass)"

                        if "html" in content_type:
                            if any(x in text_preview for x in ("forbidden", "unauthorized", "cloudflare", "error", "dns", "yasak", "hata", "bulunamadı")):
                                return False, f"Hata Sayfası Döndü (HTML/CF): {text_preview[:80].strip()}"
                            return False, "Video beklenirken HTML sayfası döndü (CF)"

                        # Video content check
                        if "video" in content_type or "octet-stream" in content_type or response.content:
                            return True, f"Video Stream ({content_type or 'unknown'}) Playable (CF Bypass)"

                        return False, f"Belirsiz İçerik Tipi (CF): {content_type}"
                    else:
                        return False, f"HTTP Hata Kodu (CF): {response.status_code}"
            except Exception:
                # curl_cffi da hata verirse, asıl hatayı raporla
                pass

            if isinstance(primary_err, httpx.TimeoutException):
                return False, "Zaman Aşımı (Timeout)"
            elif isinstance(primary_err, httpx.ConnectError):
                return False, "Sunucuya Bağlanılamadı (Connection Error)"
            return False, f"Bağlantı Hatası: {str(primary_err)}"
