# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..CLI            import konsol
from .ExtractorModels import ExtractResult
import subprocess, os

class MediaHandler:
    def __init__(self, title: str = "KekikStream", headers: dict = None):
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)"}

        self.headers = headers
        self.title   = title

    def play_with_vlc(self, extract_data: ExtractResult):
        if subprocess.check_output(['uname', '-o']).strip() == b'Android':
            return self.play_with_android_mxplayer(extract_data)

        try:
            if "Cookie" in self.headers or extract_data.subtitles:
                return self.play_with_mpv(extract_data)

            vlc_command = ["vlc", "--quiet"]

            if self.title:
                vlc_command.extend([
                    f"--meta-title={self.title}",
                    f"--input-title-format={self.title}"
                ])

            if "User-Agent" in self.headers:
                vlc_command.append(f"--http-user-agent={self.headers.get('User-Agent')}")

            if "Referer" in self.headers:
                vlc_command.append(f"--http-referrer={self.headers.get('Referer')}")

            vlc_command.extend(
                f"--sub-file={subtitle.url}" for subtitle in extract_data.subtitles
            )
            vlc_command.append(extract_data.url)

            with open(os.devnull, "w") as devnull:
                subprocess.run(vlc_command, stdout=devnull, stderr=devnull, check=True)

        except subprocess.CalledProcessError as hata:
            konsol.print(f"[red]VLC oynatma hatası: {hata}[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
        except FileNotFoundError:
            konsol.print("[red]VLC bulunamadı! VLC kurulu olduğundan emin olun.[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})

    def play_with_mpv(self, extract_data: ExtractResult):
        try:
            mpv_command = ["mpv", "--really-quiet"]

            if self.title:
                mpv_command.append(f"--force-media-title={self.title}")

            if "User-Agent" in self.headers:
                mpv_command.append(f"--http-header-fields=User-Agent: {self.headers.get('User-Agent')}")

            if "Referer" in self.headers:
                mpv_command.append(f"--http-header-fields=Referer: {self.headers.get('Referer')}")

            if "Cookie" in self.headers:
                mpv_command.append(f"--http-header-fields=Cookie: {self.headers.get('Cookie')}")

            mpv_command.extend(
                f"--sub-file={subtitle.url}" for subtitle in extract_data.subtitles
            )
            mpv_command.append(extract_data.url)

            with open(os.devnull, "w") as devnull:
                subprocess.run(mpv_command, stdout=devnull, stderr=devnull, check=True)

        except subprocess.CalledProcessError as hata:
            konsol.print(f"[red]mpv oynatma hatası: {hata}[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
        except FileNotFoundError:
            konsol.print("[red]mpv bulunamadı! mpv kurulu olduğundan emin olun.[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})

    def play_with_android_mxplayer(self, extract_data: ExtractResult):
        try:
            android_command = [
                "am", "start", "-a", "android.intent.action.VIEW",
                "-d", f"{extract_data.url}",
                "-n", "com.mxtech.videoplayer.ad/com.mxtech.videoplayer.ad.ActivityScreen"
            ]

            with open(os.devnull, "w") as devnull:
                subprocess.run(android_command, stdout=devnull, stderr=devnull, check=True)
        except Exception as hata:
            konsol.print(f"[red]Android MX Player oynatma hatası: {hata}[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})