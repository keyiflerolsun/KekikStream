# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

# -- Ana dizine geçip path ekle
import sys, os

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir   = os.path.dirname(script_dir)
os.chdir(root_dir)
sys.path.append(root_dir)
# ---------------------------------------------------------->

from KekikStream.CLI  import konsol
from asyncio          import run
from KekikStream.Core import ExtractorManager, MediaManager, MovieInfo, SeriesInfo

from KekikStream.Plugins.FilmMakinesi import FilmMakinesi

async def main():
    plugin = FilmMakinesi()
    ext    = ExtractorManager()
    media  = MediaManager()

    konsol.log(f"[red]main_url    » [purple]{plugin.main_url}")
    konsol.log(f"[red]favicon     » [purple]{plugin.favicon}")
    konsol.log(f"[red]description » [purple]{plugin.description}")

    for url, category in plugin.main_page.items():
        konsol.log(f"[red]Kategori    » [purple]{category:<12} » {url}")
        icerikler = await plugin.get_main_page(1, url, category)
        if not icerikler:
            continue

        for icerik in icerikler:
            konsol.log(icerik)

            detay = await plugin.load_item(icerik.url)
            konsol.log(detay)

            if isinstance(detay, MovieInfo):
                konsol.log(f"[red]Film        » [purple]{detay.title}")
                icerikler = await plugin.load_links(detay.url)
            elif isinstance(detay, SeriesInfo):
                konsol.log(f"[red]Dizi        » [purple]{detay.title}")
                bolum     = detay.episodes[0]
                icerikler = await plugin.load_links(bolum.url)

            for link in icerikler:
                konsol.log(f"[red]icerik_link » [purple]{link.get('url')}")

                if hasattr(plugin, "play") and callable(getattr(plugin, "play", None)):
                    await plugin.play(
                        name      = link.get("name"),
                        url       = link.get("url"),
                        referer   = link.get("referer"),
                        subtitles = link.get("subtitles")
                    )
                elif extractor := ext.find_extractor(link.get("url")):
                    sonuc = await extractor.extract(link.get("url"), referer=plugin.main_url)
                    konsol.log(sonuc)
                    if isinstance(detay, SeriesInfo):
                        media.set_title(f"{sonuc.name} - {plugin.name} - {detay.title} - {bolum.title or f'{bolum.season}x{bolum.episode}'}")
                    else:
                        media.set_title(f"{sonuc.name} - {plugin.name} - {detay.title}")
                    media.play_media(sonuc)
                else:
                    konsol.print(f"[red]Önerilen araç bulunamadı: {link.get('url')}")

                break
            break
        break

if __name__ == "__main__":
    run(main())