# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Kekik.Sifreleme  import Packer
import re, base64

def get_m3u_link(data: str) -> str:
    first = base64.b64decode(data)
    first_reversed = first[::-1]
    
    second = base64.b64decode(first_reversed)
    
    parts = second.decode('utf-8').split("|")
    if len(parts) < 2:
        raise ValueError("Decoded data has an unexpected format.")
    
    return parts[1]

def extract_data(raw_script: str) -> str:
    pattern = re.compile(r'return result\}var .*?=.*?\("(.*?)"\)')
    if match := pattern.search(raw_script):
        return match[1]
    else:
        raise Exception("data not found")

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.de"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        eval_func = re.compile(r'\s*(eval\(function[\s\S].*)\s*').findall(istek.text)[0]
        m3u_link  = get_m3u_link(extract_data(Packer.unpack(eval_func)))

        await self.close()
        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            headers   = {},
            subtitles = []
        )