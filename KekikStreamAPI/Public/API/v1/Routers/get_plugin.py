# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, JSONResponse, kekik_cache
from ..Libs   import plugin_manager
from Settings import CACHE_TIME

from random       import choice
from urllib.parse import quote_plus

@api_v1_router.get("/get_plugin")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def get_plugin(request:Request):
    istek = request.state.req_veri
    plugin_names = plugin_manager.get_plugin_names()
    if not istek:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={choice(plugin_names)}"})

    _plugin = istek.get("plugin")
    _plugin = _plugin if _plugin in plugin_names else None
    if not _plugin:
        return JSONResponse(status_code=410, content={"hata": f"{request.url.path}?plugin={_plugin or choice(plugin_names)}"})

    plugin = plugin_manager.select_plugin(_plugin)

    main_page = {}
    for url, category in plugin.main_page.items():
        main_page[quote_plus(url)] = quote_plus(category)

    result = {
        "name"        : plugin.name,
        "language"    : plugin.language,
        "main_url"    : plugin.main_url,
        "favicon"     : plugin.favicon,
        "description" : plugin.description,
        "main_page"   : main_page
    }

    return {**api_v1_global_message, "result": result}