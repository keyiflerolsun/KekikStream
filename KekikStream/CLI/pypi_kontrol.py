# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .             import konsol
from rich.panel    import Panel
from pkg_resources import get_distribution
from requests      import get
from subprocess    import check_call
import sys

def pypi_kontrol_guncelle(paket_adi: str):
    try:
        konsol.print(f"[bold cyan] {paket_adi} Güncellemesi kontrol ediliyor...[/bold cyan]")
        mevcut_surum = get_distribution(paket_adi).version
        konsol.print(Panel(f"[cyan]Yüklü sürüm:[/cyan] [bold yellow]{mevcut_surum}[/bold yellow]"))

        istek = get(f"https://pypi.org/pypi/{paket_adi}/json")
        if istek.status_code == 200:
            son_surum = istek.json()["info"]["version"]
            konsol.print(Panel(f"[cyan]En son sürüm:[/cyan] [bold green]{son_surum}[/bold green]"))

            if mevcut_surum != son_surum:
                konsol.print(f"[bold red]{paket_adi} güncelleniyor...[/bold red]")
                check_call([sys.executable, "-m", "pip", "install", "--upgrade", paket_adi, "--break-system-packages"])
                konsol.print(f"[bold green]{paket_adi} güncellendi![/bold green]")
            else:
                konsol.print(f"[bold green]{paket_adi} zaten güncel.[/bold green]")
        else:
            konsol.print("[bold red]PyPI'ye erişilemiyor. Güncelleme kontrolü atlanıyor.[/bold red]")
    except Exception as hata:
        konsol.print(f"[bold red]Güncelleme kontrolü sırasında hata oluştu: {hata}[/bold red]")