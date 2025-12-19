# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI                      import konsol
from ..Extractor.ExtractorModels import ExtractResult
import subprocess, os, yt_dlp

class MediaHandler:
    def __init__(self, title: str = "KekikStream"):
        self.title   = title
        self.headers = {}

        self._ytdlp_extractors = yt_dlp.extractor.list_extractors()

    def should_use_ytdlp(self, url: str, user_agent: str) -> bool:
        """
        yt-dlp gereken durumları akıllıca tespit et

        yt-dlp'nin kendi 1863+ extractor'ını kullanarak otomatik tespit yapar.
        YouTube, Vimeo, Twitch, TikTok, Instagram vb. binlerce site için çalışır.

        Args:
            url: Video URL'si
            user_agent: User-Agent string'i

        Returns:
            bool: yt-dlp kullanılması gerekiyorsa True
        """
        # 1. User-Agent bazlı kontrol (mevcut davranışı koru - RecTV, MolyStream için)
        ytdlp_user_agents = [
            "googleusercontent",
            "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0"
        ]

        if user_agent in ytdlp_user_agents:
            konsol.log("[cyan][ℹ] User-Agent bazlı yt-dlp tespiti[/cyan]")
            return True

        # 2. yt-dlp'nin kendi extractor tespitini kullan
        try:
            # Tüm extractorları kontrol et (Generic hariç)
            for ie in self._ytdlp_extractors:
                # Generic extractor'ı atla (her URL'ye uygundur ama özel değildir)
                if ie.ie_key() == 'Generic':
                    continue

                # Bu extractor bu URL'yi işleyebilir mi?
                if ie.suitable(url):
                    konsol.log(f"[cyan][ℹ] yt-dlp extractor bulundu: {ie.ie_key()}[/cyan]")
                    return True

            # Özel extractor bulunamadı
            return False

        except Exception as e:
            konsol.log(f"[yellow][⚠] yt-dlp kontrol hatası: {e}[/yellow]")
            return False

    def play_media(self, extract_data: ExtractResult):
        # user-agent ekle (varsayılan veya extract_data'dan)
        user_agent = extract_data.user_agent or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)"
        self.headers["user-agent"] = user_agent

        # referer ekle
        if extract_data.referer:
            self.headers["referer"] = extract_data.referer

        # İşletim sistemine göre oynatıcı seç (Android durumu)
        if subprocess.check_output(['uname', '-o']).strip() == b'Android':
            return self.play_with_android_mxplayer(extract_data)

        # Akıllı yt-dlp tespiti
        if self.should_use_ytdlp(extract_data.url, user_agent):
            konsol.log("[green][✓] yt-dlp kullanılacak[/green]")
            success = self.play_with_ytdlp(extract_data)
            if success:
                return True
            konsol.log("[yellow][⚠] yt-dlp başarısız, standart oynatıcılar deneniyor...[/yellow]")

        # Oynatıcı öncelik sırası (fallback zincirleme)
        players = [
            ("MPV", self.play_with_mpv),
            ("VLC", self.play_with_vlc),
            ("yt-dlp", self.play_with_ytdlp)
        ]

        # Fallback zincirleme
        for player_name, player_func in players:
            try:
                result = player_func(extract_data)
                if result or result is None:  # None = MPV (exception yok)
                    konsol.log(f"[green][✓] {player_name} ile başarılı[/green]")
                    return True
            except Exception as e:
                konsol.log(f"[yellow][⚠] {player_name} hatası: {e}[/yellow]")
                continue

        konsol.print("[red][✗] Hiçbir oynatıcı çalışmadı![/red]")
        return False

    def play_with_vlc(self, extract_data: ExtractResult):
        konsol.log(f"[yellow][»] VLC ile Oynatılıyor : {extract_data.url}")
        # konsol.print(self.headers)
        try:
            vlc_command = ["vlc", "--quiet"]

            if self.title:
                vlc_command.extend([
                    f"--meta-title={self.title}",
                    f"--input-title-format={self.title}"
                ])

            if "user-agent" in self.headers:
                vlc_command.append(f"--http-user-agent={self.headers.get('user-agent')}")

            if "referer" in self.headers:
                vlc_command.append(f"--http-referrer={self.headers.get('referer')}")

            vlc_command.extend(
                f"--sub-file={subtitle.url}" for subtitle in extract_data.subtitles
            )
            vlc_command.append(extract_data.url)

            with open(os.devnull, "w") as devnull:
                subprocess.run(vlc_command, stdout=devnull, stderr=devnull, check=True)

            return True
        except subprocess.CalledProcessError as hata:
            konsol.print(f"[red]VLC oynatma hatası: {hata}[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
            return False
        except FileNotFoundError:
            konsol.print("[red]VLC bulunamadı! VLC kurulu olduğundan emin olun.[/red]")
            # konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
            return False

    def play_with_mpv(self, extract_data: ExtractResult):
        konsol.log(f"[yellow][»] MPV ile Oynatılıyor : {extract_data.url}")
        # konsol.print(self.headers)
        try:
            mpv_command = ["mpv"]

            if self.title:
                mpv_command.append(f"--force-media-title={self.title}")

            for key, value in self.headers.items():
                mpv_command.append(f"--http-header-fields={key}: {value}")

            mpv_command.extend(
                f"--sub-file={subtitle.url}" for subtitle in extract_data.subtitles
            )
            mpv_command.append(extract_data.url)

            with open(os.devnull, "w") as devnull:
                subprocess.run(mpv_command, stdout=devnull, stderr=devnull, check=True)

            return True
        except subprocess.CalledProcessError as hata:
            konsol.print(f"[red]mpv oynatma hatası: {hata}[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
            return False
        except FileNotFoundError:
            konsol.print("[red]mpv bulunamadı! mpv kurulu olduğundan emin olun.[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
            return False

    def play_with_ytdlp(self, extract_data: ExtractResult):
        konsol.log(f"[yellow][»] yt-dlp ile Oynatılıyor : {extract_data.url}")
        # konsol.print(self.headers)
        try:
            ytdlp_command = ["yt-dlp", "--quiet", "--no-warnings"]

            for key, value in self.headers.items():
                ytdlp_command.extend(["--add-header", f"{key}: {value}"])

            ytdlp_command.extend([
                "-o", "-",
                extract_data.url
            ])

            mpv_command = ["mpv", "--really-quiet", "-"]

            if self.title:
                mpv_command.append(f"--force-media-title={self.title}")

            mpv_command.extend(
                f"--sub-file={subtitle.url}" for subtitle in extract_data.subtitles
            )

            with subprocess.Popen(ytdlp_command, stdout=subprocess.PIPE) as ytdlp_proc:
                subprocess.run(mpv_command, stdin=ytdlp_proc.stdout, check=True)

            return True
        except subprocess.CalledProcessError as hata:
            konsol.print(f"[red]Oynatma hatası: {hata}[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
            return False
        except FileNotFoundError:
            konsol.print("[red]yt-dlp veya mpv bulunamadı! Kurulumlarından emin olun.[/red]")
            konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
            return False

    def play_with_android_mxplayer(self, extract_data: ExtractResult):
        konsol.log(f"[yellow][»] MxPlayer ile Oynatılıyor : {extract_data.url}")
        # konsol.print(self.headers)
        paketler = [
            "com.mxtech.videoplayer.ad/.ActivityScreen",  # Free sürüm
            "com.mxtech.videoplayer.pro/.ActivityScreen"  # Pro sürüm
        ]

        for paket in paketler:
            try:
                android_command = [
                    "am", "start",
                    "-a", "android.intent.action.VIEW",
                    "-d", extract_data.url,
                    "-n", paket
                ]

                if self.title:
                    android_command.extend(["--es", "title", self.title])

                with open(os.devnull, "w") as devnull:
                    subprocess.run(android_command, stdout=devnull, stderr=devnull, check=True)

                return True
            except subprocess.CalledProcessError as hata:
                konsol.print(f"[red]{paket} oynatma hatası: {hata}[/red]")
                konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
                return False
            except FileNotFoundError:
                konsol.print(f"Paket: {paket}, Hata: MX Player kurulu değil")
                konsol.print({"title": self.title, "url": extract_data.url, "headers": self.headers})
                return False
