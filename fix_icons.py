#!/usr/bin/env python3
import os
from PIL import Image

ICONS_DIR = "icons"
MAX_SIZE = 180

def fix_icons():
    if not os.path.isdir(ICONS_DIR):
        print(f'No se encuentra el directorio {ICONS_DIR}')
        return

    files = sorted(os.listdir(ICONS_DIR))
    fixed = 0

    for f in files:
        path = os.path.join(ICONS_DIR, f)
        if not os.path.isfile(path):
            continue

        try:
            img = Image.open(path)
            w, h = img.size
            needs_resize = w > MAX_SIZE or h > MAX_SIZE
            needs_convert = img.format != 'WEBP'

            if not needs_resize and not needs_convert:
                continue

            if img.mode not in ('RGBA', 'LA'):
                img = img.convert('RGBA')

            if needs_resize:
                ratio = min(MAX_SIZE / w, MAX_SIZE / h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

            img.save(path, 'WEBP', quality=85)
            fixed += 1
            old_info = f' ({w}x{h}, {img.format})' if needs_convert else f' ({w}x{h})'
            new_info = f' -> {img.size[0]}x{img.size[1]} WEBP'
            print(f'  {f}{old_info}{new_info}')

        except Exception as e:
            print(f'  ERROR {f}: {e}')

    print(f'\nCorregidos: {fixed} iconos')

if __name__ == '__main__':
    fix_icons()
