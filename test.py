# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.CLI             import konsol
from asyncio                     import run
from KekikStream.Plugins.DiziBox import DiziBox
from KekikStream.Core            import ExtractorManager, MediaManager

async def main():
    plugin = DiziBox()
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

            bolum     = detay.episodes[0]
            icerikler = await plugin.load_links(bolum.url)
            for link in icerikler:
                konsol.log(f"[red]icerik_link » [purple]{link}")

                if extractor := ext.find_extractor(link):
                    sonuc = await extractor.extract(link)
                    konsol.log(sonuc)
                    media.set_title(f"{sonuc.name} - {plugin.name} - {detay.title} - {bolum.title or f'{bolum.season}x{bolum.episode}'}")
                    media.play_media(sonuc)

                break
            break
        break

if __name__ == "__main__":
    run(main())