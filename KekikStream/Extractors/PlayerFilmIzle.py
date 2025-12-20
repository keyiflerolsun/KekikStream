# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re

class PlayerFilmIzle(ExtractorBase):
    name     = "PlayerFilmIzle"
    main_url = "https://player.filmizle.in"

    def can_handle_url(self, url: str) -> bool:
        return "filmizle.in" in url or "fireplayer" in url.lower()

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # Kotlin tarafında referer mainUrl olarak zorlanmış
        ext_ref = self.main_url
        self.httpx.headers.update({"Referer": ext_ref})
        
        istek     = await self.httpx.get(url)
        video_req = istek.text

        subtitles = []
        if sub_match := re.search(r'playerjsSubtitle = "([^"]*)"', video_req, re.IGNORECASE):
            sub_yakala = sub_match.group(1)
            # Format örneği: [dil]url
            # Kotlin kodunda: subYakala.substringAfter("]") -> url
            # subYakala.substringBefore("]").removePrefix("[") -> lang
            if "]" in sub_yakala:
                sub_lang_raw, sub_url = sub_yakala.split("]", 1)
                sub_lang = sub_lang_raw.replace("[", "")
                subtitles.append(Subtitle(name=sub_lang, url=sub_url))

        # Data yakalama: FirePlayer|DATA|...
        data_match = re.search(r'FirePlayer\|([^|]+)\|', video_req, re.IGNORECASE)
        data_val   = data_match.group(1) if data_match else None

        if not data_val:
             raise ValueError("PlayerFilmIzle: Data bulunamadı")

        url_post = f"{self.main_url}/player/index.php?data={data_val}&do=getVideo"

        post_headers = {
            "Referer": ext_ref,
            "X-Requested-With": "XMLHttpRequest"
        }

        # Kotlin'de post data: "hash" -> data, "r" -> ""
        post_data = {"hash": data_val, "r": ""}

        response = await self.httpx.post(url_post, data=post_data, headers=post_headers)
        get_url  = response.text.replace("\\", "")

        m3u8_url = ""
        if url_yakala := re.search(r'"securedLink":"([^"]*)"', get_url, re.IGNORECASE):
            m3u8_url = url_yakala.group(1)

        if not m3u8_url:
            raise ValueError("PlayerFilmIzle: M3U8 linki bulunamadı")

        return ExtractResult(
            name       = self.name,
            url        = m3u8_url,
            referer    = ext_ref,
            user_agent = self.httpx.headers.get("User-Agent", None),
            subtitles  = subtitles
        )
