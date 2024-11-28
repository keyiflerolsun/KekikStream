# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..CLI      import konsol
from rich.panel import Panel
from rich.table import Table
from InquirerPy import inquirer
import os

class UIManager:
    @staticmethod
    def clear_console():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    async def select_from_list(message, choices):
        return await inquirer.select(message=message, choices=choices).execute_async()

    @staticmethod
    async def prompt_text(message):
        return await inquirer.text(message=message).execute_async()

    @staticmethod
    def display_media_info(plugin_name, media_info):
        table = Table(show_header=False, box=None)
        table.add_column(justify="right", style="cyan", no_wrap=True)
        table.add_column(style="magenta")

        for key, value in media_info.dict().items():
            if value:
                table.add_row(f"[bold cyan]{key.capitalize()}[/bold cyan]", str(value))

        konsol.print(Panel(table, title=f"[bold green]{plugin_name}[/bold green]", expand=False))