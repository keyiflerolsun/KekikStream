# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Kekik.cli import konsol
from asyncio   import run
from httpx     import AsyncClient

async def main():
    api    = "http://127.0.0.1:3310/api/v1"
    oturum = AsyncClient(timeout=10)

    plugin_names = await oturum.get(f"{api}/get_plugin_names")
    plugin_names = plugin_names.json().get("result")

    for plugin_name in plugin_names:
        plugin = await oturum.get(f"{api}/get_plugin?plugin={plugin_name}")
        plugin = plugin.json().get("result")

        konsol.log(f"[red]main_url    » [purple]{plugin.get('main_url')}")
        konsol.log(f"[red]favicon     » [purple]{plugin.get('favicon')}")
        konsol.log(f"[red]description » [purple]{plugin.get('description')}")

        for url, category in plugin.get("main_page").items():
            konsol.log(f"[red]Kategori    » [purple]{category:<12} » {url}")
            icerikler = await oturum.get(f"{api}/get_main_page?plugin={plugin_name}&page=1&encoded_url={url}&encoded_category={category}")
            icerikler = icerikler.json().get("result")
            if not icerikler:
                continue

            for icerik in icerikler:
                konsol.log(icerik)

                detay = await oturum.get(f"{api}/load_item?plugin={plugin_name}&encoded_url={icerik.get('url')}")
                detay = detay.json().get("result")
                konsol.log(detay)

                if detay.get("episodes"):
                    konsol.log(f"[red]Dizi        » [purple]{detay.get('title')}")
                    bolum     = detay.get("episodes")[0]
                    icerik_url = bolum.get("url")
                else:
                    konsol.log(f"[red]Film        » [purple]{detay.get('title')}")
                    icerik_url = detay.get("url")

                icerikler = await oturum.get(f"{api}/load_links?plugin={plugin_name}&encoded_url={icerik_url}")
                icerikler = icerikler.json()

                for link in icerikler.get("result"):

                    if not icerikler.get("must_extract"):
                        konsol.log(f"[red]icerik_link » [purple]{link.get('url')}")
                        konsol.log(link)
                    else:
                        konsol.log(f"[red]icerik_link » [purple]{link}")
                        sonuc = await oturum.get(f"{api}/extract?encoded_url={link}&encoded_referer={plugin.get('main_url')}")
                        sonuc = sonuc.json().get("result")
                        konsol.log(sonuc)


                    break
                break
            break

if __name__ == "__main__":
    run(main())