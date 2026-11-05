#!/usr/bin/env python3
"""Buduje QualityArmory-21-axon-1.21.11-shadery.zip z domyślnej paczki QualityArmory-21-axon.zip.

Domyślna paczka ma shadery AxonMap w formacie 1.21.4 (zrodla/shadery), których 1.21.11 nie kompiluje.
Ten skrypt kopiuje całą paczkę, usuwa z niej assets/minecraft/shaders/ i wstawia shadery
z zrodla/shadery_1_21_11 (ta sama logika: mapa, kursor, sprity, zegar klienta, chowanie HUD,
tylko nagłówki w formacie 1.21.11: bloki UBO zamiast pojedynczych uniformów i nowa mgła).
pack.mcmeta dostaje min_format = max_format = 75 (tylko 1.21.11).
"""
import json
import os
import sys
import zipfile


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'QualityArmory-21-axon.zip')
OUT = os.path.join(ROOT, 'QualityArmory-21-axon-1.21.11-shadery.zip')
SHADERS = os.path.join(HERE, 'shadery_1_21_11')
TARGET = 'assets/minecraft/shaders/core/'
DESCRIPTION = 'AXON 1.21.11: nowe modele broni na bazie QualityGuns 2.1.9 (shadery w formacie 1.21.11)'


def main():
    with zipfile.ZipFile(SRC) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename.startswith('assets/minecraft/shaders/') or info.filename == 'pack.mcmeta':
                continue
            dst.writestr(info, src.read(info.filename))
        mcmeta = {'pack': {'min_format': 75, 'max_format': 75, 'description': DESCRIPTION}}
        dst.writestr('pack.mcmeta', json.dumps(mcmeta, indent=2, ensure_ascii=False) + '\n')
        for name in sorted(os.listdir(SHADERS)):
            with open(os.path.join(SHADERS, name), 'rb') as f:
                dst.writestr(TARGET + name, f.read())
    print('zapisano', os.path.basename(OUT))
    from atlas_bloku import patch as atlas_bloku
    from dodaj_barrier import patch as dodaj_barrier
    atlas_bloku(OUT)
    dodaj_barrier(OUT)
    sys.path.insert(0, HERE)
    from sprawdz_paczke import main as sprawdz
    return sprawdz([SRC, OUT])


if __name__ == '__main__':
    sys.exit(main())
