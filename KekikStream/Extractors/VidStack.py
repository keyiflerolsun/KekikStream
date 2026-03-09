# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Crypto.Cipher    import AES
from Crypto.Util      import Padding
from urllib.parse     import urlparse, parse_qs
import re

class VidStack(ExtractorBase):
    name             = "VidStack"
    main_url         = "https://vidstack.io"
    requires_referer = True

    supported_domains = [
        "vidstack.io", "server1.uns.bio", "upns.one", "upn.one",
        "webdrama.upns.online", "webdrama.playerp2p.com",
        "player4me.vip", "vidplayer.live",
    ]

    def decrypt_aes(self, input_hex: str, key: str, iv: bytes) -> str:
        try:
            cipher    = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv)
            raw_data  = bytes.fromhex(input_hex)
            decrypted = cipher.decrypt(raw_data)
            unpadded  = Padding.unpad(decrypted, AES.block_size)
            return unpadded.decode('utf-8')
        except Exception:
            return None

    def _extract_id(self, url: str) -> str:
        # ?id=XXX query parametresini dene
        qs = parse_qs(urlparse(url).query)
        if "id" in qs:
            return qs["id"][0]
        # Fragment veya son path parçası (#hash ya da /path/hash)
        fragment = url.split("#")[-1]
        return fragment.split("/")[-1]

    async def extract(self, url: str, referer: str = None) -> ExtractResult | list[ExtractResult]:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0"}

        hash_val = self._extract_id(url)
        base_url = self.get_base_url(url)

        # API İsteği
        api_url = f"{base_url}/api/v1/video?id={hash_val}"
        istek   = await self.httpx.get(api_url, headers=headers)

        # Bazen yanıt tırnak içinde gelebilir, temizleyelim
        encoded_data = istek.text.strip().strip('"')

        # AES Çözme — sıfır IV (webdrama), ardından bilinen IV'lar
        key = "kiemtienmua911ca"
        ivs = [b"\x00" * 16, b"1234567890oiuytr", b"0123456789abcdef"]

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
                lang     = match.group(1)
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
