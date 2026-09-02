# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import re

# ── mevcut Türkçe site suffix'leri ────────────────────────────────────────────
_TITLE_SUFFIXES = [
    " izle",
    " full film",
    " filmini full",
    " full türkçe",
    " alt yazılı",
    " altyazılı",
    " tr dublaj",
    " hd türkçe",
    " türkçe dublaj",
    " azərbaycanca dublyaj",
    " azerbaycanca dublaj",
    " azərbaycanca",
    " dublyaj",
    " yeşilçam ",
    " erotik fil",
    " türkçe",
    " yerli",
    " tüekçe dublaj",
]

# ── generic uluslararası gürültü (trailing) ──────────────────────────────────
# baştaki SEO fiili: "Download X", "Watch X", "Ver X", "Nonton X"
_LEADING_NOISE = re.compile(r"^(?:download|watch|ver|assistir|regarder|nonton)\s+(?=\S)", re.I)
_SEO_TAIL      = re.compile(
    r"\s+(?:"
    r"\b(?:watch|watching)\s+(?:it\s+|the\s+full\s+)?(?:online|movie|documentary)\b"
    r"|\bfull\s*hd\b"
    r"|\bfull\s+movie\b"
    r"|\b(?:stream\s+)?kostenlos\s+online\b"
    r"|\bganzer\s+film\b"
    r"|\bonline\s+(?:free|now|kostenlos|anschauen|subtitrat)\b"
    r"|\bfree\s+(?:download|streaming|online)\b"
    r"|\bpel[ií]cula\s+completa\b"
    r"|\bsub\s+indo\b"
    r"|\bсмотреть\s+онлайн\b"
    r"|\bдивити(?:сь|ся)\s+онлайн\b"
    r")\b.*$",
    re.I,
)
_QUALITY_TAIL = re.compile(
    r"\s*[\[(]?\b(?:"
    r"DVD-?Scr|DVD-?Rip|HD-?Rip|HD-?CAM|CAM-?Rip|HD-?TS|HD-?TC|Pre-?DVD"
    r"|WEB-?DL|WEB-?Rip|Blu-?Ray|BR-?Rip|BD-?Rip|HDTV"
    r"|\d{3,4}p|2160p|4K|x264|x265|H\.?264|H\.?265|HEVC|AVC|10\s?bit|HDR|SDR|DDP?\d"
    r"|E-?Subs?|Multi\s+Audio|Dual\s+Audio"
    r")\b.*$",
    re.I,
)
# ` - 1. Staffel`, ` – Temporada 2`, ` - 3. Sezon`  (yalnız dash ile, sonda)
_DASH_SEASON_TAIL = re.compile(
    r"\s+[-–—]\s+\d+\.?\s*(?:staffel|sezon|temporada|season)\b\s*\d*\s*$",
    re.I,
)

# ── trailing bölüm belirteci (bölüm bileşeni ŞART, bare season'a dokunmaz) ────
_TRAILING_EPISODE_MARKER = re.compile(
    r"\s*[-–—:|]?\s*"
    r"(?:"
    r"s\d{1,2}\s*e\d{1,3}"                                  # S01E02
    r"|\d{1,2}\s*x\s*\d{1,3}"                               # 1x02
    r"|(?:season\s*\d+\s*[,\-–]?\s*)?episode\s*\d+"         # [Season N, ]Episode M
    r"|(?:\d+\.?\s*(?:sezon|season)\s*)?\d+\.?\s*b[öo]l[üu]m"  # [N. Sezon ]N. Bölüm
    r"|epis[oó]di[oe]\s*\d+"                                # Episodio N (es/pt)
    r"|cap[ií]tulo\s*\d+"                                   # Capítulo N
    r"|الحلقة\s*\d+"          # الحلقة N (ar)
    r")\s*$",
    re.I,
)

# Başlık içindeki sezon belirteci — TMDB araması için sezonu ayırmakta kullanılır
# ("Grand Blue Season 3" → ("Grand Blue", 3)). Başlıktan sezonu SİLMEZ (bkz.
# `MetadataHelper.extract_season_from_title`); clean_title bunu korur.
SEASON_IN_TITLE = re.compile(
    r"\s*\(?\b(?:(\d+)(?:\.|th|rd|nd|st)?\s*(?:sezon|season)|(?:sezon|season)\s*(\d+))\b\)?",
    re.I,
)

# ── bölüm-başlığı belirteçleri (Episode.title yolu) ──────────────────────────
# NOT: `PluginModels` ve `MetadataHelper` bunları buradan import eder.
# Çok dilli "bölüm" / "sezon" sözcükleri (TR / EN / ES / PT / FR / DE / PL /
# RU / UK / AR). Latin "series" KASITLI dışarıda — gerçek eser adlarında geçiyor.
_EP_WORD  = r"(?:b[öo]l[üu]m|epis[oó]di[oe]|[eé]pisode|cap[ií]tulo|folge|odcinek|сери[яйи]|сері[яїй]|эпизод|епізод|випуск|выпуск|الحلقة|ep\.?)"
_SEA_WORD = r"(?:sezon|season|staffel|temporada|sezona|сезон)"

EPISODE_DISPLAY_PREFIX = re.compile(
    rf"^(?:s\d{{1,2}}e\d{{1,3}}|\d{{1,2}}x\d{{1,3}}|\d+\.?\s*{_EP_WORD}|{_EP_WORD}\s*\d+)\s*[-–:]\s*(?P<title>.+)$",
    re.I,
)
GENERIC_EPISODE_TITLE = re.compile(
    rf"^(?:"
    rf"s\d{{1,2}}e\d{{1,3}}"
    rf"|\d{{1,2}}x\d{{1,3}}"
    rf"|\d+[.\-\s]*{_EP_WORD}"
    rf"|{_EP_WORD}\s*\d+"
    rf"|\d+[.\-\s]*{_SEA_WORD}"
    rf"|{_SEA_WORD}\s*\d+"
    rf"|.+?\s+\d+[.\s]*{_SEA_WORD}\s+\d+[.\s]*{_EP_WORD}"
    rf"|.+?\s+الحلقة\s*\d+(?:\s*-\s*[^-]+)?"
    rf")$",
    re.I,
)


def clean_title(title: str | None) -> str | None:
    """Başlıktan SEO / kalite / dil suffix'lerini ve dash-ayraçlı sezon ekini temizler."""
    if not title or not isinstance(title, str):
        return title

    cleaned = " ".join(title.split())
    if not cleaned:
        return None

    original = cleaned

    # "Film(2024)" → "Film (2024)"
    cleaned = re.sub(r"(\S)\(", r"\1 (", cleaned)

    cleaned = _LEADING_NOISE.sub("", cleaned)
    for suffix in _TITLE_SUFFIXES:
        cleaned = re.sub(rf"{re.escape(suffix)}.*$", "", cleaned, flags=re.IGNORECASE).strip()

    cleaned = _SEO_TAIL.sub("", cleaned)
    cleaned = _DASH_SEASON_TAIL.sub("", cleaned)
    cleaned = _QUALITY_TAIL.sub("", cleaned)
    cleaned = cleaned.strip(" -–—|:")

    # Aşırı temizlik koruması: elde anlamlı bir şey kalmadıysa orijinali bırak.
    return cleaned if len(cleaned) >= 2 else (original or None)


def strip_title_episode_marker(title: str | None) -> str | None:
    """Eser/kart başlığının sonundaki BÖLÜM belirtecini kaldırır.

    Bölüm bileşeni şarttır: `Episode 5`, `5. Bölüm`, `1. Sezon 5. Bölüm`,
    `S01E05`. Tek başına `Season 3` / `2. Sezon` KORUNUR (ayrı katalog
    girdisinin gerçek adı olabilir).
    """
    if not title or not isinstance(title, str):
        return title

    stripped = _TRAILING_EPISODE_MARKER.sub("", " ".join(title.split())).strip(" -–—:|")
    return stripped if len(stripped) >= 2 else title


def clean_episode_title(series_title: str | None, title: str | None) -> str | None:
    """Bölüm başlığından dizi-adı / routing önekini siler; sırf numarayı başlık sayma.

    Gerçek bir bölüm adı yoksa `None` döner (uydurma ad üretilmez).
    """
    if not title:
        return None
    cleaned = " ".join(title.split())

    if series_title:
        st = " ".join(series_title.split())
        low, stl = cleaned.casefold(), st.casefold()
        if low.startswith(f"{stl} - ") or low.startswith(f"{stl} – "):
            cleaned = cleaned[len(st) + 3:].strip()
        elif low.startswith(stl):
            rest = cleaned[len(st):].lstrip(" -–—:|.")
            # "Dizi 5. Bölüm" → sadece routing etiketi kaldıysa gerçek ad yok
            if rest and GENERIC_EPISODE_TITLE.fullmatch(rest):
                return None

    if match := EPISODE_DISPLAY_PREFIX.fullmatch(cleaned):
        cleaned = match.group("title").strip()

    cleaned = _TRAILING_EPISODE_MARKER.sub("", cleaned).strip(" -–—:|")
    return None if not cleaned or GENERIC_EPISODE_TITLE.fullmatch(cleaned) else cleaned


if __name__ == "__main__":
    # Koruma vakaları — gerçek ad parçaları asla silinmemeli
    assert clean_title("Sword Art Online: Progressive Movie") == "Sword Art Online: Progressive Movie"
    assert clean_title("La Gioia - Süchtig nach Dir") == "La Gioia - Süchtig nach Dir"
    assert clean_title("Heir-Conditioned") == "Heir-Conditioned"
    assert clean_title("Harry Potter and the Deathly Hallows: Part 2 (2011)") == "Harry Potter and the Deathly Hallows: Part 2 (2011)"
    assert clean_title("Grand Blue Season 3") == "Grand Blue Season 3"
    assert clean_title("Bigg Boss (Season 1) (2026)") == "Bigg Boss (Season 1) (2026)"

    # SEO / kalite / dash-sezon suffix'leri silinmeli
    assert clean_title("Öngörü Full HD") == "Öngörü", clean_title("Öngörü Full HD")
    assert clean_title("The Odyssey Watch Movie Online Free") == "The Odyssey", clean_title("The Odyssey Watch Movie Online Free")
    assert clean_title("Lanterns - 1 Staffel") == "Lanterns", clean_title("Lanterns - 1 Staffel")
    assert clean_title("Hi (2026) Telugu Dubbed DVDScr") == "Hi (2026) Telugu Dubbed", clean_title("Hi (2026) Telugu Dubbed DVDScr")
    assert clean_title("Money Heist All Episodes HDRip ESub") == "Money Heist All Episodes", clean_title("Money Heist All Episodes HDRip ESub")
    assert clean_title("Maniac Cop izle") == "Maniac Cop"
    assert clean_title("Download The Orphans (2025) 1080p x264") == "The Orphans (2025)", clean_title("Download The Orphans (2025) 1080p x264")
    assert clean_title("Дюна смотреть онлайн") == "Дюна", clean_title("Дюна смотреть онлайн")
    assert clean_title("Superman | Full Movie") == "Superman", clean_title("Superman | Full Movie")
    assert clean_title("Watchmen") == "Watchmen"  # baştaki "Watch" tek kelime, dokunma

    # trailing bölüm belirteci
    assert strip_title_episode_marker("Kurulus Orhan Episode 26") == "Kurulus Orhan", strip_title_episode_marker("Kurulus Orhan Episode 26")
    assert strip_title_episode_marker("Tuzlu Kahve 1.Bölüm") == "Tuzlu Kahve", strip_title_episode_marker("Tuzlu Kahve 1.Bölüm")
    assert strip_title_episode_marker("Pull Strings - 1. Sezon 24. Bölüm") == "Pull Strings", strip_title_episode_marker("Pull Strings - 1. Sezon 24. Bölüm")
    assert strip_title_episode_marker("Arafta – Episode 114") == "Arafta", strip_title_episode_marker("Arafta – Episode 114")
    assert strip_title_episode_marker("Grand Blue Season 3 - Episodio 9") == "Grand Blue Season 3", strip_title_episode_marker("Grand Blue Season 3 - Episodio 9")
    # bare season KORUNUR
    assert strip_title_episode_marker("Grand Blue Season 3") == "Grand Blue Season 3"
    assert strip_title_episode_marker('"Oshi no Ko" 2. Sezon') == '"Oshi no Ko" 2. Sezon'
    assert strip_title_episode_marker("Bigg Boss (Season 1) (2026)") == "Bigg Boss (Season 1) (2026)"

    # bölüm başlığı
    assert clean_episode_title("Kurulus Orhan", "Kurulus Orhan - The Siege") == "The Siege"
    assert clean_episode_title("Dizi", "5. Bölüm") is None
    assert clean_episode_title("Dizi", "Episode 12") is None
    assert clean_episode_title("Tuzlu Kahve", "Tuzlu Kahve 1. Bölüm") is None
    assert clean_episode_title("Kurulus Orhan", "Kurulus Orhan Episode 26") is None
    assert clean_episode_title("Dizi", "Dizi - Gerçek Ad - 5. Bölüm") == "Gerçek Ad"
    assert clean_episode_title(None, "Gerçek Bölüm Adı") == "Gerçek Bölüm Adı"
    assert clean_episode_title("The Boys", "The Boys Strike Back") == "The Boys Strike Back"
    # çok dilli routing etiketleri → gerçek ad değil → None
    assert clean_episode_title(None, "Серия 5") is None
    assert clean_episode_title(None, "Серія 12") is None
    assert clean_episode_title(None, "Épisode 3") is None
    assert clean_episode_title(None, "Capítulo 7") is None
    assert clean_episode_title(None, "Folge 2") is None
    assert clean_episode_title("Anya", "1x1 - Operasyon Strix") == "Operasyon Strix"
    # gerçek adlar korunur
    assert clean_episode_title(None, "A Series of Unfortunate Events") == "A Series of Unfortunate Events"
    assert clean_episode_title(None, "The Serpent") == "The Serpent"

    print("TitleHelper: tüm testler geçti ✓")
