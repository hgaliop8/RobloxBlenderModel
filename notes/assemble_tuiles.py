"""Assemble les bandes rendues séparément (witness_<vue>_t<i>.png + .json) en une image. Usage : python assemble.py DOSSIER... SORTIE.png"""
import sys, json, glob, os
import numpy as np
from PIL import Image

dirs, outp = sys.argv[1:-1], sys.argv[-1]
tiles = []
for d in dirs:
    for j in glob.glob(os.path.join(d, '*_t*.json')):
        info = json.load(open(j)); png = j[:-5] + '.png'
        if os.path.exists(png): tiles.append((info, np.asarray(Image.open(png).convert('RGB')).astype(np.float32)))
tiles.sort(key=lambda t: t[0]['i'])
W, H, n = tiles[0][0]['W'], tiles[0][0]['H'], tiles[0][0]['n']
assert len(tiles) == n, f'{len(tiles)} bandes sur {n}'
acc = np.zeros((H, W, 3), np.float32); wsum = np.zeros((H, 1, 1), np.float32)
for info, im in tiles:
    top = int(round((1 - info['y1'])*H)); h = im.shape[0]
    rows = np.arange(top, top + h, dtype=np.float32) + 0.5
    d0 = rows - top if top > 0 else np.full_like(rows, 1e9); d1 = (top + h) - rows if top + h < H else np.full_like(rows, 1e9)
    w = np.clip(np.minimum(d0, d1)/48, 1e-3, 1)[:, None, None]       # fondu sur la zone de recouvrement
    acc[top:top + h] += im*w; wsum[top:top + h] += w
img = acc/np.maximum(wsum, 1e-6)
Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(outp)
print('ok', outp, W, H)
