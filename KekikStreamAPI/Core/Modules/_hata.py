# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Core                 import KekikStreamAPI, Request, RedirectResponse, JSONResponse, FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@KekikStreamAPI.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request:Request, exc):
    return RedirectResponse("/") if exc.status_code != 410 else JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@KekikStreamAPI.get("/favicon.ico")
def get_favicon():
    return FileResponse("Public/Home/Static/favicon.ico")