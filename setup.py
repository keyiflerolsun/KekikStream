# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from setuptools import setup
from io         import open

setup(
    # ? Genel Bilgiler
    name         = "KekikStream",
    version      = "0.0.1",
    url          = "https://github.com/keyiflerolsun/KekikStream",
    description  = "KekikStream bir medya içerik yöneticisi ve oynatıcıdır. Kullanıcıların farklı platformlardaki içerikleri aramasını, detaylarını görüntülemesini ve izleme bağlantılarına erişmesini sağlar. Proje, modüler bir yapıya sahiptir ve kolayca yeni eklenti (plugin) ve çıkarıcı (extractor) eklenebilir.",
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
    python_requires  = ">=3.12",
    install_requires = [
        "setuptools",
        "wheel",
        "Kekik",
        "httpx",
        "parsel",
        "pydantic",
        "InquirerPy",
    ],

    # ? Konsoldan Çalıştırılabilir
    entry_points = {
        "console_scripts": [
            "KekikStream = KekikStream:basla",
        ]
    },

    # ? PyPI Bilgileri
    long_description_content_type = "text/markdown",
    long_description              = "".join(open("README.md", encoding="utf-8").readlines()),
    include_package_data          = True
)