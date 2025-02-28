# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, JSONResponse, kekik_cache
from ..Libs   import extractor_manager
from Settings import CACHE_TIME

@api_v1_router.get("/extract")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def extract(request:Request):
    istek = request.state.req_veri
    if not istek:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?_encoded_url=&_encoded_referer="})

    _encoded_url     = istek.get("encoded_url")
    _encoded_referer = istek.get("encoded_referer")
    if not _encoded_url:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?_encoded_url=&_encoded_referer="})

    extractor = extractor_manager.find_extractor(_encoded_url)
    if not extractor:
        return JSONResponse(status_code=404, content={"hata": "Extractor bulunamadı."})

    result = await extractor.extract(_encoded_url, _encoded_referer)

    return {**api_v1_global_message, "result": result}