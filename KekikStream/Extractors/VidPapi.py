# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re

class VidPapi(ExtractorBase):
    name     = "VidApi"
    main_url = "https://vidpapi.xyz"

    async def extract(self, url, referer=None) -> ExtractResult:
        ext_ref = referer or ""
        
        # URL parsing
        if "video/" in url:
            vid_id = url.split("video/")[-1]
        else:
            vid_id = url.split("?data=")[-1]
            
        # 1. Altyazıları çek
        sub_url = f"{self.main_url}/player/index.php?data={vid_id}"
        sub_headers = {
            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With" : "XMLHttpRequest",
            "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
            "Referer"          : ext_ref or "https://kultfilmler.pro/"
        }
        
        subtitles = []
        try:
            sub_istek = await self.httpx.post(
                url     = sub_url,
                headers = sub_headers,
                data    = {"hash": vid_id, "r": "https://kultfilmler.pro/"}
            )
            
            subtitle_match = re.search(r'var playerjsSubtitle = "([^"]*)"', sub_istek.text, re.IGNORECASE)
            if subtitle_match and subtitle_match.group(1):
                raw_subs = subtitle_match.group(1)
                
                found_subs = re.findall(r'\[(.*?)\](.*?)(?:,|$)', raw_subs)
                for lang, sub_link in found_subs:
                    lang = lang.strip()
                    if "Türkçe" in lang:
                        lang_code = "tr"
                        lang_name = "Turkish"
                    elif "İngilizce" in lang:
                        lang_code = "en"
                        lang_name = "English"
                    else:
                        lang_code = lang[:2].lower()
                        lang_name = lang
                        
                    subtitles.append(Subtitle(
                        name = lang_name,
                        url  = sub_link.strip()
                    ))
                    
        except Exception as e:
            pass

        # 2. Videoyu çek
        video_url = f"{self.main_url}/player/index.php?data={vid_id}&do=getVideo"
        video_headers = sub_headers.copy()
        
        response = await self.httpx.post(
            url     = video_url,
            headers = video_headers,
            data    = {"hash": vid_id, "r": "https://kultfilmler.pro/"}
        )
        response.raise_for_status()
        
        try:
            video_data = response.json()
        except Exception:
            return None

        stream_url = video_data.get("securedLink")
        if not stream_url or not stream_url.strip():
            stream_url = video_data.get("videoSource")
            
        if not stream_url:
            raise ValueError("No video link found in VidPapi response")

        return ExtractResult(
            name      = self.name,
            url       = stream_url,
            referer   = ext_ref or self.main_url,
            subtitles = subtitles
        )
