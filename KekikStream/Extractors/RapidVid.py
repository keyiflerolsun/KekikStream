# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer, HexCodec, StreamDecoder
import base64

class RapidVid(ExtractorBase):
    name     = "RapidVid"
    main_url = "https://rapidvid.net"

    # Birden fazla domain destekle
    supported_domains = ["rapidvid.net", "rapid.filmmakinesi.to"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {"Referer": referer or url}
        resp    = await self.async_cf_get(url, headers=headers)
        sel     = HTMLHelper(resp.text)

        subtitles = []
        for s_url, s_lang in sel.regex_all(r'captions","file":"([^\"]+)","label":"([^\"]+)"'):
            try:
                decoded_lang = s_lang.encode().decode('unicode_escape')
            except Exception:
                decoded_lang = s_lang
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
                # Check for direct m3u8 in text
                from KekikStream.Core import M3U8_FILE_REGEX
                video_url = sel.regex_first(M3U8_FILE_REGEX)

            if not video_url:
                raise ValueError(f"RapidVid: Video URL bulunamadı. {url}")

        except Exception as hata:
            raise RuntimeError(f"RapidVid: Extraction failed: {hata}") from hata

        return ExtractResult(
            name      = self.name,
            url       = self.fix_url(video_url),
            referer   = url,
            subtitles = subtitles
        )

    def decode_secret(self, data: str) -> str:
        """av('...') içindeki veriyi çözer."""
        # İlk base64 çözme işlemi
        decoded_bytes  = base64.b64decode(data)
        decoded_string = decoded_bytes.decode("utf-8")

        # Karakter kaydırma işlemi
        decrypted_chars = []
        for char in decoded_string:
            decrypted_chars.append(chr(ord(char) - 1))

        # Karakterleri birleştirip ikinci base64 çözme işlemini yapıyoruz
        intermediate_string = "".join(decrypted_chars)
        final_decoded_bytes = base64.b64decode(intermediate_string)

        return final_decoded_bytes.decode("utf-8")
