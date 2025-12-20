# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme   import AESManager
import re, json

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
        be_player_match = re.search(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);", i_source)
        if be_player_match:
            be_player_pass = be_player_match.group(1)
            be_player_data = be_player_match.group(2)

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
            file_match = re.search(r'file:"([^"]+)"', i_source)
            if file_match:
                m3u_link = file_match.group(1)

            # tracks pattern for subtitles
            tracks_match = re.search(r'tracks:\[([^\]]+)', i_source)
            if tracks_match:
                try:
                    tracks_str = f"[{tracks_match.group(1)}]"
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
