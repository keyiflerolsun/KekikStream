# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .ExtractorLoader import ExtractorLoader
from .ExtractorBase   import ExtractorBase

class ExtractorManager:
    def __init__(self, extractor_dir="Extractors"):
        # Çıkarıcı yükleyiciyi başlat ve tüm çıkarıcıları yükle
        self.extractor_loader = ExtractorLoader(extractor_dir)
        self.extractors       = self.extractor_loader.load_all()  # Sadece class'lar

        # Lazy loading: Instance'lar ilk kullanımda oluşturulacak
        self._extractor_instances = None  # None = henüz oluşturulmadı
        self._ytdlp_extractor     = None
        self._initialized         = False

    def _ensure_initialized(self):
        """
        Lazy initialization: İlk kullanımda TÜM extractorları initialize et

        Startup'ta sadece class'ları yükledik (hızlı).
        Şimdi instance'ları oluştur ve cache'le (bir kere).
        """
        if self._initialized:
            return

        # Instance listesi oluştur
        self._extractor_instances = []

        # TÜM extractorları instance'la
        for extractor_cls in self.extractors:
            instance = extractor_cls()

            # YTDLP'yi ayrı tut
            if instance.name == "yt-dlp":
                self._ytdlp_extractor = instance
            else:
                self._extractor_instances.append(instance)

        # YTDLP'yi EN BAŞA ekle
        if self._ytdlp_extractor:
            self._extractor_instances.insert(0, self._ytdlp_extractor)

        self._initialized = True

    def find_extractor(self, link) -> ExtractorBase:
        """
        Verilen bağlantıyı işleyebilecek çıkarıcıyı bul
        """
        # Lazy loading: İlk kullanımda extractorları initialize et
        self._ensure_initialized()

        # Cached instance'ları kullan
        for extractor in self._extractor_instances:
            if extractor.can_handle_url(link):
                return extractor

        return None

    def map_links_to_extractors(self, links) -> dict:
        """
        Bağlantıları uygun çıkarıcılarla eşleştir
        """
        # Lazy loading: İlk kullanımda extractorları initialize et
        self._ensure_initialized()

        mapping = {}
        for link in links:
            # Cached instance'ları kullan
            for extractor in self._extractor_instances:
                if extractor.can_handle_url(link):
                    mapping[link] = f"{extractor.name:<30} » {link.replace(extractor.main_url, '')}"
                    break  # İlk eşleşmede dur

        return mapping
