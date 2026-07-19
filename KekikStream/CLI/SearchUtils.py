# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import re
import unicodedata

_TR_CHAR_MAP = str.maketrans({
    "ı" : "i",
    "İ" : "i",
    "ş" : "s",
    "Ş" : "s",
    "ğ" : "g",
    "Ğ" : "g",
    "ü" : "u",
    "Ü" : "u",
    "ö" : "o",
    "Ö" : "o",
    "ç" : "c",
    "Ç" : "c",
})

def normalize_search_text(value: str) -> str:
    if not value:
        return ""
    text = str(value).translate(_TR_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    return re.sub(r"\s+", " ", text).strip()

def tokenize_search_text(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", normalize_search_text(value)) if token]

def calculate_similarity_score(title: str, query: str) -> int:
    t = normalize_search_text(title)
    q = normalize_search_text(query)
    if not t or not q:
        return 0

    if t == q:
        return 1000

    score = 0

    if t.startswith(q):
        score = max(score, 850 - min(200, len(t) - len(q)))

    idx = t.find(q)
    if idx != -1:
        score = max(score, 700 - min(250, idx * 4) - min(100, max(0, len(t) - len(q))))

    q_tokens = tokenize_search_text(q)
    t_tokens = tokenize_search_text(t)
    if q_tokens and t_tokens:
        common         = sum(1 for token in q_tokens if token in t_tokens)
        coverage_score = int((common / len(q_tokens)) * 520)
        if t.startswith(q_tokens[0]):
            coverage_score += 80
        score = max(score, coverage_score)

    return score
