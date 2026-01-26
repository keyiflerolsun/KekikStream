# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer

class PlayerFilmIzle(ExtractorBase):
    name     = "PlayerFilmIzle"
    main_url = "https://player.filmizle.in"

    def can_handle_url(self, url: str) -> bool:
        return "filmizle.in" in url or "fireplayer" in url.lower()

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref = referer or self.main_url
        self.httpx.headers.update({"Referer": ref})
        
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        subtitles = []
        if raw_subs := sel.regex_first(r'playerjsSubtitle\s*=\s*"([^"]*)"'):
            for lang, link in HTMLHelper(raw_subs).regex_all(r'\[(.*?)\](https?://[^\s\",]+)'):
                subtitles.append(Subtitle(name=lang.strip(), url=link.strip()))

        content  = Packer.unpack(resp.text) if Packer.detect_packed(resp.text) else resp.text
        data_val = HTMLHelper(content).regex_first(r'FirePlayer\s*\(\s*["\']([a-f0-9]+)["\']')

        if not data_val:
             raise ValueError(f"PlayerFilmIzle: Data bulunamadı. {url}")

        resp_vid = await self.httpx.post(
            f"{self.main_url}/player/index.php?data={data_val}&do=getVideo",
            data    = {"hash": data_val, "r": ""},
            headers = {"X-Requested-With": "XMLHttpRequest"}
        )
        
        m3u8_url = HTMLHelper(resp_vid.text).regex_first(r'"securedLink":"([^"]+)"')
        if not m3u8_url:
            raise ValueError(f"PlayerFilmIzle: Video URL bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = m3u8_url.replace("\\", ""),
            referer   = ref,
            subtitles = subtitles
        )
