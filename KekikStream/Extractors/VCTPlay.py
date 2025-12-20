# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from urllib.parse     import urlparse, parse_qs

class VCTPlay(ExtractorBase):
    name     = "VCTPlay"
    main_url = "https://vctplay.site"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        # URL'den video ID'sini çıkar
        # https://vctplay.site/video/2hjDGco5exdv -> 2hjDGco5exdv
        video_id = url.split("/")[-1]
        if "?" in video_id:
            video_id = video_id.split("?")[0]

        # Manifests URL oluştur
        master_url = f"{self.main_url}/manifests/{video_id}/master.txt"

        # partKey'den isim belirle
        parsed   = urlparse(url)
        params   = parse_qs(parsed.query)
        part_key = params.get("partKey", [""])[0]

        name_suffix = ""
        if "turkcedublaj" in part_key.lower():
            name_suffix = "Dublaj"
        elif "turkcealtyazi" in part_key.lower():
            name_suffix = "Altyazı"

        display_name = f"{self.name} - {name_suffix}" if name_suffix else self.name

        return ExtractResult(
            name      = display_name,
            url       = master_url,
            referer   = f"{self.main_url}/",
            subtitles = []
        )
