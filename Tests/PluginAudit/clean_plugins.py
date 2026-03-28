# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import json
import os
import re
from pathlib         import Path
from KekikStream.CLI import konsol

PROJE_KOK  = Path(__file__).parent.resolve()
PLUGIN_DIR = PROJE_KOK / "KekikStream" / "Plugins"
AUDIT_FILE = PROJE_KOK / "audit_results.json"

def clean_plugins():
    if not AUDIT_FILE.exists():
        konsol.print("[bold red][!] audit_results.json bulunamadı![/]")
        return

    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    cleaned_plugins_count    = 0
    total_removed_categories = 0

    for plugin_name, categories in audit_data.items():
        bad_categories = [
            cat_name for cat_name, info in categories.items()
            if info.get("status") in ["Broken/Empty", "Error"]
        ]

        if not bad_categories:
            continue

        plugin_file = PLUGIN_DIR / f"{plugin_name}.py"
        if not plugin_file.exists():
            continue

        with open(plugin_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines            = []
        removed_in_this_file = 0
        in_main_page_block   = False

        for line in lines:
            # main_page başlangıcını bul - Sadece class seviyesindeki main_page'i yakalamak için
            if "main_page" in line and "=" in line and "{" in line:
                in_main_page_block = True
                new_lines.append(line)
                continue

            # main_page sonunu bul - Sadece satırın başında "}" varsa (f-stringlerdeki } ile karışmaması için)
            if in_main_page_block and line.strip().startswith("}"):
                in_main_page_block = False
                new_lines.append(line)
                continue

            if in_main_page_block:
                is_bad = False
                for cat in bad_categories:
                    # Tırnaklı arama (value kısmında kategori ismi yazar)
                    if f'"{cat}"' in line or f"'{cat}'" in line:
                        is_bad = True
                        break

                if is_bad:
                    removed_in_this_file += 1
                    continue

            new_lines.append(line)

        if removed_in_this_file > 0:
            with open(plugin_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            konsol.print(f"[green][*] {plugin_name:<20} [/] -> [bold red]{removed_in_this_file}[/] kategori silindi.")
            cleaned_plugins_count += 1
            total_removed_categories += removed_in_this_file

    konsol.rule("[bold green]Temizlik Tamamlandı")
    konsol.print(f"[bold cyan]{cleaned_plugins_count}[/] eklentiden toplam [bold red]{total_removed_categories}[/] ölü kategori temizlendi.")

if __name__ == "__main__":
    clean_plugins()
