# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re, json

class JetTv(ExtractorBase):
    name     = "JetTv"
    main_url = "https://jetv.xyz"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        istek    = await self.httpx.get(url)
        document = istek.text

        # 1. Yöntem: API üzerinden alma
        master_url = ""
        final_ref  = f"{self.main_url}/"

        if "id=" in url:
            vid_id = url.split("id=")[-1]
            api_url = f"https://jetv.xyz/apollo/get_video.php?id={vid_id}"
            try:
                # Referer olarak video sayfasının kendisi gönderilmeli
                api_resp = await self.httpx.get(api_url, headers={"Referer": url})
                api_json = api_resp.json()
                
                if api_json.get("success"):
                     master_url = api_json.get("masterUrl", "")
                     final_ref  = api_json.get("referrerUrl") or final_ref
            except Exception:
                pass

        # 2. Yöntem: Regex Fallback
        if not master_url:
             if match := re.search(r"file: '([^']*)'", document, re.IGNORE_CASE):
                 master_url = match.group(1)
        
        if not master_url:
            raise ValueError(f"JetTv: Video kaynağı bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = master_url,
            referer   = final_ref,
            headers   = {},
            subtitles = []
        )
