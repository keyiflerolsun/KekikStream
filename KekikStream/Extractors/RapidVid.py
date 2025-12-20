# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme  import Packer, HexCodec
import re, base64

class RapidVid(ExtractorBase):
    name     = "RapidVid"
    main_url = "https://rapidvid.net"

    # Birden fazla domain destekle
    supported_domains = ["rapidvid.net", "rapid.filmmakinesi.to"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        subtitles        = []
        subtitle_matches = re.findall(r'captions\",\"file\":\"([^\"]+)\",\"label\":\"([^\"]+)\"', istek.text)
        seen_subtitles   = set()

        for sub_url, sub_lang in subtitle_matches:
            if sub_url in seen_subtitles:
                continue

            seen_subtitles.add(sub_url)
            decoded_lang = (
                sub_lang.replace("\\u0131", "ı")
                        .replace("\\u0130", "İ")
                        .replace("\\u00fc", "ü")
                        .replace("\\u00e7", "ç")
            )
            subtitles.append(Subtitle(name=decoded_lang, url=sub_url.replace("\\", "")))

        try:
            if extracted_value := re.search(r'file": "(.*)",', istek.text):
                escaped_hex = extracted_value[1]
                decoded_url = HexCodec.decode(escaped_hex)
            else:
                av_encoded = re.search(r"av\('([^']+)'\)", istek.text)
                if not av_encoded:
                    raise ValueError("AV encoding not found.")

                decoded_url = self.decode_secret(av_encoded[1])
        except Exception as hata:
            raise RuntimeError(f"Extraction failed: {hata}") from hata

        return ExtractResult(
            name      = self.name,
            url       = decoded_url,
            referer   = self.main_url,
            subtitles = subtitles
        )

    def decode_secret(self, encoded_string: str) -> str:
        # 1. Base64 ile şifrelenmiş string ters çevrilmiş, önce geri çeviriyoruz
        reversed_input = encoded_string[::-1]

        # 2. İlk base64 çözme işlemi
        decoded_once = base64.b64decode(reversed_input).decode("utf-8")

        decrypted_chars = []
        key = "K9L"

        # 3. Key'e göre karakter kaydırma geri alınıyor
        for index, encoded_char in enumerate(decoded_once):
            key_char = key[index % len(key)]
            offset = (ord(key_char) % 5) + 1  # Her karakter için dinamik offset

            original_char_code = ord(encoded_char) - offset
            decrypted_chars.append(chr(original_char_code))

        # 4. Karakterleri birleştirip ikinci base64 çözme işlemini yapıyoruz
        intermediate_string = "".join(decrypted_chars)
        final_decoded_bytes = base64.b64decode(intermediate_string)

        return final_decoded_bytes.decode("utf-8")
