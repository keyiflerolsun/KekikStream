# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import json, html, re

class Odnoklassniki(ExtractorBase):
    name     = "Odnoklassniki"
    main_url = "https://odnoklassniki.ru"

    supported_domains = ["odnoklassniki.ru", "ok.ru", "vkvideo.ru", "vk.com"]

    @staticmethod
    def _extract_metadata_from_data_options(sel: HTMLHelper) -> dict | None:
        raw_options = sel.select_attr("[data-module='OKVideo']", "data-options")
        if not raw_options:
            return None

        try:
            options   = json.loads(html.unescape(raw_options))
            flashvars = options.get("flashvars") or {}
            metadata  = flashvars.get("metadata")
            parsed_md = json.loads(metadata) if metadata else None
            return parsed_md if isinstance(parsed_md, dict) else None
        except Exception:
            return None

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # href.li redirect wrapper'ını soy
        if "href.li/?" in url:
            url = url.split("href.li/?", 1)[1]

        # vkvideo.ru / vk.com → embed formatına çevir
        if "vkvideo.ru" in url or "vk.com" in url:
            return await self._extract_vk(url, referer)

        if "/video/" in url:
            url = url.replace("/video/", "/videoembed/")
        self.httpx.headers.update({"Origin": self.main_url})

        resp = await self.httpx.get(url, follow_redirects=True)
        sel  = HTMLHelper(resp.text)

        if metadata := self._extract_metadata_from_data_options(sel):
            best_url = metadata.get("ondemandHls") or metadata.get("ondemandDash")
            videos   = metadata.get("videos") or []

            if not best_url:
                order = ["ULTRA", "QUAD", "FULL", "HD", "SD", "LOW", "MOBILE"]
                for q in order:
                    best_url = next((v.get("url") for v in videos if v.get("name", "").upper() == q), None)
                    if best_url:
                        break

            if not best_url and videos:
                best_url = videos[0].get("url")

            if best_url:
                best_url = html.unescape(best_url).replace("u0026", "&").replace("\\u0026", "&")
                if "\\u" in best_url:
                    best_url = best_url.encode().decode("unicode-escape")

                return ExtractResult(
                    name       = self.name,
                    url        = self.fix_url(best_url),
                    referer    = url,
                    user_agent = self.httpx.headers.get("User-Agent")
                )

        # Metadata içinden videos array'ini al (esnek regex)
        # Bazen "videos": [...] bazen metadata: { ..., "videos": [...] }
        v_data = sel.regex_first(r'["\']?videos["\']?\s*[:=]\s*(\[.*?\])') or \
                 sel.regex_first(r'["\']?metadata["\']?\s*[:=]\s*["\']?(\{.*?\})["\']?')

        if v_data and v_data.startswith("{"):
            # If we found metadata object, try to extract videos from it
            try:
                meta_json = json.loads(v_data)
                videos    = meta_json.get("videos")
                v_data    = json.dumps(videos) if videos else None
            except:
                v_data = HTMLHelper(v_data).regex_first(r'["\']?videos["\']?\s*[:]\s*(\[.*?\])')

        if not v_data:
            if "Видео заблокировано" in resp.text or "copyrightsRestricted" in resp.text or "not_found" in resp.text:
                raise ValueError("Odnoklassniki: Video telif nedeniyle silinmiş/erişilemiyor.")
            raise ValueError(f"Odnoklassniki: Video verisi bulunamadı. {url}")

        # Kalite sıralaması (En yüksekten düşüğe)
        order = ["ULTRA", "QUAD", "FULL", "HD", "SD", "LOW", "MOBILE"]
        # Escaped string'i temizle
        v_data = html.unescape(v_data)
        v_data = v_data.replace('\\"', '"').replace('\\/', '/')
        videos = json.loads(v_data)

        best_url = None
        for q in order:
            best_url = next((v.get("url") for v in videos if v.get("name", "").upper() == q), None)
            if best_url:
                break

        if not best_url:
            best_url = videos[0].get("url") if videos else None

        if not best_url:
            raise ValueError("Odnoklassniki: Geçerli video URL'si bulunamadı.")

        # URL temizliği (u0026 -> & ve olası unicode kaçışları)
        best_url = best_url.replace("u0026", "&").replace("\\u0026", "&")
        # Eğer hala \uXXXX formatında unicode kaçışları varsa çöz
        if "\\u" in best_url:
            best_url = best_url.encode().decode('unicode-escape')

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(best_url),
            referer    = referer,
            user_agent = self.httpx.headers.get("User-Agent")
        )

    async def _extract_vk(self, url: str, referer: str = None) -> ExtractResult:
        """vkvideo.ru / vk.com video_ext.php embed üzerinden mp4 URL çıkar."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # vk.com/video_ext.php?oid=X&id=Y zaten embed formatında
        if "video_ext.php" in url:
            embed_url = url
        else:
            # vkvideo.ru/video-OWNERID_VIDEOID formatı
            vm = re.match(r'.*/video(-?\d+)_(\d+)', url)
            if not vm:
                raise ValueError(f"Odnoklassniki: VK video ID ayrıştırılamadı. {url}")
            oid, vid  = vm.group(1), vm.group(2)
            embed_url = f"https://vkvideo.ru/video_ext.php?oid={oid}&id={vid}"

        resp = await self.httpx.get(embed_url, headers={"User-Agent": user_agent}, follow_redirects=True)

        # mp4_1080, mp4_720, mp4_480, mp4_360, mp4_240, mp4_144 kalite sırası
        order    = ["1080", "720", "480", "360", "240", "144"]
        best_url = None
        for q in order:
            m = re.search(rf'"mp4_{q}"\s*:\s*"([^"]+)"', resp.text)
            if m:
                best_url = m.group(1).replace("\\/", "/")
                break

        if not best_url:
            raise ValueError(f"Odnoklassniki: VK video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(best_url),
            referer    = embed_url,
            user_agent = user_agent
        )
