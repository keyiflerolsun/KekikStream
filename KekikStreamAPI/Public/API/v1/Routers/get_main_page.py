# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, JSONResponse, kekik_cache
from ..Libs   import plugin_manager
from Settings import CACHE_TIME

from random       import choice
from urllib.parse import quote_plus

@api_v1_router.get("/get_main_page")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def get_main_page(request:Request):
    istek = request.state.req_veri
    plugin_names = plugin_manager.get_plugin_names()
    if not istek:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={choice(plugin_names)}&page=1&encoded_url=&encoded_category="})

    _plugin           = istek.get("plugin")
    _plugin           = _plugin if _plugin in plugin_names else None
    _page             = istek.get("page")
    _page             = int(_page) if _page.isdigit() else None
    _encoded_url      = istek.get("encoded_url")
    _encoded_category = istek.get("encoded_category")
    if not _plugin or not _page or not _encoded_url or not _encoded_category:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={_plugin or choice(plugin_names)}&page=1&encoded_url=&encoded_category="})

    plugin = plugin_manager.select_plugin(_plugin)
    result = await plugin.get_main_page(_page, _encoded_url, _encoded_category)
    for icerik in result:
        icerik.url = quote_plus(icerik.url)

    return {**api_v1_global_message, "result": result}