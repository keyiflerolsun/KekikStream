# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer, HexCodec, StreamDecoder
import base64

class RapidVid(ExtractorBase):
    name     = "RapidVid"
    main_url = "https://rapidvid.net"

    # Birden fazla domain destekle
    supported_domains = ["rapidvid.net", "rapid.filmmakinesi.to"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        subtitles = []
        for s_url, s_lang in sel.regex_all(r'captions","file":"([^\"]+)","label":"([^\"]+)"'):
            decoded_lang = s_lang.encode().decode('unicode_escape')
            subtitles.append(Subtitle(name=decoded_lang, url=s_url.replace("\\", "")))

        try:
            video_url = None

            # Method 1: HexCodec pattern
            if hex_data := sel.regex_first(r'file": "(.*)",'):
                video_url = HexCodec.decode(hex_data)

            # Method 2: av('...') pattern
            elif av_data := sel.regex_first(r"av\('([^']+)'\)"):
                video_url = self.decode_secret(av_data)

            # Method 3: Packed dc_*
            elif Packer.detect_packed(resp.text):
                unpacked  = Packer.unpack(resp.text)
                video_url = StreamDecoder.extract_stream_url(unpacked)

            if not video_url:
                raise ValueError(f"RapidVid: Video URL bulunamadı. {url}")

        except Exception as hata:
            raise RuntimeError(f"RapidVid: Extraction failed: {hata}") from hata

        return ExtractResult(
            name      = self.name,
            url       = video_url,
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
