"""NADIR-4 — disposition de la base (source unique pour le plan, la maquette Roblox et le kit Blender).
Unités de conception (du) ; S convertit en studs Roblox (1 stud ≈ 0,28 m). Plan : x vers l'est, z vers le nord.
Altitudes (elev) et hauteurs sous plafond (h) déjà en studs. Trois niveaux : 0 (Recherche, Vie, hub), -16 (Machines), -28 (fonds)."""

S = 1.5                     # du -> studs
STUD_M = 0.28               # mètres par stud

SECTEURS = {
    'arrivee':   dict(nom='Arrivée', couleur=(210, 214, 220)),
    'hub':       dict(nom='Hub', couleur=(205, 205, 205)),
    'recherche': dict(nom='Recherche', couleur=(186, 222, 190)),
    'vie':       dict(nom='Vie', couleur=(186, 206, 236)),
    'machines':  dict(nom='Machines', couleur=(240, 206, 168)),
}

def R(id, nom, secteur, x0, z0, x1, z1, elev=0, h=14, **kw):
    d = dict(id=id, nom=nom, secteur=secteur, rect=(x0, z0, x1, z1), elev=elev, h=h, forme='rect')
    d.update(kw); return d

# ---------------------------------------------------------------- salles
SALLES = [
    R('navette', 'Navette Meridian', 'arrivee', -13, 104, 13, 164, h=12, sure=True, note='portail, réservoir de confinement, coffre à preuves'),
    R('amarrage', "Tube d'amarrage", 'arrivee', -5, 94, 5, 104, h=10),
    R('sas', "Sas d'arrivée", 'arrivee', -12, 70, 12, 94, h=12, note='cycle de 10 s, balise de détresse'),
    R('rotonde', 'Rotonde de commande', 'hub', -30, -30, 30, 30, h=20, forme='octo', sure=True, note='console du courant, plan, interphone'),
    # Recherche (ouest)
    R('labo_c', 'Labo C et bassin', 'recherche', -146, 30, -96, 72, h=18, note='bassin brisé 16×16 au centre'),
    R('specimens', 'Salle des spécimens', 'recherche', -136, -10, -96, 24, h=14),
    R('archives', 'Archives C-17', 'recherche', -126, -48, -96, -22, h=12, note='coffre à code'),
    R('serveurs', 'Serveurs de recherche', 'recherche', -84, 20, -50, 48, h=12),
    R('hangar', 'Hangar du drone', 'recherche', -84, -70, -46, -30, h=18, note='console de pilotage, drone Pélican-2'),
    R('sas_pression', 'Sas de décompression', 'recherche', -96, -112, -84, -96, h=12, note='levier à tenir'),
    # Vie (est)
    R('quartiers', "Quartiers de l'équipage", 'vie', 96, 40, 142, 80, h=12, note='couchettes, casiers'),
    R('cantine', 'Cantine', 'vie', 96, -20, 150, 30, h=16),
    R('reunion', 'Salle de réunion', 'vie', 96, -58, 134, -30, h=12, note='tableau blanc des gaines'),
    R('bureau', 'Bureau du commandant', 'vie', 96, -92, 128, -68, h=12),
    R('infirmerie', 'Infirmerie', 'vie', 54, 18, 84, 44, h=12, sure=True, note='porte verrouillable, sans grille'),
    R('securite', 'Poste de sécurité', 'vie', 54, -44, 84, -18, h=12, note='écrans des caméras'),
    R('radio', 'Salle radio', 'vie', 80, 95, 100, 115, h=12, note='cul-de-sac'),
    # Machines (niveau -16, fonds -28)
    R('centrale', 'Centrale électrique', 'machines', -25, -140, 25, -96, elev=-16, h=26),
    R('pompes', 'Salle des pompes', 'machines', -62, -145, -28, -115, elev=-16, h=16),
    R('ateliers', 'Ateliers', 'machines', 32, -140, 68, -110, elev=-16, h=14),
    R('inondes', 'Compartiments inondés', 'machines', -70, -195, -20, -155, elev=-28, h=16, eau=-18, note="eau jusqu'à 10 studs"),
    R('ballasts', 'Ballasts et capsules', 'machines', -10, -197, 60, -160, elev=-28, h=20, note='2 capsules de 3 places'),
]

# ---------------------------------------------------------------- couloirs (escalier : elev0 -> elev1 dans le sens de 'pente')
def C(id, x0, z0, x1, z1, elev=0, h=12, **kw):
    d = dict(id=id, rect=(x0, z0, x1, z1), elev=elev, h=h); d.update(kw); return d

COULOIRS = [
    C('c_nord', -6, 30, 6, 70),
    C('c_ouest', -84, -5, -30, 5),
    C('c_est', 30, -5, 84, 5),
    C('c_sud', -6, -84, 6, -30, escalier=(-70, -40, -16, 0)),          # escalier entre z -70 et -40 : de -16 (sud) à 0 (nord)
    C('epine_r', -96, -96, -84, 85),
    C('epine_v', 84, -95, 96, 95),
    C('desc_r', -96, -130, -84, -112, escalier=(-130, -112, -16, 0)),
    C('c_pompes_o', -96, -136, -62, -124, elev=-16),
    C('hall_m', -62, -96, 62, -84, elev=-16),
    C('c_pompes_n', -50, -115, -40, -96, elev=-16),
    C('c_ateliers_n', 40, -110, 50, -96, elev=-16),
    C('desc_v', 84, -119, 96, -95, escalier=(-119, -95, -16, 0)),
    C('c_ateliers_e', 68, -131, 96, -119, elev=-16),
    C('desc_pompes', -50, -155, -40, -145, escalier=(-155, -145, -28, -16)),
    C('desc_centrale', -6, -160, 6, -140, escalier=(-160, -140, -28, -16)),
    C('c_fonds', -20, -182, -10, -170, elev=-28, eau=-18),
]

# ---------------------------------------------------------------- portes : (x, z, mur ('x' = mur vertical sur le plan, 'z' = horizontal), largeur, type)
TYPES_PORTE = {
    'ouvert': 'passage ouvert', 'porte': 'porte manuelle', 'motorisee': 'porte motorisée (courant)',
    'badge1': 'badge niveau 1', 'badge2': 'badge niveau 2', 'badge3': 'badge niveau 3',
    'volet': 'volet blindé (salle sûre)', 'sas': 'sas (cycle 10 s)', 'pression': 'sas de pression (levier)',
    'etanche': 'porte étanche', 'navette': 'porte de la navette',
}
PORTES = [
    (0, 104, 'z', 6, 'navette'), (0, 94, 'z', 6, 'porte'), (0, 70, 'z', 8, 'sas'),
    (0, 30, 'z', 8, 'volet'), (-30, 0, 'x', 8, 'volet'), (30, 0, 'x', 8, 'volet'), (0, -30, 'z', 8, 'volet'),
    (-84, 0, 'x', 10, 'ouvert'), (84, 0, 'x', 10, 'ouvert'),
    (-96, 50, 'x', 8, 'porte'), (-96, 8, 'x', 6, 'porte'), (-96, -35, 'x', 6, 'badge3'),
    (-84, 34, 'x', 6, 'motorisee'), (-84, -50, 'x', 10, 'porte'),
    (-90, -96, 'z', 6, 'pression'), (-90, -112, 'z', 6, 'pression'), (-62, -130, 'x', 6, 'porte'),
    (96, 60, 'x', 6, 'porte'), (96, 5, 'x', 10, 'porte'), (96, -44, 'x', 6, 'porte'), (96, -80, 'x', 6, 'badge2'),
    (84, 31, 'x', 6, 'volet'), (84, -31, 'x', 6, 'badge1'), (90, 95, 'z', 6, 'porte'),
    (90, -95, 'z', 10, 'ouvert'), (68, -125, 'x', 6, 'porte'),
    (0, -84, 'z', 10, 'ouvert'), (0, -96, 'z', 12, 'porte'), (-45, -96, 'z', 8, 'ouvert'), (-45, -115, 'z', 6, 'porte'),
    (45, -96, 'z', 8, 'ouvert'), (45, -110, 'z', 6, 'porte'),
    (-45, -145, 'z', 6, 'porte'), (-45, -155, 'z', 6, 'etanche'), (-20, -176, 'x', 6, 'etanche'), (-10, -176, 'x', 6, 'etanche'),
    (0, -140, 'z', 8, 'porte'), (0, -160, 'z', 8, 'porte'),
]

# ---------------------------------------------------------------- gaines (polylignes, à 2 studs au-dessus du plafond local) et grilles
GAINES = [
    dict(id='reseau_nord', pts=[(-121, 51), (-90, 51), (-90, 8), (-116, 8)]),
    dict(id='reseau_nord_b', pts=[(-90, 8), (-90, -35), (-111, -35)]),
    dict(id='reseau_nord_c', pts=[(-90, -20), (-65, -20), (-65, -50)]),
    dict(id='reseau_nord_d', pts=[(-90, 34), (-67, 34), (-67, 60), (119, 60)]),
    dict(id='reseau_vie', pts=[(90, 60), (90, 5), (123, 5)]),
    dict(id='reseau_vie_b', pts=[(90, 5), (90, -44), (115, -44)]),
    dict(id='reseau_vie_c', pts=[(90, -44), (90, -80), (112, -80)]),
    dict(id='reseau_vie_d', pts=[(90, -31), (69, -31)]),
    dict(id='puits', pts=[(-65, -50), (-65, -105), (-45, -105), (-45, -130)], vertical=True),
    dict(id='reseau_machines', pts=[(-45, -130), (-45, -105), (50, -105), (50, -125)]),
    dict(id='reseau_machines_b', pts=[(0, -105), (0, -118)]),
    dict(id='reseau_fonds', pts=[(-45, -130), (-45, -175), (25, -175)], inonde=True),
]
GRILLES = [  # (x, z, salle, soudée ?)
    (-121, 51, 'labo_c', False), (-116, 8, 'specimens', False), (-111, -35, 'archives', True), (-65, -50, 'hangar', False),
    (-67, 34, 'serveurs', False), (119, 60, 'quartiers', False), (123, 5, 'cantine', False), (115, -44, 'reunion', False),
    (112, -80, 'bureau', True), (69, -31, 'securite', False), (50, -125, 'ateliers', False), (0, -118, 'centrale', False),
    (-45, -130, 'pompes', False), (25, -175, 'ballasts', True), (-45, -175, 'inondes', False),
]

# ---------------------------------------------------------------- points d'intérêt (énigmes, objets fixes)
POINTS = [
    (0, 0, 'console', 'Console principale (courant)'), (-10, -125, 'disjoncteurs', 'Disjoncteurs A'), (55, -135, 'disjoncteurs', 'Disjoncteurs B'),
    (-55, -140, 'disjoncteurs', 'Disjoncteurs C'), (-35, -137, 'vannes', 'Vannes de pression'), (-121, -40, 'coffre', 'Coffre des archives'),
    (90, 110, 'radio', 'Radio et enregistrement de la balise'), (-60, 28, 'serveurs', 'Disques de données'), (-75, -62, 'drone', 'Console du drone'),
    (120, -86, 'cle', 'Clé des capsules 1'), (52, -192, 'cle', 'Clé des capsules 2'), (5, -192, 'capsule', 'Capsule 1'), (30, -192, 'capsule', 'Capsule 2'),
    (-121, 51, 'bassin', 'Bassin brisé'), (0, 150, 'reservoir', 'Réservoir de confinement'), (-92, -104, 'levier', 'Levier du sas'),
    (50, -128, 'chalumeau', 'Chalumeau'), (62, -38, 'cameras', 'Écrans des caméras'),
]

def studs(v): return v*S
def taille_studs(s):
    x0, z0, x1, z1 = s['rect']; return (x1 - x0)*S, (z1 - z0)*S
