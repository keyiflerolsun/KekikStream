# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper, Subtitle
from urllib.parse import quote
from json import loads

class Videostr(ExtractorBase):
    name     = "Videostr"
    main_url = "videostr.net"

    async def extract(self, url: str, referer: str = None) -> ExtractResult | None:
        headers = {
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://videostr.net",
        }
        
        # 1. Get nonce page
        # Kotlin: url.substringAfterLast("/").substringBefore("?")
        id = url.split("?")[0].split("/")[-1]
        
        istek = await self.httpx.get(url, headers=headers)
        if istek.status_code != 200:
            return None
            
        responsenonce = istek.text
        
        # Find nonce
        # Regex: \b[a-zA-Z0-9]{48}\b
        # Or 3 blocks of 16 chars
        helper = HTMLHelper(responsenonce)
        nonce = helper.regex_first(r"\b[a-zA-Z0-9]{48}\b")
        if not nonce:
            # Fallback regex as per Kotlin: \b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b
            # In Python we can just look for the combined matches if regex_first handles grouping poorly or try finding all
            import re
            m = re.search(r"\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b", responsenonce, re.DOTALL)
            if m:
                nonce = m.group(1) + m.group(2) + m.group(3)
        
        if not nonce:
            return None
            
        # 2. Get Sources
        api_url = f"https://videostr.net/embed-1/v3/e-1/getSources?id={id}&_k={nonce}"
        
        api_resp = await self.httpx.get(api_url, headers=headers)
        if api_resp.status_code != 200:
            return None
            
        # Parse JSON
        try:
            data = api_resp.json()
        except:
            return None
            
        sources = data.get("sources", [])
        if not sources:
            return None
            
        encrypted_file = sources[0].get("file")
        if not encrypted_file:
            return None
            
        m3u8_url = None
        
        if ".m3u8" in encrypted_file:
            m3u8_url = encrypted_file
        else:
            # Decrypt
            # Need key from github
            key_url = "https://raw.githubusercontent.com/yogesh-hacker/MegacloudKeys/refs/heads/main/keys.json"
            key_resp = await self.httpx.get(key_url)
            if key_resp.status_code == 200:
                try:
                    keys = key_resp.json()
                    vidstr_key = keys.get("vidstr") # As per Kotlin code: gson.fromJson(keyJson, Megakey::class.java)?.vidstr
                    
                    if vidstr_key:
                        # Use Google Script to decrypt
                        decode_url = "https://script.google.com/macros/s/AKfycbxHbYHbrGMXYD2-bC-C43D3njIbU-wGiYQuJL61H4vyy6YVXkybMNNEPJNPPuZrD1gRVA/exec"
                        
                        full_url = f"{decode_url}?encrypted_data={quote(encrypted_file)}&nonce={quote(nonce)}&secret={quote(vidstr_key)}"
                        
                        decrypted_resp = await self.httpx.get(full_url)
                        if decrypted_resp.status_code == 200:
                            # Response is JSON {"file": "..."} usually or text?
                            # Kotlin says: Regex("\"file\":\"(.*?)\"").find(decryptedResponse)
                            m_file = re.search(r'"file":"(.*?)"', decrypted_resp.text)
                            if m_file:
                                m3u8_url = m_file.group(1).replace(r"\/", "/")
                except Exception as e:
                    # print(f"Decryption error: {e}")
                    pass

        if not m3u8_url:
            return None
            
        # Subtitles
        # Kotlin: response.tracks
        subtitles = []
        tracks = data.get("tracks", [])
        for t in tracks:
            if t.get("kind") in ["captions", "subtitles"]:
                subtitles.append(Subtitle(
                    name = t.get("label", "Altyazı"),
                    url  = t.get("file")
                ))
                
        return ExtractResult(
            name     = "Videostr",
            url      = m3u8_url,
            referer  = "https://videostr.net/",
            subtitles= subtitles
        )
