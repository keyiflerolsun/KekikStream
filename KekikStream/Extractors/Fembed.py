# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import re, json

class Fembed(ExtractorBase):
    name              = "Fembed"
    main_url          = "https://fembed.online"
    supported_domains = ["fembed.online", "fembed.net", "fembed.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        resp = await self.httpx.get(
            url     = url,
            headers = {"Referer": referer or self.main_url}
        )
        html = resp.text
        sel  = HTMLHelper(html)

        m3u8_url = None

        # playerSources dizisini JSON olarak çek
        src_match = re.search(r"var\s+playerSources\s*=\s*(\[.*?\]);", html, re.DOTALL)
        if src_match:
            try:
                sources  = json.loads(src_match.group(1))
                for src in sources:
                    f = src.get("file", "")
                    if f and (".m3u8" in f or ".mp4" in f):
                        m3u8_url = f
                        break
            except Exception:
                pass

        # Fallback: regex ile m3u8 bul
        if not m3u8_url:
            m3u8_url = sel.regex_first(r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"')

        if not m3u8_url:
            raise ValueError(f"{self.name}: Video URL bulunamadı. {url}")

        # Altyazıları çek (subtitles dizisinden)
        subtitles = []
        sub_match = re.search(r"var\s+subtitles\s*=\s*(\[.*?\]);", html, re.DOTALL)
        if sub_match:
            try:
                subs = json.loads(sub_match.group(1))
                for sub in subs:
                    s_file  = sub.get("file", "")
                    s_label = sub.get("label", "Altyazı")
                    if s_file and (s_file.startswith("http") or s_file.startswith("/")):
                        sub_url = self.fix_url(s_file)
                        subtitles.append(Subtitle(name=s_label, url=sub_url))
            except Exception:
                pass

        return ExtractResult(
            name      = self.name,
            url       = m3u8_url,
            referer   = self.main_url,
            subtitles = subtitles,
        )
