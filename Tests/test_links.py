import asyncio
import os
import sys

# Proje dizinini path'e ekle
sys.path.append(os.getcwd())

from KekikStream.Plugins.Watch32 import Watch32
from rich.console import Console

console = Console()

async def main():
    url = "https://watch32.sx/movie/watch-teenage-mutant-ninja-turtles-chrome-alone-2-lost-in-new-jersey-full-140705"
    console.print(f"[bold yellow]Test URL:[/bold yellow] {url}")

    plugin = Watch32()

    try:
        console.print("[bold cyan]Plugin başlatılıyor...[/bold cyan]")

        # Linkleri yükle
        console.print("[bold cyan]Linkler yükleniyor...[/bold cyan]")
        links = await plugin.load_links(url)

        if not links:
            console.print("[bold red]❌ Hiç link bulunamadı![/bold red]")
        else:
            console.print(f"[bold green]✅ {len(links)} link bulundu![/bold green]")
            for link in links:
                console.print(link)

        # # Metadata test
        # console.print("\n[bold cyan]Metadata yükleniyor...[/bold cyan]")
        # item = await plugin.load_item(url)
        # console.print(item)

    except Exception as e:
        console.print(f"[bold red]❌ Hata:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await plugin.close()

if __name__ == "__main__":
    asyncio.run(main())
