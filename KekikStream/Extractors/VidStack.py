# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Crypto.Cipher    import AES
from Crypto.Util      import Padding
import re

class VidStack(ExtractorBase):
    name     = "VidStack"
    main_url = "https://vidstack.io"
    requires_referer = True

    supported_domains = [
        "vidstack.io", "server1.uns.bio", "upns.one"
    ]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    def decrypt_aes(self, input_hex: str, key: str, iv: str) -> str:
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            raw_data = bytes.fromhex(input_hex)
            decrypted = cipher.decrypt(raw_data)
            unpadded = Padding.unpad(decrypted, AES.block_size)
            return unpadded.decode('utf-8')
        except Exception as e:
            # print(f"DEBUG VidStack: {iv} -> {e}") # Debugging
            return None

    async def extract(self, url: str, referer: str = None) -> ExtractResult | list[ExtractResult]:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"}

        # Hash ve Base URL çıkarma
        hash_val = url.split("#")[-1].split("/")[-1]
        base_url = self.get_base_url(url)

        # API İsteği
        api_url = f"{base_url}/api/v1/video?id={hash_val}"
        istek   = await self.httpx.get(api_url, headers=headers)

        # Bazen yanıt tırnak içinde gelebilir, temizleyelim
        encoded_data = istek.text.strip().strip('"')

        # AES Çözme
        key = "kiemtienmua911ca"
        ivs = ["1234567890oiuytr", "0123456789abcdef"]

        decrypted_text = None
        for iv in ivs:
            decrypted_text = self.decrypt_aes(encoded_data, key, iv)
            if decrypted_text and '"source":' in decrypted_text:
                break

        if not decrypted_text:
            # Hata mesajını daha detaylı verelim (debug için tırnaklanmış hali)
            raise ValueError(f"VidStack: AES çözme başarısız. {url} | Response: {istek.text[:50]}...")

        # m3u8 ve Alt yazı çıkarma
        # Kotlin'de "source":"(.*?)" regex'i kullanılıyor
        m3u8_url = re.search(r'["\']source["\']\s*:\s*["\']([^"\']+)["\']', decrypted_text)
        if m3u8_url:
            m3u8_url = m3u8_url.group(1).replace("\\/", "/")
        else:
            raise ValueError(f"VidStack: m3u8 bulunamadı. {url}")

        subtitles = []
        # Kotlin: "subtitle":\{(.*?)\}
        subtitle_section = re.search(r'["\']subtitle["\']\s*:\s*\{(.*?)\}', decrypted_text)
        if subtitle_section:
            section = subtitle_section.group(1)
            # Regex: "([^"]+)":\s*"([^"]+)"
            matches = re.finditer(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']', section)
            for match in matches:
                lang = match.group(1)
                raw_path = match.group(2).split("#")[0]
                if raw_path:
                    path = raw_path.replace("\\/", "/")
                    sub_url = f"{self.main_url}{path}"
                    subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = url,
            user_agent = headers["User-Agent"],
            subtitles  = subtitles
        )
