# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

# * Docker İmajı
FROM python:3.11.8-slim-bookworm

# * Çalışma Alanı
WORKDIR /usr/src/KekikStreamAPI
COPY ./ /usr/src/KekikStreamAPI

# ? Sistem Kurulumları ve Gereksiz Dosyaların Silinmesi
RUN apt-get update -y && \
    apt-get install --no-install-recommends -y \
        # git \
        # ffmpeg \
        # opus-tools \
        locales && \
    sed -i -e 's/# tr_TR.UTF-8 UTF-8/tr_TR.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# * Python Standart Değişkenler
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING="UTF-8"

# * Dil ve Bölge
ENV LANGUAGE="tr_TR.UTF-8" LANG="tr_TR.UTF-8" LC_ALL="tr_TR.UTF-8" TZ="Europe/Istanbul"

# * Gerekli Paketlerin Yüklenmesi
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir -U setuptools wheel && \
    python3 -m pip install --no-cache-dir -Ur requirements.txt

# * Python Çalıştırılması
CMD ["python3", "basla.py"]