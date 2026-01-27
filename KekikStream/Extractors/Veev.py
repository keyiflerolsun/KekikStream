# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from contextlib       import suppress

class Veev(ExtractorBase):
    name     = "Veev"
    main_url = "https://veev.to"
    
    supported_domains = ["veev.to", "kinoger.to", "poophq.com", "doods.pro", "dood.so", "dood.li", "dood.wf", "dood.cx", "dood.sh", "dood.watch", "dood.pm", "dood.to", "dood.ws"]
    
    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    def veev_decode(self, encoded: str) -> str:
        if not encoded:
            return ""

        result = []
        # Python dictionary key integer, value string
        # Başlangıçta 0-255 ascii karakterleri
        lut = {i: chr(i) for i in range(256)}
        n = 256

        c = encoded[0]
        result.append(c)

        for char in encoded[1:]:
            code = ord(char)
            if code < 256:
                nc = char
            else:
                nc = lut.get(code, c + c[0])

            result.append(nc)
            lut[n] = c + nc[0]
            n += 1
            c = nc

        return "".join(result)

    def build_array(self, encoded: str) -> list[list[int]]:
        result   = []
        iterator = iter(encoded)

        def next_int_or_zero():
            try:
                char = next(iterator)
                if char.isdigit():
                    return int(char)
                return 0
            except StopIteration:
                return 0

        count = next_int_or_zero()
        while count != 0:
            row = []
            for _ in range(count):
                row.append(next_int_or_zero())
            result.append(list(reversed(row)))
            count = next_int_or_zero()

        return result

    def decode_url(self, encoded: str, rules: list[int]) -> str:
        text = encoded
        for r in rules:
            if r == 1:
                text = text[::-1]

            # Hex decode
            with suppress(Exception):
                # remove optional whitespace just in case
                clean_hex = "".join(text.split())
                arr = bytes.fromhex(clean_hex)
                # utf-8 decode, replace errors
                text = arr.decode('utf-8', errors='replace')

            text = text.replace("dXRmOA==", "")

        return text

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # URL'den ID çıkar
        # https://veev.to/e/lla8v3k6arev
        video_id = url.split("/")[-1]

        # Sayfayı al
        # Referer lazım mı? Genelde lazım olabilir.
        page_url = f"{self.main_url}/e/{video_id}"
        resp = await self.httpx.get(page_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        html = resp.text

        # Regex ile şifreli stringleri bul
        # Regex: [.\s'](?:fc|_vvto\[[^]]*)(?:['\]]*)?\s*[:=]\s*['"]([^'"]+)
        # Python regex için düzenleme gerekebilir.
        found_values = HTMLHelper(html).regex_all(r"[.\s'](?:fc|_vvto\[[^]]*)(?:['\]]*)?\s*[:=]\s*['\"]([^'\"]+)")

        if not found_values:
            raise ValueError(f"Veev: Token bulunamadı. {url}")

        # Kotlin kodunda sondan başlayıp deniyor (reversed)
        for f in reversed(found_values):
            try:
                ch = self.veev_decode(f)
                if ch == f:
                    continue # Decode olmadıysa geç

                # API Call
                dl_url   = f"{self.main_url}/dl?op=player_api&cmd=gi&file_code={video_id}&r={self.main_url}&ch={ch}&ie=1"
                api_resp = await self.httpx.get(dl_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

                data     = api_resp.json()
                file_obj = data.get("file")
                if not file_obj or file_obj.get("file_status") != "OK":
                    continue

                dv = file_obj.get("dv")
                # dv json string içinde s key'inde olabilir (Kotlin: getString("s"))
                # Ancak api yanıtını görmeden emin olamayız, json yapısına göre file->dv bir string mi object mi?
                # Kotlin: file.getJSONArray("dv").getJSONObject(0).getString("s")
                # Demek ki dv bir array

                encoded_dv = None
                if isinstance(dv, list) and len(dv) > 0:
                     if isinstance(dv[0], dict):
                         encoded_dv = dv[0].get("s")

                if not encoded_dv:
                    continue

                # Decode
                # rules = buildArray(ch)[0]
                rules = self.build_array(ch)[0]

                final_url = self.decode_url(self.veev_decode(encoded_dv), rules)

                if final_url.startswith("http"):
                     return ExtractResult(name=self.name, url=self.fix_url(final_url), referer=self.main_url)

            except Exception as e:
                # print(f"Veev Error: {e}")
                continue

        raise ValueError(f"Veev: Video URL'si çözülemedi. {url}")
