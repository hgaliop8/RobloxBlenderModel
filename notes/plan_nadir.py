"""Dessine le plan à l'échelle de Nadir-4 depuis lib/nadir_layout.py. Usage : python plan_nadir.py SORTIE.png"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from PIL import Image, ImageDraw, ImageFont
import nadir_layout as N

PX = 4.0                                   # pixels par unité de conception
X0, X1, Z0, Z1 = -165, 170, -210, 178
LEG = 470
W, H = int((X1 - X0)*PX) + LEG, int((Z1 - Z0)*PX) + 70
F = '/usr/share/fonts/truetype/dejavu/'
f_t = ImageFont.truetype(F + 'DejaVuSans-Bold.ttf', 30)
f_n = ImageFont.truetype(F + 'DejaVuSans-Bold.ttf', 15)
f_s = ImageFont.truetype(F + 'DejaVuSans.ttf', 13)
f_l = ImageFont.truetype(F + 'DejaVuSans.ttf', 16)
f_lb = ImageFont.truetype(F + 'DejaVuSans-Bold.ttf', 17)

def P(x, z): return ((x - X0)*PX, (Z1 - z)*PX + 60)
def box(r): a = P(r[0], r[3]); b = P(r[2], r[1]); return (a[0], a[1], b[0], b[1])

img = Image.new('RGB', (W, H), (250, 250, 248)); d = ImageDraw.Draw(img, 'RGBA')
d.text((20, 14), 'Nadir-4 — plan à l\'échelle (vue de dessus)', font=f_t, fill=(25, 28, 32))
WALL = (40, 44, 50); COR = (226, 226, 222)
ELEV_C = {0: (0, 0, 0, 0), -16: (120, 70, 0, 26), -28: (90, 40, 0, 50)}

def octo(r):
    x0, z0, x1, z1 = r; c = 0.29*(x1 - x0)
    pts = [(x0 + c, z1), (x1 - c, z1), (x1, z1 - c), (x1, z0 + c), (x1 - c, z0), (x0 + c, z0), (x0, z0 + c), (x0, z1 - c)]
    return [P(*p) for p in pts]

# sols
for c in N.COULOIRS:
    b = box(c['rect']); d.rectangle(b, fill=COR)
    if 'escalier' in c:
        za, zb, ea, eb = c['escalier']; x0, _, x1, _ = c['rect']
        for k in range(int((zb - za)/2.5) + 1):
            z = za + k*2.5; d.line([P(x0, z), P(x1, z)], fill=(150, 150, 150), width=1)
        tx, ty = P(x1 + 1.5, (za + zb)/2); bb = d.textbbox((tx, ty), f'escalier {ea} → {eb}', font=f_s, anchor='lm')
        d.rectangle(bb, fill=(250, 250, 248)); d.text((tx, ty), f'escalier {ea} → {eb}', font=f_s, fill=(90, 90, 90), anchor='lm')
for s in N.SALLES:
    col = N.SECTEURS[s['secteur']]['couleur']
    if s['forme'] == 'octo': d.polygon(octo(s['rect']), fill=col)
    else: d.rectangle(box(s['rect']), fill=col)
    if s.get('sure'):
        x0, y0, x1, y1 = box(s['rect']); m = Image.new('L', img.size, 0); dm = ImageDraw.Draw(m)
        if s['forme'] == 'octo': dm.polygon(octo(s['rect']), fill=255)
        else: dm.rectangle((x0, y0, x1, y1), fill=255)
        hat = Image.new('RGBA', img.size, (0, 0, 0, 0)); dh = ImageDraw.Draw(hat)
        for k in range(int(x0) - int(y1 - y0), int(x1), 14): dh.line([(k, y1), (k + (y1 - y0)*0.6, y0)], fill=(60, 110, 200, 70), width=2)
        img.paste(hat, (0, 0), Image.composite(hat, Image.new('RGBA', img.size, (0, 0, 0, 0)), m).split()[3])
# teinte de profondeur
for o in N.SALLES + N.COULOIRS:
    e = o['elev'];
    if e in ELEV_C and e != 0:
        if o.get('forme') == 'octo': continue
        d.rectangle(box(o['rect']), fill=ELEV_C[e])
# eau
for o in N.SALLES + N.COULOIRS:
    if 'eau' in o: d.rectangle(box(o['rect']), fill=(40, 120, 220, 120))
# murs
for o in N.SALLES + N.COULOIRS:
    if o.get('forme') == 'octo': d.polygon(octo(o['rect']), outline=WALL, width=3)
    else: d.rectangle(box(o['rect']), outline=WALL, width=3 if o in N.SALLES else 2)
# portes
PCOL = {'ouvert': None, 'porte': (90, 90, 90), 'motorisee': (130, 60, 170), 'badge1': (40, 150, 60), 'badge2': (230, 150, 20),
        'badge3': (210, 40, 40), 'volet': (40, 90, 200), 'sas': (0, 150, 160), 'pression': (0, 150, 160), 'etanche': (20, 60, 120), 'navette': (40, 90, 200)}
for x, z, mur, w, t in N.PORTES:
    if mur == 'x': a, b = P(x, z + w/2), P(x, z - w/2); gap = [(a[0] - 3, a[1]), (b[0] + 3, b[1])]
    else: a, b = P(x - w/2, z), P(x + w/2, z); gap = [(a[0], a[1] - 3), (b[0], b[1] + 3)]
    d.rectangle(gap, fill=COR)
    if PCOL[t]:
        if mur == 'x': d.rectangle([(a[0] - 2, a[1]), (b[0] + 2, b[1])], fill=PCOL[t])
        else: d.rectangle([(a[0], a[1] - 2), (b[0], b[1] + 2)], fill=PCOL[t])
# gaines
def dashed(p, q, col, w=3, dash=10, gap=7):
    (x0, y0), (x1, y1) = p, q; L = math.hypot(x1 - x0, y1 - y0); n = int(L/(dash + gap)) + 1
    for k in range(n):
        t0 = k*(dash + gap)/L; t1 = min(1, (k*(dash + gap) + dash)/L)
        if t0 >= 1: break
        d.line([(x0 + (x1 - x0)*t0, y0 + (y1 - y0)*t0), (x0 + (x1 - x0)*t1, y0 + (y1 - y0)*t1)], fill=col, width=w)
for g in N.GAINES:
    col = (30, 110, 220) if g.get('inonde') else (230, 110, 20)
    for p, q in zip(g['pts'][:-1], g['pts'][1:]): dashed(P(*p), P(*q), col)
for x, z, salle, soudee in N.GRILLES:
    cx, cy = P(x, z); d.rectangle([cx - 6, cy - 6, cx + 6, cy + 6], fill=(200, 40, 40) if soudee else (230, 110, 20), outline=WALL)
# points d'intérêt numérotés
for i, (x, z, k, nom) in enumerate(N.POINTS, 1):
    cx, cy = P(x, z); d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(255, 255, 255), outline=(25, 28, 32), width=2)
    d.text((cx, cy), str(i), font=f_s, fill=(25, 28, 32), anchor='mm')
# étiquettes
for s in N.SALLES:
    x0, z0, x1, z1 = s['rect']; cx, cy = P((x0 + x1)/2, (z0 + z1)/2)
    if s['id'] in ('amarrage',): continue
    w, h = N.taille_studs(s)
    nom = s['nom']; txt2 = f"{w:.0f}×{h:.0f} studs · niv. {s['elev']}"
    if s['id'] in ('sas_pression',):
        lx_, ly_ = P(x0 - 2, (z0 + z1)/2); d.text((lx_, ly_ - 9), nom, font=f_n, fill=(20, 22, 26), anchor='rm'); d.text((lx_, ly_ + 9), txt2, font=f_s, fill=(60, 64, 70), anchor='rm'); continue
    if s['id'] == 'radio':
        lx_, ly_ = P(x1 + 2, (z0 + z1)/2); d.text((lx_, ly_ - 9), nom, font=f_n, fill=(20, 22, 26), anchor='lm'); d.text((lx_, ly_ + 9), txt2, font=f_s, fill=(60, 64, 70), anchor='lm'); continue
    ty = P(0, z1)[1] + (34 if s['id'] == 'rotonde' else 16)
    for t_, f_, dy in ((nom, f_n, 0), (txt2, f_s, 18)):
        bb = d.textbbox((cx, ty + dy), t_, font=f_, anchor='mm'); d.rectangle((bb[0] - 3, bb[1] - 1, bb[2] + 3, bb[3] + 1), fill=(255, 255, 255, 170))
        d.text((cx, ty + dy), t_, font=f_, fill=(20, 22, 26) if dy == 0 else (60, 64, 70), anchor='mm')
# échelle et nord
sx, sy = P(-160, -205); L = 40/N.S*PX
d.line([(sx, sy), (sx + L, sy)], fill=WALL, width=4); d.text((sx + L + 8, sy), f'40 studs ≈ {40*N.STUD_M:.0f} m', font=f_s, fill=WALL, anchor='lm')
nx, ny = P(155, 168); d.polygon([(nx, ny - 20), (nx - 9, ny + 6), (nx + 9, ny + 6)], fill=WALL); d.text((nx, ny + 18), 'N', font=f_n, fill=WALL, anchor='mm')
# légende
lx = W - LEG + 20; y = 80
d.text((lx, y), 'Légende', font=f_t, fill=(25, 28, 32)); y += 46
for k, v in N.SECTEURS.items():
    d.rectangle([lx, y, lx + 26, y + 18], fill=v['couleur'], outline=WALL); d.text((lx + 36, y + 9), v['nom'], font=f_l, fill=(30, 30, 30), anchor='lm'); y += 26
d.rectangle([lx, y, lx + 26, y + 18], fill=COR, outline=WALL); d.text((lx + 36, y + 9), 'Couloir', font=f_l, fill=(30, 30, 30), anchor='lm'); y += 26
d.rectangle([lx, y, lx + 26, y + 18], fill=(255, 255, 255), outline=WALL)
for k in range(0, 26, 7): d.line([(lx + k, y), (lx + k + 6, y + 18)], fill=(60, 110, 200), width=2)
d.text((lx + 36, y + 9), 'Salle sûre', font=f_l, fill=(30, 30, 30), anchor='lm'); y += 26
d.rectangle([lx, y, lx + 26, y + 18], fill=(150, 190, 235), outline=WALL); d.text((lx + 36, y + 9), 'Eau', font=f_l, fill=(30, 30, 30), anchor='lm'); y += 26
d.rectangle([lx, y, lx + 26, y + 18], fill=(225, 205, 185), outline=WALL); d.text((lx + 36, y + 9), 'Plus foncé = plus profond', font=f_l, fill=(30, 30, 30), anchor='lm'); y += 34
for col, lab in (((230, 110, 20), 'Gaine (accroupi)'), ((30, 110, 220), 'Gaine inondée')):
    dashed((lx, y + 9), (lx + 26, y + 9), col); d.text((lx + 36, y + 9), lab, font=f_l, fill=(30, 30, 30), anchor='lm'); y += 26
for col, lab in (((230, 110, 20), 'Grille ouverte'), ((200, 40, 40), 'Grille soudée (chalumeau)')):
    d.rectangle([lx + 7, y + 3, lx + 19, y + 15], fill=col, outline=WALL); d.text((lx + 36, y + 9), lab, font=f_l, fill=(30, 30, 30), anchor='lm'); y += 26
y += 8; d.text((lx, y), 'Portes', font=f_lb, fill=(25, 28, 32)); y += 26
for t, col in PCOL.items():
    if not col or t == 'navette' or t == 'pression': continue
    d.rectangle([lx, y + 6, lx + 26, y + 12], fill=col); d.text((lx + 36, y + 9), N.TYPES_PORTE[t], font=f_l, fill=(30, 30, 30), anchor='lm'); y += 24
y += 8; d.text((lx, y), "Points d'intérêt", font=f_lb, fill=(25, 28, 32)); y += 26
for i, (x, z, k, nom) in enumerate(N.POINTS, 1):
    d.text((lx, y), f'{i:>2}  {nom}', font=f_s, fill=(30, 30, 30)); y += 19
img.save(sys.argv[1]); print('ok', img.size)
