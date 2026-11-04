"""NADIR-4 — disposition de la base (source unique pour le plan, la maquette Roblox et le kit Blender).
Unités de conception (du) ; S convertit en studs Roblox (1 stud ≈ 0,28 m). Plan : x vers l'est, z vers le nord.
Altitudes (elev) et hauteurs sous plafond (h) en studs. Niveaux : 0 (arrivée, hub, Recherche, Vie), -16 (Machines), -28 (fonds).

Les salles sont posées le long des couloirs avec aile() : on donne la liste des salles de chaque côté, dans l'ordre,
avec leur longueur le long du couloir et leur profondeur ; les portes sont créées au milieu du mur côté couloir."""

S = 1.2                     # du -> studs
STUD_M = 0.28               # mètres par stud

SECTEURS = {
    'arrivee':   dict(nom='Arrivée', couleur=(210, 214, 220)),
    'hub':       dict(nom='Hub', couleur=(200, 200, 200)),
    'recherche': dict(nom='Recherche', couleur=(186, 222, 190)),
    'vie':       dict(nom='Vie', couleur=(186, 206, 236)),
    'machines':  dict(nom='Machines', couleur=(240, 206, 168)),
    'fonds':     dict(nom='Fonds', couleur=(214, 180, 150)),
}
TYPES_PORTE = {
    'ouvert': 'passage ouvert', 'porte': 'porte manuelle', 'motorisee': 'porte motorisée (courant)',
    'badge1': 'badge niveau 1', 'badge2': 'badge niveau 2', 'badge3': 'badge niveau 3',
    'volet': 'volet blindé (salle sûre)', 'sas': 'sas (cycle 10 s)', 'pression': 'sas de pression (levier)',
    'etanche': 'porte étanche', 'navette': 'porte de la navette',
}

SALLES, COULOIRS, PORTES = [], [], []

def salle(id, nom, secteur, x0, z0, x1, z1, elev=0, h=12, **kw):
    d = dict(id=id, nom=nom, secteur=secteur, rect=(x0, z0, x1, z1), elev=elev, h=h, forme=kw.pop('forme', 'rect'))
    d.update(kw); SALLES.append(d); return d

def couloir(id, x0, z0, x1, z1, elev=0, h=12, **kw):
    d = dict(id=id, rect=(x0, z0, x1, z1), elev=elev, h=h); d.update(kw); COULOIRS.append(d); return d

def porte(x, z, mur, w=6, t='porte'): PORTES.append((x, z, mur, w, t))

def aile(c, secteur, cote_plus=(), cote_moins=(), elev=None):
    """pose des salles le long du couloir c (axe = sa plus grande dimension).
    Chaque entrée : nombre (vide, en du) ou (id, nom, longueur, profondeur, {options}). cote_plus = côté +z (couloir est-ouest)
    ou +x (couloir nord-sud)."""
    x0, z0, x1, z1 = c['rect']; e = c['elev'] if elev is None else elev
    long_x = (x1 - x0) >= (z1 - z0)
    for cote, liste in ((1, cote_plus), (-1, cote_moins)):
        cur = x0 if long_x else z0
        for it in liste:
            if not isinstance(it, tuple): cur += it; continue
            id, nom, L, P = it[:4]; kw = dict(it[4]) if len(it) > 4 else {}
            t = kw.pop('porte', 'porte'); pw = kw.pop('largeur_porte', 10 if L >= 50 else 6); h = kw.pop('h', 16 if L*P >= 2000 else 12)
            if long_x:
                r = (cur, z1, cur + L, z1 + P) if cote > 0 else (cur, z0 - P, cur + L, z0)
                porte(cur + L/2, z1 if cote > 0 else z0, 'z', pw, t)
            else:
                r = (x1, cur, x1 + P, cur + L) if cote > 0 else (x0 - P, cur, x0, cur + L)
                porte(x1 if cote > 0 else x0, cur + L/2, 'x', pw, t)
            salle(id, nom, secteur, *r, elev=e, h=h, couloir=c['id'], **kw)
            cur += L

# ================================================================ ARRIVÉE (nord)
salle('navette', 'Navette Meridian', 'arrivee', -14, 250, 14, 320, h=12, sure=True, sans_grille=True, note='portail, réservoir de confinement, coffre à preuves')
salle('amarrage', "Tube d'amarrage", 'arrivee', -5, 238, 5, 250, h=10, sans_grille=True)
salle('sas', "Sas d'arrivée", 'arrivee', -14, 210, 14, 238, h=12, note='cycle de 10 s, balise de détresse')
porte(0, 250, 'z', 6, 'navette'); porte(0, 238, 'z', 6, 'porte'); porte(0, 210, 'z', 8, 'sas')
c = couloir('c_arrivee', -6, 40, 6, 210)
aile(c, 'arrivee',
     cote_plus=[4, ('toilettes_n', 'Toilettes', 16, 18), 4, ('consigne', 'Consigne du matériel', 30, 26), 4,
                ('briefing', 'Salle de briefing', 40, 32), 6, ('decontamination', 'Décontamination', 30, 26), 4, ('vestiaire_arr', "Vestiaires d'arrivée", 32, 26)],
     cote_moins=[8, ('local_tech_n', 'Local technique', 18, 16), 8, ('reserve_n', 'Réserve', 28, 24), 8,
                 ('attente', "Salle d'attente", 36, 30), 8, ('poste_garde', 'Poste de garde', 26, 22), 8, ('placard_a1', 'Placard', 12, 10)])

# ================================================================ HUB
salle('rotonde', 'Rotonde de commande', 'hub', -40, -40, 40, 40, h=22, forme='octo', sure=True, sans_grille=True, note='console du courant, plan, interphone')
for x, z, m in ((0, 40, 'z'), (-40, 0, 'x'), (40, 0, 'x'), (0, -40, 'z')): porte(x, z, m, 10, 'volet')

# ================================================================ RECHERCHE (ouest)
c = couloir('c_rech', -400, -6, -40, 6)
aile(c, 'recherche',
     cote_plus=[4, ('labo_b', 'Labo B — biochimie', 44, 36), 6, ('chambre_froide', 'Chambre froide', 26, 22), 6, ('placard_r1', 'Placard', 12, 10), 18,
                6, ('labo_c', 'Labo C et bassin', 60, 56, dict(note='bassin brisé au centre', h=18)), 8, ('specimens', 'Salle des spécimens', 46, 40), 20,
                12, ('serveurs', 'Serveurs de recherche', 34, 30), 6, ('bureau_cherch', 'Bureau des chercheurs', 36, 28), 4, ('placard_r2', 'Placard', 12, 10)],
     cote_moins=[4, ('aquariums', 'Aquariums de quarantaine', 56, 44), 6, ('reserve_r', 'Réserve de matériel', 30, 24), 20,
                 ('labo_a', 'Labo A — génétique', 50, 40), 6, ('dissection', 'Salle de dissection', 36, 32), 6, ('stock_chimie', 'Produits chimiques', 22, 18, dict(porte='badge1')), 8,
                 12, 6, ('archives', 'Archives C-17', 36, 30, dict(porte='badge3')), 8, ('imprimerie', 'Imprimerie et dossiers', 24, 20), 8, ('toilettes_r', 'Toilettes', 16, 16)])
salle('quarantaine', 'Labo de quarantaine', 'recherche', -444, -24, -400, 24, h=14, note='porte à badge 3, double vitrage'); porte(-400, 0, 'x', 8, 'badge3')
c = couloir('c_rech_n1', -156, 6, -144, 200)
aile(c, 'recherche',
     cote_plus=[64, ('hangar', 'Hangar du drone', 60, 56, dict(h=18)), 6, ('atelier_drone', 'Atelier du drone', 30, 26)],
     cote_moins=[62, ('biblio_sci', 'Bibliothèque scientifique', 40, 34), 8, ('labo_e', 'Labo E — microscopie', 36, 30), 8, ('placard_r3', 'Placard', 12, 10)])
salle('observatoire', "Salle d'observation", 'recherche', -180, 200, -120, 240, h=16, note="grande baie vitrée sur l'abîme"); porte(-150, 200, 'z', 10, 'porte')
c = couloir('c_rech_n2', -296, 6, -284, 170)
aile(c, 'recherche',
     cote_plus=[64, ('labo_f', 'Labo F — haute pression', 40, 34), 8, ('reserve_r2', 'Réserve', 26, 20)],
     cote_moins=[64, ('stock_echant', "Stock d'échantillons", 36, 30), 6, ('placard_r4', 'Placard', 12, 10), 6, ('salle_cuves', 'Salle des cuves', 40, 36)])
couloir('tunnel_verre', -294, 170, -286, 260, h=10, verre=True)
salle('module_prel', 'Module de prélèvement', 'recherche', -320, 260, -260, 316, h=14, note='isolé au bout du tunnel de verre'); porte(-290, 260, 'z', 8, 'etanche')
salle('cloche', 'Cloche de plongée', 'recherche', -260, 276, -234, 302, h=12, sans_grille=True); porte(-260, 289, 'x', 6, 'etanche')
couloir('desc_rech', -156, -124, -144, -6, escalier=(-112, -76, -16, 0))
couloir('desc_pression', -296, -124, -284, -6, escalier=(-114, -86, -16, 0))
porte(-290, -62, 'z', 12, 'pression'); porte(-290, -78, 'z', 12, 'pression')

# ================================================================ VIE (est)
c = couloir('c_vie', 40, -6, 400, 6)
aile(c, 'vie',
     cote_plus=[4, ('cantine', 'Cantine', 60, 50, dict(h=16)), 4, ('cuisine', 'Cuisine', 34, 30), 2,
                12, 4, ('quartiers_a', 'Quartiers A (cabines 1 à 8)', 64, 44), 6, ('douches', 'Douches et sanitaires', 32, 30), 6, ('buanderie', 'Buanderie', 16, 20),
                12, 6, ('sport', 'Salle de sport', 44, 36), 6, ('detente', 'Salle de détente', 40, 34)],
     cote_moins=[4, ('infirmerie', 'Infirmerie', 44, 36, dict(sure=True, sans_grille=True, porte='volet')), 4, ('pharmacie', 'Pharmacie', 24, 20, dict(porte='badge1')), 4, ('bureau_medecin', 'Bureau du médecin', 24, 22),
                 12, 4, ('securite', 'Poste de sécurité', 40, 32, dict(porte='badge1')), 6, ('scelles', 'Salle des scellés', 24, 20, dict(porte='badge2')), 6, ('vestiaire_v', "Vestiaires de l'équipage", 30, 26), 6, ('toilettes_v', 'Toilettes', 12, 16),
                 12, 6, ('reunion', 'Salle de réunion', 40, 32), 6, ('bureau', 'Bureau du commandant', 34, 30, dict(porte='badge2')), 6, ('archives_adm', 'Archives administratives', 18, 18)])
couloir('tunnel_serre', 400, -4, 470, 4, h=10, verre=True)
salle('serre', 'Serre hydroponique', 'vie', 470, -40, 540, 40, h=18, note='bacs de culture, lampes violettes'); porte(470, 0, 'x', 8, 'etanche')
c = couloir('c_vie_n1', 144, 6, 156, 210)
aile(c, 'vie',
     cote_plus=[60, ('quartiers_b', 'Quartiers B (cabines 9 à 14)', 56, 40), 8, ('recueillement', 'Salle de recueillement', 26, 22), 8, ('placard_v1', 'Placard', 12, 10)],
     cote_moins=[60, ('reserve_alim', 'Réserve alimentaire', 36, 30), 6, ('chambre_froide_v', 'Chambre froide alimentaire', 26, 22), 6, ('placard_v2', 'Placard', 12, 10)])
salle('radio', 'Salle radio', 'vie', 134, 210, 166, 240, h=12, note='cul-de-sac'); porte(150, 210, 'z', 6, 'porte')
c = couloir('c_vie_n2', 284, 6, 296, 150)
aile(c, 'vie',
     cote_plus=[46, ('cabine_cdt', 'Cabine du commandant', 30, 26, dict(porte='badge2')), 8, ('bibliotheque', 'Bibliothèque', 36, 30)],
     cote_moins=[52, ('linge', 'Réserve de linge', 24, 20), 6, ('placard_v3', 'Placard', 12, 10), 6, ('salle_jeux', 'Salle de jeux', 34, 28)])
couloir('desc_vie', 144, -124, 156, -6, escalier=(-112, -76, -16, 0))
c = couloir('c_vie_s2', 284, -92, 296, -6)
aile(c, 'vie',
     cote_plus=[0, ('magasin', 'Magasin général', 40, 34)],
     cote_moins=[0, ('cellule', "Cellule d'isolement", 16, 16, dict(porte='badge2', sans_grille=True)), 4, ('salle_info', 'Salle informatique', 30, 30)])

# ================================================================ HUB → MACHINES
couloir('desc_sud', -6, -124, 6, -40, escalier=(-112, -70, -16, 0))

# ================================================================ MACHINES (niveau -16)
E = -16
c = couloir('c_mach', -320, -136, 320, -124, elev=E)
aile(c, 'machines',
     cote_plus=[36, ('traitement_air', "Traitement de l'air", 50, 30), 6, ('oxygene', "Réserves d'oxygène", 36, 28), 42,
                6, ('controle_m', 'Salle de contrôle des machines', 44, 30), 6, ('local_elec', 'Local électrique', 26, 22), 6, ('placard_m1', 'Placard', 12, 10), 56,
                ('chaufferie', 'Chaufferie', 46, 30), 6, ('vestiaire_m', 'Vestiaire des techniciens', 28, 24), 70,
                ('pieces', 'Magasin de pièces détachées', 50, 30), 6, ('reserve_m', 'Réserve', 24, 20)],
     cote_moins=[('reservoirs_eau', "Réservoirs d'eau douce", 56, 46), 6, ('pompes', 'Salle des pompes', 56, 44), 6, ('placard_m2', 'Placard', 12, 10), 6,
                 ('soudure', 'Atelier de soudure', 40, 32), 44,
                 ('centrale', 'Centrale électrique', 80, 70, dict(h=26)), 20,
                 ('ateliers', 'Ateliers', 56, 44), 6, ('outillage', "Salle d'outillage", 22, 20), 16,
                 ('entrepot', 'Entrepôt principal', 70, 56, dict(h=18)), 8, ('filtration', 'Filtration', 40, 32), 8, ('placard_m3', 'Placard', 12, 10)])
c = couloir('c_mach_o', -106, -300, -94, -136, elev=E, escalier=(-300, -278, -28, -16))
aile(c, 'machines', cote_plus=[26, ('sous_station', 'Sous-station électrique', 36, 30)],
     cote_moins=[26, ('vannes', 'Salle des vannes', 36, 30), 6, ('carburant', 'Stock de carburant', 30, 26, dict(porte='badge1'))])
c = couloir('c_mach_c', -6, -278, 6, -136, elev=E)
aile(c, 'machines', cote_plus=[4, ('compresseurs', 'Compresseurs', 40, 34), 6, ('placard_m4', 'Placard', 12, 10)],
     cote_moins=[4, ('turbines', 'Salle des turbines', 44, 40, dict(h=18))])
c = couloir('c_mach_e', 94, -300, 106, -136, elev=E, escalier=(-300, -278, -28, -16))
aile(c, 'machines', cote_plus=[26, ('batteries', 'Local des batteries', 40, 32), 6, ('controle_ballasts', 'Contrôle des ballasts', 34, 28)],
     cote_moins=[26, ('huiles', 'Huiles et lubrifiants', 26, 22), 6, ('placard_m5', 'Placard', 12, 10)])

# ================================================================ FONDS (niveau -28)
F = -28
c = couloir('c_fonds', -130, -312, 130, -300, elev=F)
aile(c, 'fonds',
     cote_moins=[('inondes', 'Compartiments inondés', 80, 60, dict(eau=10, h=16, porte='etanche')), 8, ('puisard', 'Puisard', 30, 26, dict(eau=6, porte='etanche')), 8,
                 ('ballasts', 'Ballasts et capsules de survie', 100, 60, dict(h=20, note='2 capsules de 3 places'))])

# ================================================================ gaines : une gaine au plafond de chaque couloir, une branche vers chaque salle
GAINES, GRILLES = [], []
SOUDEES = {'archives', 'bureau', 'ballasts', 'cabine_cdt', 'quarantaine', 'scelles'}
EXCLUS = {'tunnel_verre', 'tunnel_serre'}
for c in COULOIRS:
    if c['id'] in EXCLUS: continue
    x0, z0, x1, z1 = c['rect']; cx, cz = (x0 + x1)/2, (z0 + z1)/2
    pts = [(x0 + 2, cz), (x1 - 2, cz)] if (x1 - x0) >= (z1 - z0) else [(cx, z0 + 2), (cx, z1 - 2)]
    GAINES.append(dict(id='g_' + c['id'], pts=pts, elev=c['elev']))
for s in SALLES:
    if s.get('sans_grille') or 'couloir' not in s: continue
    c = next(c for c in COULOIRS if c['id'] == s['couloir'])
    x0, z0, x1, z1 = s['rect']; cx0, cz0, cx1, cz1 = c['rect']; mx, mz = (x0 + x1)/2, (z0 + z1)/2
    if (cx1 - cx0) >= (cz1 - cz0): a = (mx, (cz0 + cz1)/2); b = (mx, mz)
    else: a = ((cx0 + cx1)/2, mz); b = (mx, mz)
    GAINES.append(dict(id='b_' + s['id'], pts=[a, b], elev=s['elev'], branche=True, inonde=bool(s.get('eau'))))
    GRILLES.append((b[0], b[1], s['id'], s['id'] in SOUDEES))
GAINES += [dict(id='puits_rech', pts=[(-150, -60), (-150, -130)], elev=0, vertical=True),
           dict(id='puits_vie', pts=[(150, -60), (150, -130)], elev=0, vertical=True),
           dict(id='puits_fonds', pts=[(0, -278), (0, -306)], elev=-16, vertical=True)]

# ================================================================ points d'intérêt (énigmes, objets fixes) : (salle, dx, dz, type, nom)
_P = [
    ('rotonde', 0, 0, 'console', 'Console principale (courant)'), ('centrale', -20, -15, 'disjoncteurs', 'Disjoncteurs A'),
    ('local_elec', 0, 0, 'disjoncteurs', 'Disjoncteurs B'), ('sous_station', 0, 0, 'disjoncteurs', 'Disjoncteurs C'),
    ('pompes', 0, 0, 'vannes', 'Vannes de pression'), ('archives', 0, 0, 'coffre', 'Coffre des archives'),
    ('radio', 0, 0, 'radio', 'Radio et enregistrement de la balise'), ('serveurs', 0, 0, 'serveurs', 'Disques de données'),
    ('hangar', 0, 0, 'drone', 'Console du drone'), ('bureau', 0, 0, 'cle', 'Clé des capsules 1'), ('controle_ballasts', 0, 0, 'cle', 'Clé des capsules 2'),
    ('ballasts', -25, -15, 'capsule', 'Capsule 1'), ('ballasts', 25, -15, 'capsule', 'Capsule 2'), ('labo_c', 0, 0, 'bassin', 'Bassin brisé'),
    ('navette', 0, 20, 'reservoir', 'Réservoir de confinement'), ('c_rech', 0, 0, 'levier', 'Levier du sas de pression'),
    ('ateliers', 0, 0, 'chalumeau', 'Chalumeau'), ('securite', 0, 0, 'cameras', 'Écrans des caméras'), ('observatoire', 0, 0, 'baie', 'Baie vitrée'),
    ('module_prel', 0, 0, 'echantillon', 'Échantillon rare (C-17)'), ('controle_m', 0, 0, 'console', 'Contrôle des pompes'),
]
def _centre(id):
    for o in SALLES:
        if o['id'] == id: x0, z0, x1, z1 = o['rect']; return (x0 + x1)/2, (z0 + z1)/2
    return None
POINTS = []
for sid, dx, dz, k, nom in _P:
    c = _centre(sid) if sid != 'c_rech' else (-290, -70)
    POINTS.append((c[0] + dx, c[1] + dz, k, nom))

def studs(v): return v*S
def taille_studs(s):
    x0, z0, x1, z1 = s['rect']; return (x1 - x0)*S, (z1 - z0)*S

def verifier():
    """chevauchements (vue de dessus) entre salles, et entre salles et couloirs ; renvoie la liste des problèmes"""
    pb = []
    def inter(a, b):
        return min(a[2], b[2]) - max(a[0], b[0]) > 0.01 and min(a[3], b[3]) - max(a[1], b[1]) > 0.01
    for i, a in enumerate(SALLES):
        for b in SALLES[i + 1:]:
            if inter(a['rect'], b['rect']): pb.append(f"salle {a['id']} × salle {b['id']}")
        for c in COULOIRS:
            if inter(a['rect'], c['rect']): pb.append(f"salle {a['id']} × couloir {c['id']}")
    return pb

def surfaces():
    sal = sum((s['rect'][2] - s['rect'][0])*(s['rect'][3] - s['rect'][1])*(0.71 if s['forme'] == 'octo' else 1) for s in SALLES)*S*S
    cou = sum((c['rect'][2] - c['rect'][0])*(c['rect'][3] - c['rect'][1]) for c in COULOIRS)*S*S
    return sal, cou

if __name__ == '__main__':
    for p in verifier(): print('CHEVAUCHEMENT', p)
    sal, cou = surfaces()
    print(f'{len(SALLES)} salles, {len(COULOIRS)} couloirs, {len(PORTES)} portes, {len(GRILLES)} grilles')
    print(f'surface salles {sal:,.0f} studs² ({sal*STUD_M**2:,.0f} m²), couloirs {cou:,.0f} studs² ({cou*STUD_M**2:,.0f} m²)')
