# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""
Extractor'lar için ortak mixin'ler / base class'lar.

Sık tekrarlanan Extractor pattern'lerini tek noktada toplar:
  - SecuredLinkExtractor  : securedLink POST API (HDPlayerSystem, YildizKisaFilm, vb.)
  - PackedJSExtractor     : eval(function(p,a,c,k,e,d)) unpack (Filemoon, StreamWish, Vtbe, vb.)
  - BePlayerExtractor     : bePlayer AES decrypt (HDMomPlayer, HotStream, DonilasPlay, vb.)
  - PlaylistAPIExtractor  : file → playlist API (Sobreatsesuyp, TRsTX)
  - NonceDecryptExtractor : Nonce + external key decrypt (MegaCloud, Videostr)
"""

from .ExtractorBase   import ExtractorBase
from .ExtractorModels import ExtractResult, Subtitle
from ..Helpers        import HTMLHelper
from Kekik.Sifreleme  import Packer, AESManager
from urllib.parse     import quote
import json, contextlib, re


# ============================================
# Ortak Regex Sabitleri
# ============================================

PACKED_REGEX    = r'(eval\s*\(\s*function[\s\S]+?)<\/script>'
FILE_REGEX      = r'file\s*:\s*["\']([^"\']+)["\']'
SOURCES_REGEX   = r'sources\s*:\s*\[\s*\{\s*file\s*:\s*["\']([^"\']+)["\']'
M3U8_FILE_REGEX = r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
BEPLAYER_REGEX  = r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);"
CAPTIONS_REGEX  = r'captions","file":"([^\"]+)","label":"([^\"]+)"'
PLAYERJS_SUB_RE = r'\[(.*?)\](https?://[^\s\",]+)'


# ============================================
# SecuredLinkExtractor
# ============================================

class SecuredLinkExtractor(ExtractorBase):
    """
    securedLink POST API kullanan Extractor'lar için ortak base class.

    Kullanım:
        class HDPlayerSystem(SecuredLinkExtractor):
            name     = "HDPlayerSystem"
            main_url = "https://hdplayersystem.com"

    Uyumlu: HDPlayerSystem, YildizKisaFilm, ve benzer yapılar.
    """

    def _parse_video_id(self, url: str) -> str:
        """URL'den video ID'sini çıkar."""
        return url.split("video/")[-1] if "video/" in url else url.split("?data=")[-1]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref  = referer or self.main_url
        v_id = self._parse_video_id(url)

        resp = await self.httpx.post(
            url     = f"{self.main_url}/player/index.php?data={v_id}&do=getVideo",
            data    = {"hash": v_id, "r": ref},
            headers = {"Referer": ref, "X-Requested-With": "XMLHttpRequest"}
        )

        m3u8_url = resp.json().get("securedLink")
        if not m3u8_url:
            raise ValueError(f"{self.name}: Video URL bulunamadı. {url}")

        return ExtractResult(name=self.name, url=m3u8_url, referer=ref)


# ============================================
# PackedJSExtractor
# ============================================

class PackedJSExtractor(ExtractorBase):
    """
    eval(function(p,a,c,k,e,d)) packed JS içinden m3u8 çıkaran Extractor'lar için base class.

    Alt sınıflarda override edilebilecek alanlar:
        url_pattern : str  — Unpack sonrası video URL'sini bulmak için regex

    Uyumlu: Filemoon, StreamWish, VidHide, Vtbe, Vidora, CloseLoad, vb.
    """

    url_pattern = SOURCES_REGEX  # Alt sınıflar override edebilir

    def unpack_and_find(self, html_text: str, pattern: str | None = None) -> str | None:
        """
        HTML içinden packed JS'yi bulup unpack eder ve video URL'sini çıkarır.

        Returns:
            Video URL veya None
        """
        sel    = HTMLHelper(html_text)
        target = pattern or self.url_pattern

        # 1. Packed script bul ve unpack et
        packed = sel.regex_first(PACKED_REGEX)
        if packed:
            with contextlib.suppress(Exception):
                unpacked = Packer.unpack(packed)
                if url := HTMLHelper(unpacked).regex_first(target):
                    return url

        # 2. Fallback: Direkt HTML'den ara (FILE_REGEX çok geniş, M3U8_FILE_REGEX daha güvenli)
        return sel.regex_first(target) or sel.regex_first(M3U8_FILE_REGEX)


# ============================================
# BePlayerExtractor
# ============================================

class BePlayerExtractor(ExtractorBase):
    """
    bePlayer AES şifreli içerik kullanan Extractor'lar için base class.

    Override edilebilecek alan:
        beplayer_regex : str — bePlayer çağrısını yakalamak için regex

    Uyumlu: HDMomPlayer, HotStream, DonilasPlay, LuciferPlays, MixPlayHD
    """

    beplayer_regex = BEPLAYER_REGEX

    def decrypt_beplayer(self, html_text: str) -> tuple[str | None, list[Subtitle], dict | None]:
        """
        bePlayer AES şifresini çözer.

        Returns:
            (video_url, subtitles, raw_data)
        """
        sel       = HTMLHelper(html_text)
        m3u8_url  = None
        subtitles = []
        raw_data  = None

        match = sel.regex_first(self.beplayer_regex, group=None)
        if not match:
            return None, [], None

        pass_val, data_val = match
        with contextlib.suppress(Exception):
            decrypted = AESManager.decrypt(data_val, pass_val)

            try:
                data     = json.loads(decrypted)
                raw_data = data
                m3u8_url = data.get("video_location")

                # schedule.client içinde olabilir (MixPlayHD pattern)
                if not m3u8_url:
                    client_data = data.get("schedule", {}).get("client", "")
                    m3u8_url    = HTMLHelper(client_data).regex_first(r'"video_location":"([^"]+)"')

                # Altyazıları çıkar
                for sub in data.get("strSubtitles", []):
                    if "Forced" not in sub.get("label", ""):
                        subtitles.append(Subtitle(
                            name = sub.get("label", "TR").upper(),
                            url  = self.fix_url(sub.get("file", ""))
                        ))

            except json.JSONDecodeError:
                m3u8_url = HTMLHelper(decrypted).regex_first(r'"video_location":"([^"]+)"')

        return m3u8_url, subtitles, raw_data

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        m3u8_url, subtitles, _ = self.decrypt_beplayer(resp.text)

        # Fallback: Düz JS içinde file: ara
        if not m3u8_url:
            m3u8_url = sel.regex_first(r'file\s*:\s*"([^"]+)"')

        if not m3u8_url:
            raise ValueError(f"{self.name}: Video linki bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = self.fix_url(m3u8_url),
            referer   = url,
            subtitles = subtitles
        )


# ============================================
# PlaylistAPIExtractor
# ============================================

class PlaylistAPIExtractor(ExtractorBase):
    """
    file → playlist POST API kullanan Extractor'lar için base class.

    Uyumlu: Sobreatsesuyp, TRsTX
    """

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult:
        ref = referer or self.main_url
        self.httpx.headers.update({"Referer": ref})

        resp = await self.httpx.get(url)
        path = HTMLHelper(resp.text).regex_first(r'file":"([^\"]+)')
        if not path:
            raise ValueError(f"{self.name}: File path bulunamadı. {url}")

        post_resp = await self.httpx.post(f"{self.main_url}/{path.replace(chr(92), '')}")
        data_list = post_resp.json()[1:] if isinstance(post_resp.json(), list) else []

        results = []
        for item in data_list:
            title = item.get("title")
            file  = item.get("file")
            if title and file:
                playlist_resp = await self.httpx.post(f"{self.main_url}/playlist/{file.lstrip('/')}.txt")
                results.append(ExtractResult(
                    name    = f"{self.name} - {title}",
                    url     = playlist_resp.text,
                    referer = self.main_url
                ))

        if not results:
            raise ValueError(f"{self.name}: Video bulunamadı. {url}")

        return results[0] if len(results) == 1 else results


# ============================================
# NonceDecryptExtractor
# ============================================

class NonceDecryptExtractor(ExtractorBase):
    """
    Nonce + external key + Google Apps Script ile decrypt eden Extractor'lar için base class.

    Alt sınıflarda override:
        key_name   : str — keys.json'daki anahtar adı ("mega" veya "vidstr")
        embed_path : str — API endpoint yolu (default: "embed-1/v3/e-1")

    Uyumlu: MegaCloud, Videostr
    """

    key_name   = "mega"
    embed_path = "embed-1/v3/e-1"

    _keys_url   = "https://raw.githubusercontent.com/yogesh-hacker/MegacloudKeys/refs/heads/main/keys.json"
    _decode_api = "https://script.google.com/macros/s/AKfycbxHbYHbrGMXYD2-bC-C43D3njIbU-wGiYQuJL61H4vyy6YVXkybMNNEPJNPPuZrD1gRVA/exec"

    def _find_nonce(self, html_text: str) -> str | None:
        """HTML'den nonce değerini çıkar."""
        sel = HTMLHelper(html_text)

        # 1. meta tag
        if nonce := sel.select_attr("meta[name='_gg_fb']", "content"):
            return nonce

        # 2. 48 karakterlik token
        if nonce := sel.regex_first(r"\b[a-zA-Z0-9]{48}\b"):
            return nonce

        # 3. 16x3 birleştirme
        if m := re.search(r"\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b", html_text, re.DOTALL):
            return m.group(1) + m.group(2) + m.group(3)

        return None

    # ISO 639 kısa koddan dil adına dönüştürme
    _LANG_MAP = {
        "ara": "Arabic",      "bul": "Bulgarian",  "cze": "Czech",      "dan": "Danish",
        "dut": "Dutch",       "eng": "English",     "est": "Estonian",   "fin": "Finnish",
        "fre": "French",      "ger": "German",      "gre": "Greek",     "heb": "Hebrew",
        "hin": "Hindi",       "hrv": "Croatian",    "hun": "Hungarian", "ice": "Icelandic",
        "ind": "Indonesian",  "ita": "Italian",     "jpn": "Japanese",  "kor": "Korean",
        "lat": "Latvian",     "lit": "Lithuanian",  "may": "Malay",     "nob": "Norwegian",
        "nor": "Norwegian",   "per": "Persian",     "pol": "Polish",    "por": "Portuguese",
        "rum": "Romanian",    "rus": "Russian",     "slv": "Slovenian", "spa": "Spanish",
        "swe": "Swedish",     "tha": "Thai",        "tur": "Turkish",   "ukr": "Ukrainian",
        "vie": "Vietnamese",  "chi": "Chinese",     "zho": "Chinese",   "srp": "Serbian",
        "scc": "Serbian",     "alb": "Albanian",    "bos": "Bosnian",   "cat": "Catalan",
        "mac": "Macedonian",  "geo": "Georgian",    "arm": "Armenian",  "ben": "Bengali",
        "tam": "Tamil",       "tel": "Telugu",      "mal": "Malayalam", "mar": "Marathi",
        "pan": "Punjabi",     "urd": "Urdu",        "fil": "Filipino",  "msa": "Malay",
    }

    def _lang_from_url(self, url: str) -> str | None:
        """VTT URL dosya adından ISO 639 dil kodunu çıkar (ör: 'tur-29.vtt' → 'Turkish')."""
        m = re.search(r"/([a-z]{2,3})-\d+\.vtt", url)
        if m:
            return self._LANG_MAP.get(m.group(1))
        return None

    def _parse_subtitles(self, data: dict) -> list[Subtitle]:
        """API yanıtından altyazıları çıkar."""
        tracks = [t for t in data.get("tracks", []) if t.get("kind") in ["captions", "subtitles"]]
        if not tracks:
            return []

        # Tüm label'lar aynıysa (API hatası), URL'den dil adı çıkarmayı dene
        labels       = [t.get("label", "") for t in tracks]
        all_same     = len(set(labels)) <= 1 and len(tracks) > 1
        first_is_bad = labels[0].lower() in ("abkhaz", "unknown", "") if labels else False
        use_url_lang = all_same or first_is_bad

        return [
            Subtitle(
                name = (self._lang_from_url(t.get("file", "")) or t.get("label", "Altyazı")) if use_url_lang else t.get("label", "Altyazı"),
                url  = t.get("file")
            )
                for t in tracks
        ]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        v_id     = url.split("?")[0].split("/")[-1]
        base_url = self.get_base_url(url)
        headers  = {"Referer": base_url, "X-Requested-With": "XMLHttpRequest"}

        resp = await self.httpx.get(url, headers=headers, follow_redirects=True)

        nonce = self._find_nonce(resp.text)
        if not nonce:
            raise ValueError(f"{self.name}: Nonce bulunamadı. {url}")

        # Embed path'i URL'den al veya varsayılanı kullan
        embed_match = re.search(r"(embed-\d+/v\d+/e-\d+)", url)
        path        = embed_match.group(1) if embed_match else self.embed_path

        api_resp = await self.httpx.get(f"{base_url}/{path}/getSources?id={v_id}&_k={nonce}", headers=headers)
        data     = api_resp.json()

        enc_file = data.get("sources", [{}])[0].get("file")
        if not enc_file:
            raise ValueError(f"{self.name}: Kaynak bulunamadı.")

        m3u8_url = None
        if ".m3u8" in enc_file:
            m3u8_url = enc_file
        else:
            with contextlib.suppress(Exception):
                key_resp = await self.httpx.get(self._keys_url)
                secret   = key_resp.json().get(self.key_name)
                if secret:
                    dec_resp = await self.httpx.get(
                        url    = self._decode_api,
                        params = {
                            "encrypted_data" : enc_file,
                            "nonce"          : nonce,
                            "secret"         : secret
                        }
                    )
                    if m := re.search(r'"file":"(.*?)"', dec_resp.text):
                        m3u8_url = m.group(1).replace("\\/", "/")

        if not m3u8_url:
            raise ValueError(f"{self.name}: Video URL bulunamadı. {url}")

        subtitles = self._parse_subtitles(data)

        return ExtractResult(name=self.name, url=m3u8_url, referer=f"{base_url}/", subtitles=subtitles)
