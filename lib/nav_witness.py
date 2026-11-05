"""Réseau de déplacement de The Witness, généré depuis le plan de Nadir-4 (mêmes données que la map).
Trois couches reliées : plafonds (grille dans chaque salle et couloir), gaines (axes des conduits), grilles (passages gaine <-> plafond,
seulement les grilles non soudées). Le sol n'est pas maillé ici : Roblox le gère (PathfindingService).
Sortie : roblox/Witness/NavWitness.lua (ModuleScript) + nav_witness.png (contrôle)."""
import sys, os, math, json
sys.argv = sys.argv[:1] + [a for a in sys.argv[1:] if a.startswith('--')]
import nadir_build as B
import nadir_layout as N

PAS_PLAFOND, MARGE, PAS_GAINE = 8.0, 3.0, 10.0
PLAFOND, GAINE = 1, 2
TYPES_ARETE = {'plafond': 1, 'gaine': 2, 'porte': 3, 'ouverture': 4, 'grille': 5, 'puits': 6}

noeuds = []          # (x, y, z, couche, espace)
aretes = []          # (a, b, type, infos)
par_espace = {}

def ajouter(x, y, z, couche, esp):
    noeuds.append((round(x, 1), round(y, 1), round(z, 1), couche, esp)); return len(noeuds) - 1

def plafond_y(e): return (e.ymax if e.esc else e.elev + e.h) - 0.3

# ---------------------------------------------------------------- plafonds
for e in B.ESP:
    W, D = e.X1 - e.X0, e.Z1 - e.Z0
    nx = max(1, int(round((W - 2*MARGE)/PAS_PLAFOND)) + 1); nz = max(1, int(round((D - 2*MARGE)/PAS_PLAFOND)) + 1)
    xs = [(e.X0 + e.X1)/2] if nx == 1 else [e.X0 + MARGE + i*(W - 2*MARGE)/(nx - 1) for i in range(nx)]
    zs = [(e.Z0 + e.Z1)/2] if nz == 1 else [e.Z0 + MARGE + j*(D - 2*MARGE)/(nz - 1) for j in range(nz)]
    y = plafond_y(e); grid = {}
    for i, x in enumerate(xs):
        for j, z in enumerate(zs): grid[(i, j)] = ajouter(x, y, z, PLAFOND, e.id)
    for (i, j), a in grid.items():
        for di, dj in ((1, 0), (0, 1), (1, 1), (1, -1)):
            b = grid.get((i + di, j + dj))
            if b is not None: aretes.append((a, b, 'plafond', None))
    par_espace[e.id] = list(grid.values())

def espace_en(X, Z, y=None):
    best = None
    for e in B.ESP:
        if e.X0 - 0.01 <= X <= e.X1 + 0.01 and e.Z0 - 0.01 <= Z <= e.Z1 + 0.01:
            if y is None or e.ymin - 2 <= y <= e.ymax + 2:
                if best is None or (e.X1 - e.X0)*(e.Z1 - e.Z0) < (best.X1 - best.X0)*(best.Z1 - best.Z0): best = e
    return best

def plus_proche(ids, X, Z, y=None):
    return min(ids, key=lambda i: (noeuds[i][0] - X)**2 + (noeuds[i][2] - Z)**2 + (0 if y is None else (noeuds[i][1] - y)**2))

# ---------------------------------------------------------------- portes
n_portes = 0
for d in B.DOORS:
    nrm = (0, 1) if d['axis'] == 'X' else (1, 0); cotes = []
    for s in (-1, 1):
        X, Z = d['X'] + nrm[0]*s*2.5, d['Z'] + nrm[1]*s*2.5
        e = espace_en(X, Z)
        if e: cotes.append(e)
    if len(cotes) == 2 and cotes[0] is not cotes[1]:
        a = plus_proche(par_espace[cotes[0].id], d['X'], d['Z']); b = plus_proche(par_espace[cotes[1].id], d['X'], d['Z'])
        sol = min(cotes[0].elev, cotes[1].elev)
        aretes.append((a, b, 'porte', dict(x=round(d['X'], 1), y=round(sol + B.DOOR_H - 0.8, 1), z=round(d['Z'], 1), t=d['t']))); n_portes += 1

# ---------------------------------------------------------------- ouvertures entre couloirs (jonctions sans porte)
n_ouv = 0
for i, a in enumerate(B.COUL):
    for b in B.COUL[i + 1:]:
        if not B.vert_overlap(a, b): continue
        ix0, iz0, ix1, iz1 = max(a.X0, b.X0), max(a.Z0, b.Z0), min(a.X1, b.X1), min(a.Z1, b.Z1)
        if ix1 < ix0 - 0.1 or iz1 < iz0 - 0.1: continue
        cx, cz = (ix0 + ix1)/2, (iz0 + iz1)/2
        na = plus_proche(par_espace[a.id], cx, cz); nb = plus_proche(par_espace[b.id], cx, cz)
        aretes.append((na, nb, 'ouverture', None)); n_ouv += 1

# ---------------------------------------------------------------- gaines
gaines = {}
for g in N.GAINES:
    if g.get('vertical'): continue
    y = g['elev'] + 13 + 2.3; ids = []
    for (ax, az), (bx, bz) in zip(g['pts'][:-1], g['pts'][1:]):
        ax, az, bx, bz = ax*B.S, -az*B.S, bx*B.S, -bz*B.S; L = math.hypot(bx - ax, bz - az); n = max(1, int(L/PAS_GAINE))
        for k in range(n + 1):
            t = k/n; p = ajouter(ax + (bx - ax)*t, y, az + (bz - az)*t, GAINE, g['id'])
            if ids and k > 0: aretes.append((ids[-1], p, 'gaine', None))
            ids.append(p)
    gaines[g['id']] = ids
# jonctions : nœuds de gaines différentes au même niveau, proches, ou un bout qui tombe sur l'axe d'une autre gaine
gl = list(gaines.items())
for i, (ga, ia) in enumerate(gl):
    for gb, ib in gl[i + 1:]:
        best = None
        for p in ia:
            for q in ib:
                if abs(noeuds[p][1] - noeuds[q][1]) > 0.5: continue
                dd = math.hypot(noeuds[p][0] - noeuds[q][0], noeuds[p][2] - noeuds[q][2])
                if dd < 14 and (best is None or dd < best[0]): best = (dd, p, q)
        if best: aretes.append((best[1], best[2], 'gaine', None))
# puits verticaux entre niveaux
for g in N.GAINES:
    if not g.get('vertical'): continue
    (ax, az), (bx, bz) = g['pts'][0], g['pts'][1]
    cands = [i for i, n in enumerate(noeuds) if n[3] == GAINE]
    hauts = sorted(cands, key=lambda i: (noeuds[i][0] - ax*B.S)**2 + (noeuds[i][2] + az*B.S)**2)
    bas = sorted(cands, key=lambda i: (noeuds[i][0] - bx*B.S)**2 + (noeuds[i][2] + bz*B.S)**2)
    h = hauts[0]; b = next((i for i in bas if noeuds[i][1] < noeuds[h][1] - 5), None)
    if b is not None: aretes.append((h, b, 'puits', None))

# ---------------------------------------------------------------- grilles (non soudées) : gaine <-> plafond
grilles = []
for gx, gz, sid, soud in B.GRILLE_W:
    e = B.BYID.get(sid)
    if not e: continue
    grilles.append(dict(x=round(gx, 1), z=round(gz, 1), y=round(e.elev + min(e.h, 12.5), 1), salle=sid, soudee=soud))
    if soud: continue
    g = gaines.get('b_' + sid)
    if not g: continue
    v = plus_proche(g, gx, gz); c = plus_proche(par_espace[sid], gx, gz)
    aretes.append((v, c, 'grille', dict(x=round(gx, 1), y=round(e.elev + min(e.h, 12.5), 1), z=round(gz, 1))))

# ---------------------------------------------------------------- connexité
adj = {i: [] for i in range(len(noeuds))}
for a, b, t, _ in aretes: adj[a].append(b); adj[b].append(a)
vu = set(); comp = []
for s in range(len(noeuds)):
    if s in vu: continue
    pile = [s]; c = []
    while pile:
        u = pile.pop()
        if u in vu: continue
        vu.add(u); c.append(u); pile += adj[u]
    comp.append(c)
comp.sort(key=len, reverse=True)
isoles = sorted({noeuds[c[0]][4] for c in comp[1:]})

# ---------------------------------------------------------------- écriture Luau
def ecrire(chemin):
    L = ['-- Réseau de déplacement de The Witness (généré par lib/nav_witness.py, ne pas modifier à la main)',
         '-- noeuds : x, y, z, couche (1 = plafond, 2 = gaine), index d\'espace ; aretes : a, b, type (1 plafond, 2 gaine, 3 porte, 4 ouverture, 5 grille, 6 puits)',
         'local N = {}']
    esp = sorted({n[4] for n in noeuds}); idx = {s: i + 1 for i, s in enumerate(esp)}
    L.append('N.espaces = {' + ','.join(f'"{s}"' for s in esp) + '}')
    infos = {}
    for e in B.ESP:
        infos[e.id] = (e.X0, e.Z0, e.X1, e.Z1, e.elev, plafond_y(e))
    L.append('N.boites = {' + ','.join('{%g,%g,%g,%g,%g,%g}' % tuple(round(v, 1) for v in infos.get(s, (0, 0, 0, 0, 0, 0))) for s in esp) + '}')
    flat = []
    for x, y, z, c, s in noeuds: flat += [x, y, z, c, idx[s]]
    L.append('N.noeuds = {' + ','.join('%g' % v for v in flat) + '}')
    fa = []; extra = []
    for k, (a, b, t, inf) in enumerate(aretes):
        fa += [a + 1, b + 1, TYPES_ARETE[t]]
        if inf: extra.append('[%d]={x=%g,y=%g,z=%g%s}' % (k + 1, inf['x'], inf['y'], inf['z'], f',t="{inf["t"]}"' if 't' in inf else ''))
    L.append('N.aretes = {' + ','.join(str(v) for v in fa) + '}')
    L.append('N.passages = {' + ','.join(extra) + '}')
    L.append('N.grilles = {' + ','.join('{x=%g,y=%g,z=%g,salle="%s",soudee=%s}' % (g['x'], g['y'], g['z'], g['salle'], 'true' if g['soudee'] else 'false') for g in grilles) + '}')
    L.append('return N')
    open(chemin, 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(racine, 'roblox', 'Witness'), exist_ok=True)
    ecrire(os.path.join(racine, 'roblox', 'Witness', 'NavWitness.lua'))
    print(f'{len(noeuds)} noeuds ({sum(1 for n in noeuds if n[3] == PLAFOND)} plafond, {sum(1 for n in noeuds if n[3] == GAINE)} gaine), {len(aretes)} arêtes, '
          f'{n_portes} portes, {n_ouv} ouvertures, {sum(1 for a in aretes if a[2] == "grille")} grilles praticables ; {len(comp)} morceaux, le plus grand {len(comp[0])}')
    print('espaces isolés :', isoles)
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(14, 12))
        cols = {'plafond': '#9ab', 'gaine': '#c84', 'porte': '#2a6', 'ouverture': '#26a', 'grille': '#d22', 'puits': '#a2a'}
        for a, b, t, _ in aretes:
            ax.plot([noeuds[a][0], noeuds[b][0]], [noeuds[a][2], noeuds[b][2]], color=cols[t], lw=0.4 if t == 'plafond' else 1.2)
        ax.set_aspect('equal'); ax.invert_yaxis(); fig.savefig(os.path.join(racine, 'notes', 'nav_witness.png'), dpi=110, bbox_inches='tight')
    except Exception as ex: print('pas de figure :', ex)
