#!/usr/bin/env python3
"""Podmienia shadery AxonMap (zrodla/shadery) w gotowych zipach bez pełnej przebudowy paczki."""
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip']
TARGET = 'assets/minecraft/shaders/core/'


def main():
    shaders = {}
    for name in sorted(os.listdir(os.path.join(HERE, 'shadery'))):
        shaders[TARGET + name] = open(os.path.join(HERE, 'shadery', name), 'rb').read()
    for zip_name in ZIPS:
        path = os.path.join(ROOT, zip_name)
        if not os.path.exists(path):
            continue
        tmp = path + '.tmp'
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                if info.filename in shaders:
                    continue
                dst.writestr(info, src.read(info.filename))
            for name, data in shaders.items():
                dst.writestr(name, data)
        shutil.move(tmp, path)
        print('zaktualizowano', zip_name, len(shaders), 'plików shaderów')


if __name__ == '__main__':
    sys.exit(main())
