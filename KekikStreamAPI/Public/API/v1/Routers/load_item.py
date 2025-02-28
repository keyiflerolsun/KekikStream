# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, JSONResponse, kekik_cache
from ..Libs   import plugin_manager, SeriesInfo
from Settings import CACHE_TIME

from random       import choice
from urllib.parse import quote_plus

@api_v1_router.get("/load_item")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def load_item(request:Request):
    istek = request.state.req_veri
    plugin_names = plugin_manager.get_plugin_names()
    if not istek:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={choice(plugin_names)}&encoded_url="})

    _plugin      = istek.get("plugin")
    _plugin      = _plugin if _plugin in plugin_names else None
    _encoded_url = istek.get("encoded_url")
    if not _plugin or not _encoded_url:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={_plugin or choice(plugin_names)}&encoded_url="})

    plugin = plugin_manager.select_plugin(_plugin)
    result = await plugin.load_item(_encoded_url)

    result.url = quote_plus(result.url)

    if isinstance(result, SeriesInfo):
        for episode in result.episodes:
            episode.url = quote_plus(episode.url)

    return {**api_v1_global_message, "result": result}