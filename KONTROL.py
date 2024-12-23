# ! Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Kekik.cli    import konsol
from cloudscraper import CloudScraper
import os, re

class MainUrlGuncelleyici:
    def __init__(self, ana_dizin="."):
        self.ana_dizin = ana_dizin
        self.oturum    = CloudScraper()

    @property
    def eklentiler(self):
        """Plugins dizinindeki tüm Python dosyalarını listeler."""
        plugins_dizini = os.path.join(self.ana_dizin, "KekikStream", "Plugins")
        return sorted([
            os.path.join(plugins_dizini, dosya)
                for dosya in os.listdir(plugins_dizini)
                    if dosya.endswith(".py") and not dosya.startswith("__")
        ])

    def _main_url_bul(self, dosya_yolu):
        """Dosyadaki main_url değerini bulur."""
        with open(dosya_yolu, "r", encoding="utf-8") as dosya:
            icerik = dosya.read()
            if main_url := re.search(r'(main_url\s*=\s*)(["\'])(https?://.*?)(\2)', icerik):
                return main_url.groups()

        return None

    def _main_url_guncelle(self, dosya_yolu, eski_satir, yeni_satir):
        """Dosyadaki main_url değerini günceller."""
        with open(dosya_yolu, "r+", encoding="utf-8") as dosya:
            icerik = dosya.readlines()
            dosya.seek(0)
            dosya.writelines(
                [
                    satir.replace(eski_satir, yeni_satir)
                        if eski_satir in satir else satir
                            for satir in icerik
                ]
            )
            dosya.truncate()

    def _setup_surum_guncelle(self):
        """setup.py içindeki sürüm numarasını artırır."""
        setup_dosyasi = os.path.join(self.ana_dizin, "setup.py")
        with open(setup_dosyasi, "r+", encoding="utf-8") as dosya:
            icerik = dosya.read()
            if surum_eslesmesi := re.search(r'(version\s*=\s*)(["\'])(\d+)\.(\d+)\.(\d+)(\2)', icerik):
                ana, ara, yama = map(int, surum_eslesmesi.groups()[2:5])
                eski_surum = f"{ana}.{ara}.{yama}"
                yeni_surum = f"{ana}.{ara}.{yama + 1}"
                icerik     = icerik.replace(eski_surum, yeni_surum)

                dosya.seek(0)
                dosya.write(icerik)
                dosya.truncate()
                konsol.print()
                konsol.log(f"[»] Sürüm güncellendi: {eski_surum} -> {yeni_surum}")

    def guncelle(self):
        """Tüm plugin dosyalarını kontrol eder ve gerekirse main_url günceller."""
        guncelleme_var = False

        for dosya_yolu in self.eklentiler:
            eklenti_adi = dosya_yolu.split("/")[-1].replace(".py", "")
    
            konsol.print()
            konsol.log(f"[~] Kontrol ediliyor : {eklenti_adi}")
            main_url_gruplari = self._main_url_bul(dosya_yolu)

            if not main_url_gruplari:
                konsol.log(f"[!] main_url bulunamadı: {dosya_yolu}")
                continue

            prefix, tirnak, eski_url, son_tirnak = main_url_gruplari

            if eklenti_adi == "RecTV":
                yeni_url = self._rectv_ver()
            else:
                try:
                    istek    = self.oturum.get(eski_url, allow_redirects=True)
                    yeni_url = istek.url.rstrip("/")
                    # konsol.log(f"[+] Kontrol edildi   : {eski_url} -> {yeni_url}")
                except Exception as hata:
                    konsol.log(f"[!] Kontrol edilemedi: {eski_url}")
                    konsol.log(f"[!] {type(hata).__name__}: {hata}")
                    continue

            if eski_url != yeni_url:
                eski_satir = f"{prefix}{tirnak}{eski_url}{son_tirnak}"
                yeni_satir = f"{prefix}{tirnak}{yeni_url}{son_tirnak}"
                self._main_url_guncelle(dosya_yolu, eski_satir, yeni_satir)
                konsol.log(f"{eski_url} -> {yeni_url}")
                guncelleme_var = True

        if guncelleme_var:
            # setup.py sürümünü güncelle
            self._setup_surum_guncelle()

    def _rectv_ver(self):
        istek = self.oturum.post(
            url     = "https://firebaseremoteconfig.googleapis.com/v1/projects/791583031279/namespaces/firebase:fetch",
            headers = {
                "X-Goog-Api-Key"    : "AIzaSyBbhpzG8Ecohu9yArfCO5tF13BQLhjLahc",
                "X-Android-Package" : "com.rectv.shot",
                "User-Agent"        : "Dalvik/2.1.0 (Linux; U; Android 12)",
            },
            json    = {
                "appBuild"      : "81",
                "appInstanceId" : "evON8ZdeSr-0wUYxf0qs68",
                "appId"         : "1:791583031279:android:1",
            }
        )
        return istek.json().get("entries", {}).get("api_url", "").replace("/api/", "")


if __name__ == "__main__":
    guncelleyici = MainUrlGuncelleyici()
    guncelleyici.guncelle()