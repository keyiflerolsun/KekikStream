# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .MediaHandler import MediaHandler

class MediaManager:
    def __init__(self):
        self.media_handler = MediaHandler()

    def set_title(self, title):
        self.media_handler.title = title

    def get_title(self):
        return self.media_handler.title

    def set_headers(self, headers):
        self.media_handler.headers.update(headers)

    def play_media(self, extract_data):
        self.media_handler.play_media(extract_data)