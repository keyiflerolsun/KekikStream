# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from httpx    import AsyncClient
from Core     import kekik_cache
from Settings import CACHE_TIME

@kekik_cache(ttl=CACHE_TIME)
async def ip_log(hedef_ip:str) -> dict[str, str]:
    try:
        oturum = AsyncClient(timeout=3)

        istek = await oturum.get(f"http://ip-api.com/json/{hedef_ip}")
        veri  = istek.json()

        if veri["status"] != "fail":
            return {
                "ulke"   : veri["country"] or "",
                "il"     : veri["regionName"] or "",
                "ilce"   : veri["city"] or "",
                "isp"    : veri["isp"] or "",
                "sirket" : veri["org"] or "",
                "host"   : veri["as"] or ""
            }
        else:
            return {"hata": "Veri Bulunamadı.."}
    except Exception as hata:
        return {"hata": f"{type(hata).__name__} » {hata}"}