# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from yaml import load, FullLoader

with open("AYAR.yml", "r", encoding="utf-8") as yaml_dosyasi:
    AYAR = load(yaml_dosyasi, Loader=FullLoader)

HOST       = AYAR["APP"]["HOST"]
PORT       = AYAR["APP"]["PORT"]
WORKERS    = AYAR["APP"]["WORKERS"]
CACHE_TIME = AYAR["APP"]["CACHE"] * 60