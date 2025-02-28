# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, JSONResponse, kekik_cache
from ..Libs   import plugin_manager
from Settings import CACHE_TIME

from random       import choice
from urllib.parse import quote_plus

@api_v1_router.get("/search")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def search(request:Request):
    istek = request.state.req_veri
    plugin_names = plugin_manager.get_plugin_names()
    if not istek:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={choice(plugin_names)}&query="})

    _plugin = istek.get("plugin")
    _plugin = _plugin if _plugin in plugin_names else None
    _query  = istek.get("query")
    if not _plugin or not _query:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={_plugin or choice(plugin_names)}&query="})

    plugin = plugin_manager.select_plugin(_plugin)
    result = await plugin.search(_query)

    for elem in result:
        elem.url = quote_plus(elem.url)

    return {**api_v1_global_message, "result": result}