# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from CLI      import konsol
from Settings import AYAR, HOST, PORT, WORKERS
from sys      import version_info
import uvicorn

def basla():
    surum = f"{version_info[0]}.{version_info[1]}"
    konsol.print(f"\n[bold gold1]{AYAR['PROJE']}[/] [yellow]:bird:[/] [turquoise2]Python {surum}[/] [bold yellow2]uvicorn[/]", width=70, justify="center")
    konsol.print(f"[red]{HOST}[light_coral]:[/]{PORT}[pale_green1] başlatılmıştır...[/]\n", width=70, justify="center")

    uvicorn.run("Core:KekikStreamAPI", host=HOST, port=PORT, forwarded_allow_ips="*", workers=WORKERS, log_level="error")