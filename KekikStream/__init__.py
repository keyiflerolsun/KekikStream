# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .CLI     import pypi_kontrol_guncelle, cikis_yap, hata_yakala
from .CLI.App import KekikStream
from .Core    import PluginManager, ExtractorManager, UIManager, MediaManager, PluginBase, ExtractorBase, SeriesInfo, ExtractResult
from asyncio  import run

def basla():
    try:
        # PyPI güncellemelerini kontrol et
        pypi_kontrol_guncelle("KekikStream")

        # Uygulamayı başlat
        app = KekikStream()
        run(app.start())
        cikis_yap(False)
    except KeyboardInterrupt:
        cikis_yap(True)
    except Exception as hata:
        hata_yakala(hata)
