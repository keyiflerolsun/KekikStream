# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Crypto.Cipher    import AES
from urllib.parse     import urlparse
import re, binascii

class VidStack(ExtractorBase):
    name             = "VidStack"
    main_url         = "https://vidstack.io"
    requires_referer = True

    def get_base_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return self.main_url

    def decrypt_aes(self, encrypted_hex: str, key: str, iv: str) -> str:
        try:
            key_bytes = key.encode('utf-8')
            iv_bytes  = iv.encode('utf-8')
            cipher    = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            
            encrypted_bytes = binascii.unhexlify(encrypted_hex)
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            
            # Remove PKCS5 padding
            padding_len = decrypted_bytes[-1]
            return decrypted_bytes[:-padding_len].decode('utf-8')
        except Exception:
            return None

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.cffi.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"
        })

        if referer:
            self.cffi.headers.update({"Referer": referer})

        video_hash = url.split("#")[-1].split("/")[-1]
        base_url   = self.get_base_url(url)
        
        api_url = f"{base_url}/api/v1/video?id={video_hash}"
        istek   = await self.cffi.get(api_url)
        encoded = istek.text.strip()

        key     = "kiemtienmua911ca"
        iv_list = ["1234567890oiuytr", "0123456789abcdef"]
        
        decrypted_text = None
        for iv in iv_list:
            if result := self.decrypt_aes(encoded, key, iv):
                decrypted_text = result
                break
        
        if not decrypted_text:
            raise ValueError(f"VidStack: Şifre çözülemedi. {url}")

        m3u8_url = ""
        if match := re.search(r'"source":"(.*?)"', decrypted_text):
            m3u8_url = match.group(1).replace("\\/", "/")
        
        if not m3u8_url:
             raise ValueError(f"VidStack: Source bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = m3u8_url,
            referer   = url,
            headers   = {},
            subtitles = []
        )
