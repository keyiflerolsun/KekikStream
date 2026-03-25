# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re, json, base64

class Kodik(ExtractorBase):
    name     = "Kodik"
    main_url = "https://kodik.info"

    supported_domains = ["kodik.info", "kodik.cc", "kinosat.net"]

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        """
        Kodik videolarını çözümler.
        Kinogo.py'den taşınmıştır.
        """
        try:
            req = await self.async_cf_get(url, headers={'Referer': referer or self.main_url})

            v_type_match = re.search(r"vInfo\.type\s*=\s*'([^']+)'", req.text)
            if not v_type_match:
                return []

            v_type = v_type_match.group(1)
            v_hash = re.search(r"vInfo\.hash\s*=\s*'([^']+)'", req.text).group(1)
            v_id   = re.search(r"vInfo\.id\s*=\s*'([^']+)'", req.text).group(1)

            d_sign, pd_sign, ref_sign = None, None, None
            try:
                d_sign   = re.search(r"var d_sign\s*=\s*\"([^\"]+)\"", req.text).group(1)
                pd_sign  = re.search(r"var pd_sign\s*=\s*\"([^\"]+)\"", req.text).group(1)
                ref_sign = re.search(r"var ref_sign\s*=\s*\"([^\"]+)\"", req.text).group(1)
            except AttributeError:
                params_match = re.search(r"var urlParams\s*=\s*'([^']+)'", req.text)
                if params_match:
                    jsn      = json.loads(params_match.group(1))
                    d_sign   = jsn.get('d_sign')
                    pd_sign  = jsn.get('pd_sign')
                    ref_sign = jsn.get('ref_sign')

            if not all([d_sign, pd_sign, ref_sign]):
                return []

            api_url = "https://kodik.info/ftor"
            d_match = re.search(r"var domain\s*=\s*\"([^\"]+)\"", req.text)
            domain  = d_match.group(1) if d_match else "kodik.info"

            data = {
                "d"              : domain,
                "d_sign"         : d_sign,
                "pd"             : "kodik.info",
                "pd_sign"        : pd_sign,
                "ref"            : referer or "",
                "ref_sign"       : ref_sign,
                "bad_user"       : "true",
                "cdn_is_working" : "true",
                "type"           : v_type,
                "hash"           : v_hash,
                "id"             : v_id,
                "info"           : "{}"
            }
            headers = {
                'Accept'           : 'application/json, text/javascript, */*; q=0.01',
                'Content-Type'     : 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin'           : 'https://kodik.info',
                'Referer'          : url,
                'X-Requested-With' : 'XMLHttpRequest',
                'User-Agent'       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }

            api_req   = await self.async_cf_post(api_url, data=data, headers=headers)
            resp_json = api_req.json()

            def decode_kodik(hash_str):
                res = ''
                for char in hash_str:
                    if char.isalpha():
                        start = ord('a') if char.islower() else ord('A')
                        res += chr(start + (ord(char) - start + 18) % 26)
                    else:
                        res += char
                res += '=' * ((4 - len(res) % 4) % 4)
                try:
                    decoded = base64.b64decode(res).decode('utf-8', errors='strict')
                    if decoded.startswith('//'):
                        decoded = 'https:' + decoded
                    return decoded
                except Exception:
                    return None

            links   = resp_json.get("links", {})
            results = []
            for resolution, hashes in links.items():
                if isinstance(hashes, list) and len(hashes) > 0:
                    encoded_src = hashes[0].get("src")
                    if encoded_src:
                        decoded = decode_kodik(encoded_src)
                        if decoded:
                            results.append(ExtractResult(
                                name       = f"{self.name} {resolution}p",
                                url        = self.fix_url(decoded),
                                referer    = url,
                                user_agent = headers["User-Agent"]
                            ))
            return results
        except Exception:
            return []
