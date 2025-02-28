# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .        import api_v1_router, api_v1_global_message
from Core     import Request, kekik_cache
from ..Libs   import plugin_manager
from Settings import CACHE_TIME

@api_v1_router.get("/get_plugin_names")
@kekik_cache(ttl=CACHE_TIME, is_fastapi=True)
async def get_plugin_names(request: Request):
    plugin_names = plugin_manager.get_plugin_names()

    return {**api_v1_global_message, "result": plugin_names}