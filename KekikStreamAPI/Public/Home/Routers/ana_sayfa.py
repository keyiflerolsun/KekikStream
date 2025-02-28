# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Core import Request, HTMLResponse
from .    import home_router, home_template

@home_router.get("/", response_class=HTMLResponse)
async def ana_sayfa(request: Request):
    context = {
        "request"  : request,
        "baslik"   : "keyiflerolsun - Ömer Faruk Sancak | KekikAkademi",
        "aciklama" : "siz hayal edin, biz geliştirelim.. 🕊"
    }

    return home_template.TemplateResponse("index.html", context)