# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Crypto.Cipher    import AES
from Crypto.Util      import Counter
import re, json, hashlib, base64


class Abyss(ExtractorBase):
    name              = "Abyss"
    main_url          = "https://abyss.to"
    supported_domains = ["abyssplayer.com", "abysscdn.com", "abyss.to"]

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult:
        # Standardize headers to mimic browser traffic
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if referer:
            headers["Referer"] = referer

        # Fetch the embed page (this follows redirects like abyssplayer.com -> abysscdn.com/?v=...)
        resp = await self.httpx.get(url, headers=headers, follow_redirects=True)
        html = resp.text

        # Find the encoded "datas" script payload
        datas_match = re.search(r'const datas\s*=\s*["\']([^"\']+)["\']', html)
        if not datas_match:
            raise ValueError(f"Abyss: Encrypted data payload not found. URL: {url}")

        try:
            # Decode using latin-1 to safely handle raw binary bytes without raising UTF-8 errors
            payload_str = base64.b64decode(datas_match.group(1)).decode('latin-1')
            payload     = json.loads(payload_str)
        except Exception as e:
            raise ValueError(f"Abyss: Failed to decode base64 data payload. Error: {e}")

        slug    = payload.get("slug")
        md5_id  = payload.get("md5_id")
        user_id = payload.get("user_id")
        media   = payload.get("media")

        if not all([slug, md5_id, user_id, media]):
            raise ValueError("Abyss: Incomplete payload parameters")

        md5_id  = str(md5_id)
        user_id = str(user_id)

        # AES-CTR key and counter calculation
        key_string = f"{user_id}:{slug}:{md5_id}"
        h          = hashlib.md5(key_string.encode('utf-8')).hexdigest()

        key_bytes     = h.encode('utf-8')
        counter_bytes = h[:16].encode('utf-8')

        ciphertext = media.encode('latin-1')

        try:
            # Initialize AES-CTR decryptor
            ctr           = Counter.new(128, initial_value=int.from_bytes(counter_bytes, byteorder='big'))
            cipher        = AES.new(key_bytes, AES.MODE_CTR, counter=ctr)
            decrypted_str = cipher.decrypt(ciphertext).decode('utf-8', errors='ignore')
            decrypted     = json.loads(decrypted_str)
        except Exception as e:
            raise ValueError(f"Abyss: Decryption failed. Error: {e}")

        # Extract streams
        results     = []
        mp4_data    = decrypted.get("mp4", {})
        sources     = mp4_data.get("sources", [])
        frist_datas = mp4_data.get("fristDatas", [])

        # Create a resolution mapping: res_id -> label (e.g. 3 -> "480p", 4 -> "720p")
        res_map = {}
        for src in sources:
            res_id = src.get("res_id")
            label  = src.get("label")
            if res_id and label:
                res_map[res_id] = label

        # Map each stream URL from fristDatas
        for item in frist_datas:
            stream_url = item.get("url")
            if not stream_url:
                continue

            res_id = item.get("res_id")
            label  = res_map.get(res_id, f"Quality {res_id}")

            results.append(ExtractResult(
                name    = f"{self.name} ({label})",
                url     = stream_url,
                referer = url,
            ))

        if not results:
            raise ValueError("Abyss: No playable stream links found in decrypted media payload")

        return results
