# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme import AESManager
import re
import json

class HDMomPlayer(ExtractorBase):
    name     = "HDMomPlayer"
    main_url = "hdmomplayer.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult | None:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        try:
            response = await self.httpx.get(url)
            page_source = response.text
            
            m3u_link = None
            
            # Regex for bePlayer matches
            # Matches: bePlayer('PASS', '{DATA}');
            helper = HTMLHelper(page_source)
            be_matches = helper.regex_all(r"bePlayer\('([^']+)',\s*'(\{[^\}]+\})'\);")
            
            if be_matches:
                pass_val, data_val = be_matches[0]
                
                try:
                    # Use Kekik.Sifreleme.AESManager as requested
                    decrypted = AESManager.decrypt(data_val, pass_val).replace("\\", "")
                    
                    # Search for video_location in decrypted string
                    # Kotlin: video_location":"([^"]+)
                    m_loc = re.search(r'video_location":"([^"]+)"', decrypted)
                    if m_loc:
                        m3u_link = m_loc.group(1).replace(r"\/", "/")
                except Exception:
                    pass

            if not m3u_link:
                # Fallback regex
                # file:"..."
                m_file = re.search(r'file:"([^"]+)"', page_source)
                if m_file:
                    m3u_link = m_file.group(1)
            
            if not m3u_link:
                return None
            
            # Fix URL if needed
            if m3u_link.startswith("//"):
                m3u_link = "https:" + m3u_link
                
            return ExtractResult(
                name    = "HDMomPlayer",
                url     = m3u_link,
                referer = url, 
            )
        except Exception:
            return None
