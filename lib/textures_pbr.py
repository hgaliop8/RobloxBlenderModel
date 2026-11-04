"""Textures PBR raccordables (sans couture) pour Nadir-4, générées par programme.
Chaque matière produit 4 cartes 1024² : _Couleur (sRGB), _Normale (OpenGL, Y+), _Rugosite, _Metal.
Les couleurs « teintables » sont gardées claires et neutres : la couleur de la pièce Roblox les teinte.
Usage : python textures_pbr.py DOSSIER [noms,...]"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

N = 1024
rng = np.random.default_rng(7)

# ---------------------------------------------------------------- briques de base (toutes périodiques)
def fbm(n=N, beta=2.0, seed=None, lo=1.0, hi=None):
    """bruit fractal périodique : bruit blanc filtré en 1/f^beta dans l'espace de Fourier"""
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n))
    fx = np.fft.fftfreq(n)[:, None]*n; fy = np.fft.fftfreq(n)[None, :]*n
    f = np.sqrt(fx**2 + fy**2); f[0, 0] = 1
    filt = 1/f**(beta/2)
    filt[f < lo] = 0
    if hi: filt *= np.exp(-(f/hi)**2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w)*filt))
    out -= out.min(); out /= out.max() + 1e-9
    return out

def anis(n=N, sx=1.0, sy=40.0, seed=None):
    """bruit étiré (métal brossé, fibres)"""
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n))
    fx = np.fft.fftfreq(n)[:, None]*n; fy = np.fft.fftfreq(n)[None, :]*n
    filt = np.exp(-(fx/sy)**2 - (fy/sx)**2*0.0) * np.exp(-(fy/(sx*300))**2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w)*filt)); out -= out.min(); out /= out.max() + 1e-9
    return out

def smooth(x, a, b):
    t = np.clip((x - a)/(b - a + 1e-9), 0, 1); return t*t*(3 - 2*t)

def blur(a, s):
    """flou périodique (gaussien via FFT)"""
    n = a.shape[0]; fx = np.fft.fftfreq(n)[:, None]; fy = np.fft.fftfreq(n)[None, :]
    g = np.exp(-2*(math.pi*s)**2*(fx**2 + fy**2))
    return np.real(np.fft.ifft2(np.fft.fft2(a)*g))

def voronoi(n=N, cells=12, seed=None):
    """distance au germe le plus proche et à la frontière (F2-F1), périodique"""
    r = np.random.default_rng(seed); pts = r.random((cells*cells, 2))*n
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d1 = np.full((n, n), 1e9, np.float32); d2 = np.full((n, n), 1e9, np.float32); idx = np.zeros((n, n), np.int32)
    for k, (px, py) in enumerate(pts):
        dx = np.abs(xx - px); dx = np.minimum(dx, n - dx); dy = np.abs(yy - py); dy = np.minimum(dy, n - dy)
        d = np.sqrt(dx*dx + dy*dy)
        m = d < d1; d2 = np.where(m, d1, np.minimum(d2, d)); idx = np.where(m, k, idx); d1 = np.where(m, d, d1)
    return d1/(n/cells), (d2 - d1)/(n/cells), idx

def traits(n=N, count=300, lmin=10, lmax=120, width=(1, 2), seed=None, angle=None, val=1.0, seg=4, wig=0.08):
    """rayures : segments dessinés sur une toile 3x3 puis repliés (périodique)"""
    r = np.random.default_rng(seed); img = Image.new('L', (3*n, 3*n), 0); d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = r.random()*n + n, r.random()*n + n
        a = (angle if angle is not None else r.random()*math.pi) + r.normal(0, 0.15)
        L = r.uniform(lmin, lmax)
        pts = [(x, y)]
        for k in range(seg):
            a += r.normal(0, wig); x += math.cos(a)*L/seg; y += math.sin(a)*L/seg; pts.append((x, y))
        d.line(pts, fill=int(255*val*r.uniform(0.4, 1)), width=int(r.integers(width[0], width[1] + 1)))
    a = np.asarray(img, np.float32)/255
    return sum(a[i*n:(i + 1)*n, j*n:(j + 1)*n] for i in range(3) for j in range(3)).clip(0, 1)

def taches(n=N, count=40, rmin=10, rmax=80, seed=None, soft=12):
    r = np.random.default_rng(seed); img = Image.new('L', (3*n, 3*n), 0); d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = r.random()*n + n, r.random()*n + n; rr = r.uniform(rmin, rmax)
        d.ellipse((x - rr, y - rr*r.uniform(0.5, 1.2), x + rr, y + rr*r.uniform(0.5, 1.2)), fill=int(255*r.uniform(0.3, 1)))
    img = img.filter(ImageFilter.GaussianBlur(soft))
    a = np.asarray(img, np.float32)/255
    return sum(a[i*n:(i + 1)*n, j*n:(j + 1)*n] for i in range(3) for j in range(3)).clip(0, 1)

def taches_irr(count=30, rmin=20, rmax=120, seed=None, soft=20, anneau=False):
    """taches aux bords irréguliers (et auréole plus foncée si anneau)"""
    b = taches(count=count, rmin=rmin, rmax=rmax, seed=seed, soft=soft)
    nz = fbm(beta=1.7, seed=(seed or 0) + 900, lo=5)
    t = smooth(b*(0.55 + 0.9*nz), 0.3, 0.6)
    if anneau:
        edge = smooth(b*(0.55 + 0.9*nz), 0.28, 0.34) - smooth(b*(0.55 + 0.9*nz), 0.36, 0.45)
        return t*0.6 + np.clip(edge, 0, 1)*0.8
    return t

def coulures(n=N, count=60, seed=None):
    """traînées verticales (salissures qui coulent) : bruit étiré verticalement"""
    r = np.random.default_rng(seed); a = np.zeros((n, n), np.float32)
    for _ in range(count):
        x = int(r.random()*n); w = int(r.integers(3, 18)); y0 = int(r.random()*n); L = int(r.integers(60, 500))
        prof = np.linspace(1, 0, L)**1.5*r.uniform(0.3, 1)
        for k in range(-w, w + 1):
            col = (x + k) % n; fall = math.exp(-(k/(w*0.6))**2)
            ys = (y0 + np.arange(L)) % n; a[ys, col] = np.maximum(a[ys, col], prof*fall)
    return blur(a, 2)

def normal_from_height(h, strength=4.0):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1))*0.5*strength*N/512
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0))*0.5*strength*N/512
    nx, ny, nz = -gx, gy, np.ones_like(h)          # OpenGL : Y vers le haut de l'image
    l = np.sqrt(nx*nx + ny*ny + nz*nz)
    return np.stack([nx/l, ny/l, nz/l], -1)*0.5 + 0.5

def lin2srgb(c): return np.where(c <= 0.0031308, 12.92*c, 1.055*np.power(np.clip(c, 0, 1), 1/2.4) - 0.055)
def col(rgb): return np.array(rgb, np.float32)/255

def save(dirp, name, color, height, rough, metal, nstrength=4.0):
    """color en sRGB 0..1 (h, w, 3)"""
    os.makedirs(dirp, exist_ok=True)
    rough = np.broadcast_to(np.asarray(rough, np.float32), (N, N)); metal = np.broadcast_to(np.asarray(metal, np.float32), (N, N))
    Image.fromarray((np.clip(color, 0, 1)*255 + 0.5).astype(np.uint8)).save(f'{dirp}/{name}_Couleur.png')
    Image.fromarray((normal_from_height(height, nstrength)*255 + 0.5).astype(np.uint8)).save(f'{dirp}/{name}_Normale.png')
    Image.fromarray((np.clip(rough, 0, 1)*255 + 0.5).astype(np.uint8)).save(f'{dirp}/{name}_Rugosite.png')
    Image.fromarray((np.clip(metal, 0, 1)*255 + 0.5).astype(np.uint8)).save(f'{dirp}/{name}_Metal.png')

def mix(a, b, t): t = t[..., None] if t.ndim == 2 and a.ndim == 3 else t; return a*(1 - t) + b*t
def fill(c): return np.ones((N, N, 3), np.float32)*col(c)

# ---------------------------------------------------------------- matières
MAT = {}
def matiere(f): MAT[f.__name__] = f; return f

@matiere
def metal_peint(d, s=1):
    """tôle peinte : peau d'orange, éclats qui montrent l'acier, rayures, crasse en bas, coulures (teintable : base claire)"""
    peau = fbm(beta=1.2, seed=s, lo=60)
    chips_n = fbm(beta=2.2, seed=s + 1, lo=3); chips = smooth(chips_n, 0.78, 0.8) * smooth(fbm(beta=1.6, seed=s + 2, lo=8), 0.55, 0.75)
    sc = traits(count=60, lmin=8, lmax=70, seed=s + 3, width=(1, 2), val=0.6)
    grime = smooth(fbm(beta=2.4, seed=s + 4, lo=2), 0.45, 0.9)*0.6 + coulures(seed=s + 5)*0.5
    base = fill((232, 232, 228))*(0.94 + 0.06*peau[..., None])
    steel = fill((120, 122, 124))*(0.8 + 0.4*anis(seed=s + 6)[..., None])
    c = mix(base, steel, np.clip(chips + sc*0.4, 0, 1))
    c = mix(c, fill((60, 52, 44)), np.clip(grime, 0, 1)*0.5)
    c = mix(c, fill((150, 80, 40)), smooth(chips_n, 0.8, 0.9)*0.6)
    h = peau*0.15 - chips*0.6 - sc*0.25
    rough = 0.42 + 0.1*peau + 0.25*grime - 0.12*chips + 0.05*sc
    metal = np.clip(chips + sc*0.6, 0, 1)
    save(d, 'metal_peint', c, h, rough, metal, 3.0)

@matiere
def metal_brut(d, s=11):
    br = anis(seed=s); sc = traits(count=400, lmin=20, lmax=200, seed=s + 1, angle=0.0, width=(1, 1))
    sm = smooth(fbm(beta=2.2, seed=s + 2, lo=2), 0.5, 0.95)
    c = fill((176, 178, 180))*(0.85 + 0.25*br[..., None]); c = mix(c, fill((90, 86, 80)), sm*0.35)
    save(d, 'metal_brut', c, br*0.08 - sc*0.2, 0.32 + 0.12*br + 0.2*sm + 0.1*sc, np.ones((N, N))*0.95, 2.0)

@matiere
def metal_rouille(d, s=21):
    r1 = fbm(beta=2.0, seed=s, lo=2); r2 = fbm(beta=1.4, seed=s + 1, lo=16); pits = smooth(fbm(beta=0.8, seed=s + 2, lo=100), 0.7, 0.9)
    rust = smooth(r1, 0.35, 0.65)
    c = mix(fill((120, 118, 112)), fill((130, 64, 30)), rust); c = mix(c, fill((70, 34, 18)), smooth(r2, 0.55, 0.8)*rust)
    c = mix(c, fill((190, 110, 50)), smooth(r2, 0.75, 0.9)*0.5)
    save(d, 'metal_rouille', c, r2*0.4 - pits*0.4 + rust*0.2, 0.55 + 0.35*rust, (1 - rust)*0.8, 4.0)

@matiere
def tole_striee(d, s=31):
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); rep = 8; per = n/rep
    h = np.zeros((n, n), np.float32)
    for off, ang in ((0, 0.785), (per/2, -0.785)):
        u = ((xx - off) % per - per/2); v = ((yy - (off if off else 0)) % per - per/2)
        mask = ((xx//(per/2) + yy//(per/2)) % 2 == (0 if off == 0 else 1))
        a = (u*math.cos(ang) + v*math.sin(ang)); b = (-u*math.sin(ang) + v*math.cos(ang))
        bump = np.clip(1 - (a/(per*0.38))**2 - (b/(per*0.08))**2, 0, 1)**0.5
        h = np.maximum(h, bump*mask)
    wear = smooth(fbm(beta=2.0, seed=s, lo=2), 0.5, 0.8); sc = traits(count=300, seed=s + 1, lmin=20, lmax=150)
    grime = smooth(fbm(beta=1.8, seed=s + 2, lo=4), 0.4, 0.8)*(1 - h)
    c = fill((150, 152, 154))*(0.85 + 0.15*anis(seed=s + 3)[..., None]); c = mix(c, fill((205, 206, 206)), h*wear*0.6); c = mix(c, fill((40, 36, 32)), grime*0.6)
    save(d, 'tole_striee', c, h*0.6 - sc*0.1, 0.35 + 0.35*grime - 0.15*h*wear + 0.1*sc, np.ones((N, N))*0.9 - grime*0.5, 5.0)

@matiere
def beton(d, s=41):
    b1 = fbm(beta=2.1, seed=s, lo=1); b2 = fbm(beta=1.0, seed=s + 1, lo=80); pores = smooth(fbm(beta=0.6, seed=s + 2, lo=150), 0.8, 0.9)
    st = taches_irr(count=25, rmin=40, rmax=160, seed=s + 3, soft=30); cracks = traits(count=8, lmin=120, lmax=420, seed=s + 4, width=(1, 2), seg=18, wig=0.35)
    c = fill((168, 166, 160))*(0.82 + 0.25*b1[..., None] + 0.08*b2[..., None]); c = mix(c, fill((90, 86, 78)), st*0.45); c = mix(c, fill((50, 48, 44)), np.clip(pores + cracks, 0, 1)*0.7)
    save(d, 'beton', c, b2*0.3 + b1*0.2 - pores*0.6 - cracks*0.5, 0.85 + 0.1*b2 - 0.15*st, np.zeros((N, N)), 3.5)

@matiere
def vinyle(d, s=51):
    sp = (np.random.default_rng(s).random((N, N)) > 0.985).astype(np.float32); sp = blur(sp, 1.0)*4
    scuff = traits(count=160, lmin=30, lmax=200, seed=s + 1, width=(2, 5), val=0.6)
    m = fbm(beta=2.0, seed=s + 2, lo=1); dirt = smooth(fbm(beta=2.4, seed=s + 3, lo=2), 0.55, 0.9)
    c = fill((226, 230, 228))*(0.95 + 0.06*m[..., None]); c = mix(c, fill((120, 124, 126)), np.clip(sp, 0, 1)*0.5)
    c = mix(c, fill((70, 70, 70)), scuff*0.35); c = mix(c, fill((120, 110, 90)), dirt*0.3)
    save(d, 'vinyle', c, m*0.05 - scuff*0.05, 0.5 + 0.08*m + 0.2*scuff + 0.15*dirt, np.zeros((N, N)), 1.5)

@matiere
def carrelage(d, s=61, rep=6):
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); per = n/rep
    gu = np.minimum(xx % per, per - xx % per); gv = np.minimum(yy % per, per - yy % per)
    joint = 1 - smooth(np.minimum(gu, gv), 3, 6)
    tid = (xx//per)*rep + yy//per; tv = np.random.default_rng(s).random(rep*rep)[tid.astype(int) % (rep*rep)]
    m = fbm(beta=1.8, seed=s + 1, lo=2); dirt = smooth(fbm(beta=2.2, seed=s + 2, lo=2), 0.5, 0.85)
    cr = traits(count=10, lmin=40, lmax=160, seed=s + 3, width=(1, 1))
    c = fill((238, 240, 238))*(0.95 + 0.05*tv[..., None] + 0.03*m[..., None]); c = mix(c, fill((110, 104, 92)), joint*(0.6 + 0.4*dirt)); c = mix(c, fill((60, 60, 58)), cr*0.6)
    save(d, 'carrelage', c, -joint*0.6 + 0.02*m - cr*0.3, 0.12 + 0.6*joint + 0.15*dirt, np.zeros((N, N)), 4.0)

@matiere
def moquette(d, s=71):
    lo = fbm(beta=0.4, seed=s, lo=200); mid = fbm(beta=1.6, seed=s + 1, lo=6); st = taches_irr(count=12, rmin=40, rmax=140, seed=s + 2, soft=25)
    c = fill((200, 200, 200))*(0.75 + 0.3*lo[..., None] + 0.1*mid[..., None]); c = mix(c, fill((90, 80, 70)), st*0.15)
    save(d, 'moquette', c, lo*0.6 + mid*0.2, 0.95 - 0.05*lo, np.zeros((N, N)), 5.0)

@matiere
def tissu(d, s=81, fils=96):
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); p = n/fils
    wx = 0.5 + 0.5*np.sin(2*math.pi*xx/p); wy = 0.5 + 0.5*np.sin(2*math.pi*yy/p)
    chk = ((xx//p + yy//p) % 2)
    h = np.where(chk > 0, wx, wy)*0.7 + 0.3*fbm(beta=0.8, seed=s, lo=150)
    pl = fbm(beta=2.6, seed=s + 1, lo=1); fz = fbm(beta=0.5, seed=s + 2, lo=200)
    c = fill((214, 214, 212))*(0.8 + 0.2*h[..., None] + 0.08*pl[..., None]); c = mix(c, fill((150, 150, 150)), fz*0.15)
    save(d, 'tissu', c, h*0.4 + pl*0.8, 0.92 + 0.05*fz, np.zeros((N, N)), 3.5)

@matiere
def matelas(d, s=91, rep=4):
    """toile matelassée : coutures en losanges, boursouflures entre elles"""
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); per = n/rep
    a = (xx + yy) % per; b = (xx - yy) % per
    da = np.minimum(a, per - a); db = np.minimum(b, per - b)
    puff = np.sin(math.pi*a/per)*np.sin(math.pi*b/per)
    seam = 1 - smooth(np.minimum(da, db), 1.5, 4)
    t = fbm(beta=0.6, seed=s, lo=150); st = taches_irr(count=8, rmin=50, rmax=160, seed=s + 1, soft=40, anneau=True)
    c = fill((226, 226, 220))*(0.86 + 0.12*puff[..., None] + 0.05*t[..., None]); c = mix(c, fill((170, 150, 110)), st*0.35); c = mix(c, fill((150, 150, 146)), seam*0.5)
    save(d, 'matelas', c, puff*0.8 - seam*0.6 + t*0.1, 0.9, np.zeros((N, N)), 6.0)

@matiere
def bois(d, s=101, planches=5):
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); per = n/planches
    pid = (yy//per).astype(int); off = np.random.default_rng(s).random(planches + 1)[pid]*n
    warp = fbm(beta=2.2, seed=s + 1, lo=1)*40
    grain = 0.5 + 0.5*np.sin(2*math.pi*((yy + warp)/per*7 + off/n*3) + 6*fbm(beta=1.4, seed=s + 2, lo=4))
    fine = anis(seed=s + 3); joint = 1 - smooth(np.minimum(yy % per, per - yy % per), 1, 3)
    c = mix(fill((182, 136, 90)), fill((120, 80, 48)), grain*0.6 + fine*0.2); c = mix(c, fill((40, 28, 20)), joint*0.8)
    save(d, 'bois', c, grain*0.1 + fine*0.15 - joint*0.6, 0.55 + 0.15*fine + 0.3*joint, np.zeros((N, N)), 3.0)

@matiere
def plastique(d, s=111):
    g = smooth(fbm(beta=0.5, seed=s, lo=200), 0.3, 0.7); m = fbm(beta=2.0, seed=s + 1, lo=1); sc = traits(count=120, seed=s + 2, lmin=10, lmax=60)
    dirt = smooth(fbm(beta=2.2, seed=s + 3, lo=2), 0.55, 0.9)
    c = fill((230, 230, 228))*(0.96 + 0.04*m[..., None]); c = mix(c, fill((150, 150, 146)), sc*0.3); c = mix(c, fill((110, 100, 84)), dirt*0.25)
    save(d, 'plastique', c, g*0.1 - sc*0.1, 0.45 + 0.1*g + 0.15*sc + 0.15*dirt, np.zeros((N, N)), 1.5)

@matiere
def peinture_mur(d, s=121):
    """panneau mural peint, léger relief, salissures en bas et autour des mains"""
    m = fbm(beta=1.0, seed=s, lo=80); lo = fbm(beta=2.4, seed=s + 1, lo=1); hand = taches_irr(count=18, rmin=30, rmax=90, seed=s + 2, soft=20)
    sc = traits(count=14, lmin=20, lmax=120, seed=s + 3, width=(1, 2), val=0.5); cou = coulures(count=20, seed=s + 4)
    c = fill((236, 236, 232))*(0.95 + 0.04*m[..., None] + 0.04*lo[..., None]); c = mix(c, fill((150, 140, 120)), hand*0.1 + cou*0.15); c = mix(c, fill((110, 110, 108)), sc*0.2)
    save(d, 'peinture_mur', c, m*0.08 - sc*0.2, 0.6 + 0.1*m - 0.1*hand + 0.1*sc, np.zeros((N, N)), 1.5)

@matiere
def plafond(d, s=131, rep=4):
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); per = n/rep
    gu = np.minimum(xx % per, per - xx % per); gv = np.minimum(yy % per, per - yy % per); grid = 1 - smooth(np.minimum(gu, gv), 4, 9)
    pts = fbm(beta=0.2, seed=s, lo=300); st = taches_irr(count=10, rmin=50, rmax=160, seed=s + 1, soft=30, anneau=True)
    c = fill((228, 228, 222))*(0.9 + 0.1*pts[..., None]); c = mix(c, fill((150, 146, 136)), grid*0.6); c = mix(c, fill((150, 120, 70)), st*0.18)
    save(d, 'plafond', c, -grid*0.5 + pts*0.2, 0.9 - 0.3*grid, grid*0.6, 4.0)

@matiere
def caoutchouc(d, s=141, rep=24):
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); per = n/rep
    u = (xx % per) - per/2; v = (yy % per) - per/2; dot = np.clip(1 - (u*u + v*v)/(per*0.28)**2, 0, 1)**0.4
    m = fbm(beta=1.6, seed=s, lo=2); dust = smooth(fbm(beta=2.0, seed=s + 1, lo=3), 0.5, 0.85)
    c = fill((60, 62, 64))*(0.9 + 0.15*m[..., None]); c = mix(c, fill((120, 116, 108)), dust*(1 - dot)*0.5)
    save(d, 'caoutchouc', c, dot*0.7, 0.75 - 0.2*dot + 0.1*dust, np.zeros((N, N)), 5.0)

@matiere
def simili_cuir(d, s=151):
    v1, v2, _ = voronoi(cells=60, seed=s); h = smooth(v2, 0.0, 0.25); wr = traits(count=80, lmin=30, lmax=120, seed=s + 1, width=(1, 2), val=0.8)
    c = fill((210, 210, 210))*(0.85 + 0.15*h[..., None]); c = mix(c, fill((120, 120, 120)), wr*0.4)
    save(d, 'simili_cuir', c, h*0.5 - wr*0.4, 0.55 - 0.15*h + 0.2*wr, np.zeros((N, N)), 4.0)

@matiere
def carton(d, s=161):
    f = anis(seed=s); m = fbm(beta=1.8, seed=s + 1, lo=2); st = taches_irr(count=15, rmin=30, rmax=110, seed=s + 2, soft=15, anneau=True)
    c = fill((176, 136, 92))*(0.85 + 0.15*f[..., None] + 0.1*m[..., None]); c = mix(c, fill((120, 86, 50)), st*0.4)
    save(d, 'carton', c, f*0.2 + m*0.2, 0.9, np.zeros((N, N)), 2.0)

@matiere
def grille_vent(d, s=171, rep=16):
    """grille perforée (crasse dans les trous) : opaque, les trous sont rendus sombres"""
    n = N; yy, xx = np.mgrid[0:n, 0:n].astype(np.float32); per = n/rep
    u = (xx % per) - per/2; v = ((yy + (xx//per % 2)*per/2) % per) - per/2; hole = smooth(per*0.32 - np.sqrt(u*u + v*v), -1, 1)
    m = fbm(beta=2.0, seed=s, lo=2); dirt = smooth(m, 0.4, 0.8)
    c = fill((150, 152, 150))*(0.85 + 0.2*m[..., None]); c = mix(c, fill((14, 14, 14)), hole); c = mix(c, fill((60, 54, 44)), dirt*0.4*(1 - hole))
    save(d, 'grille_vent', c, -hole*0.8, 0.45 + 0.3*dirt + 0.4*hole, (1 - hole)*0.85, 5.0)

if __name__ == '__main__':
    out = sys.argv[1]; names = sys.argv[2].split(',') if len(sys.argv) > 2 else list(MAT)
    for n in names:
        MAT[n](out); print('ok', n, flush=True)
