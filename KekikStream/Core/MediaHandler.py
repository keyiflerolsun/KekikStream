# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..CLI            import konsol
from .ExtractorModels import ExtractResult
import subprocess

class MediaHandler:
    def __init__(self, title: str = "KekikStream", headers: dict = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)"}):
        self.headers = headers
        self.title   = title

    def play_with_vlc(self, extract_data: ExtractResult):
        try:
            if "Cookie" in self.headers:
                self.play_with_mpv(extract_data)
                return

            vlc_command = ["vlc"]

            if self.title:
                vlc_command.append(f"--meta-title={self.title}")
                vlc_command.append(f"--input-title-format={self.title}")

            if "User-Agent" in self.headers:
                vlc_command.append(f"--http-user-agent={self.headers.get('User-Agent')}")

            if "Referer" in self.headers:
                vlc_command.append(f"--http-referrer={self.headers.get('Referer')}")

            vlc_command.append(extract_data.url)
            subprocess.run(vlc_command, check=True)
        except subprocess.CalledProcessError as e:
            konsol.print(f"[red]VLC oynatma hatası: {e}[/red]")
        except FileNotFoundError:
            konsol.print("[red]VLC bulunamadı! VLC kurulu olduğundan emin olun.[/red]")

    def play_with_mpv(self, extract_data: ExtractResult):
        try:
            mpv_command = ["mpv"]

            if self.title:
                mpv_command.append(f"--title={self.title}")

            if "User-Agent" in self.headers:
                mpv_command.append(f"--http-header-fields=User-Agent: {self.headers.get('User-Agent')}")

            if "Referer" in self.headers:
                mpv_command.append(f"--http-header-fields=Referer: {self.headers.get('Referer')}")

            if "Cookie" in self.headers:
                mpv_command.append(f"--http-header-fields=Cookie: {self.headers.get('Cookie')}")

            mpv_command.append(extract_data.url)
            subprocess.run(mpv_command, check=True)
        except subprocess.CalledProcessError as e:
            konsol.print(f"[red]mpv oynatma hatası: {e}[/red]")
        except FileNotFoundError:
            konsol.print("[red]mpv bulunamadı! mpv kurulu olduğundan emin olun.[/red]")