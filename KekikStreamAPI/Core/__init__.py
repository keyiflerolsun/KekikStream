# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from fastapi             import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses   import JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse, FileResponse
from Kekik.cache         import kekik_cache

KekikStreamAPI = FastAPI(
    title       = "KekikStreamAPI",
    openapi_url = None,
    docs_url    = None,
    redoc_url   = None
)

# ! ----------------------------------------» Routers

from Core.Modules          import _istek, _hata
from Public.Home.Routers   import home_router
from Public.API.v1.Routers import api_v1_router

KekikStreamAPI.include_router(home_router, prefix="")
KekikStreamAPI.mount("/static/home", StaticFiles(directory="Public/Home/Static"), name="static_home")

KekikStreamAPI.include_router(api_v1_router, prefix="/api/v1")