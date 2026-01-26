# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper, Subtitle
from urllib.parse import quote
import re

class Videostr(ExtractorBase):
    name     = "Videostr"
    main_url = "https://videostr.net"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        v_id = url.split("?")[0].split("/")[-1]
        headers = {"Referer": self.main_url, "X-Requested-With": "XMLHttpRequest"}
        
        resp = await self.httpx.get(url, headers=headers)
        sel  = HTMLHelper(resp.text)

        # Nonce Bulma
        nonce = sel.regex_first(r"\b[a-zA-Z0-9]{48}\b")
        if not nonce:
            m = re.search(r"\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b", resp.text, re.DOTALL)
            if m: nonce = m.group(1) + m.group(2) + m.group(3)

        if not nonce:
            raise ValueError(f"Videostr: Nonce bulunamadı. {url}")

        # Kaynakları Çek
        api_resp = await self.httpx.get(f"{self.main_url}/embed-1/v3/e-1/getSources?id={v_id}&_k={nonce}", headers=headers)
        data = api_resp.json()
        
        enc_file = data.get("sources", [{}])[0].get("file")
        if not enc_file:
            raise ValueError("Videostr: Kaynak bulunamadı.")

        m3u8_url = None
        if ".m3u8" in enc_file:
            m3u8_url = enc_file
        else:
            # Decryption Flow (External Keys)
            with contextlib.suppress(Exception):
                key_resp = await self.httpx.get("https://raw.githubusercontent.com/yogesh-hacker/MegacloudKeys/refs/heads/main/keys.json")
                v_key = key_resp.json().get("vidstr")
                if v_key:
                    decode_api = "https://script.google.com/macros/s/AKfycbxHbYHbrGMXYD2-bC-C43D3njIbU-wGiYQuJL61H4vyy6YVXkybMNNEPJNPPuZrD1gRVA/exec"
                    dec_resp = await self.httpx.get(f"{decode_api}?encrypted_data={quote(enc_file)}&nonce={quote(nonce)}&secret={quote(v_key)}")
                    m3u8_url = re.search(r'"file":"(.*?)"', dec_resp.text).group(1).replace("\\/", "/")

        if not m3u8_url:
            raise ValueError(f"Videostr: Video URL bulunamadı. {url}")

        subtitles = [
            Subtitle(name=t.get("label", "Altyazı"), url=t.get("file"))
            for t in data.get("tracks", []) if t.get("kind") in ["captions", "subtitles"]
        ]

        return ExtractResult(name=self.name, url=m3u8_url, referer=f"{self.main_url}/", subtitles=subtitles)

import contextlib
