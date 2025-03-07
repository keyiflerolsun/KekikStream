# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from setuptools import setup
from io         import open

setup(
    # ? Genel Bilgiler
    name         = "KekikStream",
    version      = "1.5.2",
    url          = "https://github.com/keyiflerolsun/KekikStream",
    description  = "terminal üzerinden medya içeriği aramanızı ve VLC/MPV gibi popüler medya oynatıcılar aracılığıyla doğrudan izlemenizi sağlayan modüler ve genişletilebilir bir bıdı bıdı",
    keywords     = ["KekikStream", "KekikAkademi", "keyiflerolsun"],

    author       = "keyiflerolsun",
    author_email = "keyiflerolsun@gmail.com",

    license      = "GPLv3+",
    classifiers  = [
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3"
    ],

    # ? Paket Bilgileri
    packages         = ["KekikStream"],
    python_requires  = ">=3.10",
    install_requires = [
        "setuptools",
        "wheel",
        "Kekik",
        "httpx[http2]",
        "cloudscraper",
        "parsel",
        "pydantic",
        "InquirerPy",
        "yt-dlp"
    ],

    # ? Konsoldan Çalıştırılabilir
    entry_points = {
        "console_scripts": [
            "KekikStream = KekikStream:basla"
        ]
    },

    # ? PyPI Bilgileri
    long_description_content_type = "text/markdown",
    long_description              = "".join(open("README.md", encoding="utf-8").readlines()),
    include_package_data          = True
)
