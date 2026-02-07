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
from KekikStream.Core import PluginManager, ExtractorManager, MediaManager, MovieInfo, SeriesInfo

async def main():
    ext     = ExtractorManager()
    plugins = PluginManager(ex_manager=ext)
    media   = MediaManager()

    for eklenti_adi in plugins.get_plugin_names():
        konsol.log(f"[red]Eklenti     » [purple]{eklenti_adi}")
        plugin = plugins.select_plugin(eklenti_adi)

        if not plugin.main_page:
            continue

        konsol.log(f"[red]main_url    » [purple]{plugin.main_url}")
        konsol.log(f"[red]favicon     » [purple]{plugin.favicon}")
        konsol.log(f"[red]description » [purple]{plugin.description}")

        for url, category in plugin.main_page.items():
            konsol.log(f"[red]Kategori    » [purple]{category:<12} » {url}")
            icerikler = await plugin.get_main_page(1, url, category)

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

                    await plugin.play(
                        name      = link.get("name"),
                        url       = link.get("url"),
                        referer   = link.get("referer"),
                        subtitles = link.get("subtitles")
                    )

                    break
                break
            break

if __name__ == "__main__":
    run(main())
