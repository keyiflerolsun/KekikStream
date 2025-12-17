# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Kekik.Sifreleme  import Packer
import re

class FirePlayer(ExtractorBase):
    name     = "FirePlayer"
    main_url = "https://Player.filmizle.in"

    def can_handle_url(self, url: str) -> bool:
        return "filmizle.in" in url or "fireplayer" in url.lower()

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if not referer:
            referer = "https://sinezy.site/"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": referer
        }

        istek  = await self.cffi.get(url, headers=headers)
        
        # Unpack usage similar to VidMoxy / suggestion
        # Find the packed code block
        match = re.search(r'(eval\(function\(p,a,c,k,e,d\)[\s\S]+?)\s*</script>', istek.text)
        if match:
            packed_code = match.group(1)
            unpacked    = Packer.unpack(packed_code)
        else:
            unpacked = istek.text

        # Normalize escaped slashes
        unpacked = unpacked.replace(r"\/", "/")
        
        video_url = None
        
        # Look for .mp4 or .m3u8 urls directly first
        url_match = re.search(r'(https?://[^"\'\s]+\.(?:mp4|m3u8))', unpacked)
        if url_match:
             video_url = url_match.group(1)
        
        if not video_url:
             # Fallback: find all 'file': '...' and pick best
             files = re.findall(r'file\s*:\s*["\']([^"\']+)["\']', unpacked)
             for f in files:
                 if f.strip() and not f.endswith(".jpg") and not f.endswith(".png") and not f.endswith(".vtt"):
                     video_url = f
                     break

        if not video_url:
             raise ValueError("Could not find video URL in unpacked content")

        return ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = url,
            headers   = headers
        )

