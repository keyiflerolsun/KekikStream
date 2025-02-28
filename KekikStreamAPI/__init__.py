# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from pathlib import Path
import os, sys

proje_dizin = Path(__file__).resolve().parent
os.chdir(proje_dizin)
sys.path.append(str(proje_dizin))

from CLI  import cikis_yap, hata_yakala
from Core import Motor

def basla():
    try:
        Motor.basla()
        cikis_yap(False)
    except Exception as hata:
        hata_yakala(hata)