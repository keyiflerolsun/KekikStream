# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from urllib.parse     import urlparse
import re, json, base64

class Alloha(ExtractorBase):
    name     = "Alloha"
    main_url = "https://alloha.tv"

    supported_domains = [
        "alloha.tv",
        "cinemar.vip",
        "cinemar.cc",
        "fotpro.net",
        "fotpro135alto.com",
        "alohastreamalto.com",
        "alohastream.com",
    ]

    async def get_playlist(self, iframe_url: str, referer: str) -> list[dict]:
        """
        Alloha oynatma listesini (sezon/bölüm/film) döndürür.
        Kinogo.py'den taşınmıştır.
        """
        try:
            req    = await self.async_cf_get(iframe_url, headers={"Referer": referer})
            i_text = req.text

            data = None

            # 1. Base64 JSON blobs
            b64_matches = re.findall(r'[\'\"](ey[a-zA-Z0-9\+\/]{50,}=*)[\'\"]', i_text)
            if b64_matches:
                for b64 in b64_matches:
                    try:
                        b_clean = re.sub(r'[^A-Za-z0-9+/=_\-]', '', b64)
                        b_clean += '=' * ((4 - len(b_clean) % 4) % 4)
                        raw = base64.b64decode(b_clean).decode('utf-8', errors='ignore')
                        if '"file"' in raw or '"folder"' in raw:
                            data = json.loads(raw)
                            if data:
                                break
                    except Exception:
                        pass

            # 2. playerConfigs (Alloha v2)
            if not data:
                p_configs = re.search(r'playerConfigs\s*=\s*({.*?});', i_text, re.DOTALL)
                if p_configs:
                    try:
                        conf  = json.loads(p_configs.group(1))
                        f_val = conf.get("file", "").replace("\\/", "/")
                        f_key = conf.get("key", "")

                        if f_val and f_key:
                            p_url       = urlparse(iframe_url)
                            base_domain = ".".join(p_url.netloc.split(".")[-2:])

                            if f_val.startswith("~"):
                                token   = re.sub(r'^~|!!$', '', f_val)
                                txt_url = f"https://vid11.{base_domain}/playlist/{token}.txt"
                            elif "/playlist/" in f_val:
                                txt_url = f"https://vid11.{base_domain}{f_val}"
                            else:
                                txt_url = ""

                            if txt_url:
                                headers = {
                                    "X-CSRF-TOKEN" : f_key,
                                    "Referer"      : iframe_url
                                }
                                txt_resp = await self.async_cf_post(txt_url, headers=headers)
                                if txt_resp.status_code == 200:
                                    try:
                                        data = json.loads(txt_resp.text)
                                    except Exception:
                                        if txt_resp.text.startswith("http"):
                                            return [{"type": "movie", "link": txt_resp.text, "title": "Alloha (v2)"}]
                                else:
                                    pass

                        elif '"' in f_val or "[" in f_val:
                            data = json.loads(f_val)
                    except Exception:
                        pass

            # 3. Old encrypted strings
            if not data:
                match = re.search(r'\"file\"\:\"(.*?)\"', i_text)
                if match:
                    encoded = match.group(1).replace('//_//', '')
                    if encoded.startswith('#2'):
                        e  = encoded[2:]
                        dm = e[0:2]
                        try:
                            delim = chr(int(dm))
                        except Exception:
                            delim = '#'

                        parts  = e[2:].split(delim)
                        result = []
                        for p in parts:
                            if not p: continue
                            try:
                                t = int(p[-1])
                                if len(p) > 32:
                                    result.append(p[2*t : 2*t + len(p) - 3*t - 1] + p[0:t])
                                else:
                                    result.append(p)
                            except Exception:
                                result.append(p)
                        encoded = "".join(result)
                        # Normally here you'd check if encoded is JSON, but usually for old style it's just the URL or JSON.
                        # For now, following Kinogo.py logic.

            if not data or not isinstance(data, list):
                return []

            playlist = []
            for item in data:
                if isinstance(item, dict) and "folder" in item:
                    # Series Season
                    s_id    = item.get("id", "1")
                    s_match = re.search(r'(\d+)', str(s_id))
                    s_num   = int(s_match.group(1)) if s_match else 1

                    for ep in item["folder"]:
                        if not isinstance(ep, dict):
                            continue

                        e_id    = ep.get("id", ep.get("episode", ep.get("title", "1")))
                        e_match = re.search(r'(\d+)', str(e_id))
                        e_num   = int(e_match.group(1)) if e_match else 1

                        voices = []
                        if "folder" in ep and isinstance(ep["folder"], list):
                            for v in ep["folder"]:
                                if isinstance(v, dict):
                                    voices.append({
                                        "title" : v.get("title", "Unknown"),
                                        "link"  : self.fix_url(v.get("file") or v.get("link") or "")
                                    })
                                elif isinstance(v, list) and len(v) >= 2:
                                    voices.append({
                                        "title" : str(v[0]),
                                        "link"  : self.fix_url(str(v[1]))
                                    })
                        else:
                            v_link = ep.get("file") or ep.get("link") or ""
                            if v_link:
                                voices.append({
                                    "title" : item.get("title", ""),
                                    "link"  : self.fix_url(v_link)
                                })

                        playlist.append({
                            "type"    : "series",
                            "season"  : s_num,
                            "episode" : e_num,
                            "title"   : ep.get("title", "Kinogo"),
                            "voices"  : voices
                        })
                elif isinstance(item, dict):
                    # Movie
                    m_link = item.get("file") or item.get("link") or ""
                    if m_link and isinstance(m_link, str) and m_link.startswith("http"):
                        playlist.append({
                            "type"  : "movie",
                            "title" : item.get("title", "Kinogo"),
                            "link"  : m_link
                        })
            return playlist
        except Exception:
            return []

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        playlist = await self.get_playlist(url, referer)
        results  = []

        for item in playlist:
            if item.get("type") == "movie":
                title = re.sub(r'<[^>]+>', '', item.get('title', '')).strip()
                name  = title if title else "Alloha"

                link_str = item.get("link", "")
                for l in link_str.split(','):
                    m = re.search(r'\[(.*?)\](.*)', l)
                    if m:
                        results.append(ExtractResult(
                            name    = f"{name} {m.group(1)}",
                            url     = self.fix_url(m.group(2)),
                            referer = url
                        ))
                    else:
                        results.append(ExtractResult(
                            name    = name,
                            url     = self.fix_url(l),
                            referer = url
                        ))
        return results
