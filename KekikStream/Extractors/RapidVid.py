# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme  import Packer, HexCodec
import re

class RapidVid(ExtractorBase):
    name     = "RapidVid"
    main_url = "https://rapidvid.net"

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
                eval_jwsetup = re.search(r'\};\s*(eval\(function[\s\S]*?)var played = \d+;', istek.text)
                if not eval_jwsetup:
                    raise ValueError("JWPlayer setup not found.")

                unpacked_jwsetup = Packer.unpack(Packer.unpack(eval_jwsetup[1]))
                extracted_value  = re.search(r'file":"(.*)","label', unpacked_jwsetup)
                if not extracted_value:
                    raise ValueError("File URL not found in unpacked JWPlayer setup.")

                escaped_hex = extracted_value[1].replace("\\\\x", "")
                decoded_url = bytes.fromhex(escaped_hex).decode("utf-8")
        except Exception as hata:
            raise RuntimeError(f"Extraction failed: {hata}") from hata

        await self.close()
        return ExtractResult(
            name      = self.name,
            url       = decoded_url,
            referer   = self.main_url,
            headers   = {},
            subtitles = subtitles
        )