# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, JSONResponse, kekik_cache
from ..Libs   import plugin_manager
from Settings import CACHE_TIME

from random       import choice
from urllib.parse import quote_plus

@api_v1_router.get("/load_links")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def load_links(request:Request):
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
    links  = await plugin.load_links(_encoded_url)

    if hasattr(plugin, "play") and callable(getattr(plugin, "play", None)):
        result = []
        for link in links:
            data = plugin._data.get(link, {})
            result.append({
                "name"      : data.get("name"),
                "url"       : link,
                "referer"   : data.get("referer"),
                "subtitles" : data.get("subtitles")
            })

        return {**api_v1_global_message, "must_extract": False, "result": result}

    return {**api_v1_global_message, "must_extract": True, "result": [quote_plus(link) for link in links]}