# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme   import AESManager
import json

class DonilasPlay(ExtractorBase):
    name     = "DonilasPlay"
    main_url = "https://donilasplay.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()
        i_source = istek.text

        m3u_link   = None
        subtitles  = []

        # bePlayer pattern
        hp = HTMLHelper(i_source)
        be_player_matches = hp.regex_all(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);")
        if be_player_matches:
            be_player_pass, be_player_data = be_player_matches[0]

            try:
                # AES decrypt
                decrypted = AESManager.decrypt(be_player_data, be_player_pass)
                data      = json.loads(decrypted)

                m3u_link = data.get("video_location")

                # Altyazıları işle
                str_subtitles = data.get("strSubtitles", [])
                if str_subtitles:
                    for sub in str_subtitles:
                        label = sub.get("label", "")
                        file  = sub.get("file", "")
                        # Forced altyazıları hariç tut
                        if "Forced" in label:
                            continue
                        if file:
                            # Türkçe kontrolü
                            keywords = ["tur", "tr", "türkçe", "turkce"]
                            language = "Turkish" if any(k in label.lower() for k in keywords) else label
                            subtitles.append(Subtitle(
                                name = language,
                                url  = self.fix_url(file)
                            ))
            except Exception:
                pass

        # Fallback: file pattern
        if not m3u_link:
            file_match = hp.regex_first(r'file:"([^"]+)"')
            if file_match:
                m3u_link = file_match

            # tracks pattern for subtitles
            tracks_match = hp.regex_first(r'tracks:\[([^\]]+)')
            if tracks_match:
                try:
                    tracks_str = f"[{tracks_match}]"
                    tracks = json.loads(tracks_str)
                    for track in tracks:
                        file_url = track.get("file")
                        label    = track.get("label", "")
                        if file_url and "Forced" not in label:
                            subtitles.append(Subtitle(
                                name = label,
                                url  = self.fix_url(file_url)
                            ))
                except Exception:
                    pass

        if not m3u_link:
            raise ValueError("m3u link not found")

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = url,
            subtitles = subtitles
        )
