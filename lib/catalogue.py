"""Registre des objets du kit (nom -> fonction de construction sans argument, renvoie la racine)."""
import kit_labo as L
import kit_quartiers as Q
REGISTRE = {
    'paillasse': lambda: L.paillasse(8.0, seed=1),
    'paillasse_courte': lambda: L.paillasse(5.0, seed=2, evier=False),
    'hotte': lambda: L.hotte(5.0, seed=1),
    'etagere_specimens': lambda: L.etagere_specimens(6.0, seed=1),
    'aquarium': lambda: L.aquarium(seed=1),
    'armoire_vitree': lambda: L.armoire_vitree(seed=1),
    'tabouret': lambda: L.tabouret(1),
    'tableau_blanc': lambda: L.tableau_blanc(seed=1),
    'chariot': lambda: L.chariot(1),
    'lit_superpose': lambda: Q.lit_superpose(1),
    'casiers': lambda: Q.casiers(4, seed=1, ouvert=2),
}
import kit_tech as T
REGISTRE.update({
    'etagere_stockage': lambda: T.etagere_stockage(seed=1),
    'palette_caisses': lambda: T.palette_caisses(1),
    'futs': lambda: T.groupe_futs(3, seed=2),
    'rack_bouteilles': lambda: T.rack_bouteilles(4, seed=1),
    'extincteur': lambda: _grp('Extincteur', T.extincteur()),
    'etabli': lambda: T.etabli(seed=1),
    'armoire_elec': lambda: T.armoire_elec(seed=1, ouverte=False),
    'armoire_elec_ouverte': lambda: T.armoire_elec(seed=2, ouverte=True),
    'rack_serveur': lambda: T.rack_serveur(1),
    'pupitre': lambda: T.pupitre(6.0, seed=1, allume=True),
    'pompe': lambda: T.pompe(1),
    'cuve': lambda: T.cuve(seed=1),
    'groupe_electrogene': lambda: T.groupe_electrogene(seed=1),
    'transformateur': lambda: T.transformateur(1),
    'vannes': lambda: T.nourrice_vannes(seed=1),
})
def _grp(nom, objs):
    from kit_meshes import empty, parent_all
    r = empty(nom); parent_all(objs, r); return r
import kit_vie as V
REGISTRE.update({
    'cuisine': lambda: V.cuisine(10.0, seed=1),
    'frigo': lambda: V.frigo(seed=1),
    'distributeur': lambda: V.distributeur(1),
    'wc_cabine': lambda: V.wc_cabine(1, porte_ouverte=True),
    'lavabo': lambda: V.lavabo(1),
    'douche': lambda: V.douche(1),
    'chaise_bureau': lambda: V.chaise_bureau(1),
    'bureau': lambda: V.bureau(5.0, seed=1),
    'bibliotheque': lambda: V.bibliotheque(seed=1),
    'canape': lambda: V.canape(6.0, seed=1),
    'table_basse': lambda: V.table_basse(1),
    'bac_plantes': lambda: V.bac_plantes(6.0, seed=1),
    'lit_hopital': lambda: V.lit_hopital(1),
    'potence': lambda: V.potence(1),
    'paravent': lambda: V.paravent(1),
    'tiroirs_morgue': lambda: V.tiroirs_morgue(6.0, seed=1),
    'table_autopsie': lambda: V.table_autopsie(1),
})

# variantes hauteur sous plafond 16 (grandes salles) pour les objets reliés au plafond
REGISTRE.update({
    'hotte_h16': lambda: L.hotte(5.0, seed=1, hauteur_plafond=16.0),
    'armoire_elec_h16': lambda: T.armoire_elec(seed=1, ouverte=False, plafond=16.0),
    'armoire_elec_ouverte_h16': lambda: T.armoire_elec(seed=2, ouverte=True, plafond=16.0),
    'bac_plantes_h16': lambda: V.bac_plantes(6.0, seed=1, plafond=16.0),
    'table_autopsie_h16': lambda: V.table_autopsie(1, plafond=16.0),
    'chaise': lambda: Q.chaise(seed=0),
    'table': lambda: Q.table(),
    'horloge': lambda: Q.horloge(),
    'tableau_affichage': lambda: Q.tableau_affichage(seed=3),
    'microscope': lambda: _grp('Microscope', L.microscope((0, 0, 0))),
    'centrifugeuse': lambda: _grp('Centrifugeuse', L.centrifugeuse((0, 0, 0))),
    'ecran_pc': lambda: _grp('EcranPC', L.ecran_pc((0, 0, 0))),
})

# variantes demandées par le générateur de la map (correspondance avec les objets en blocs de nadir_props)
REGISTRE.update({
    'lit_superpose_0': lambda: Q.lit_superpose(0), 'lit_superpose_1': lambda: Q.lit_superpose(1), 'lit_superpose_2': lambda: Q.lit_superpose(2),
    'casiers_1': lambda: Q.casiers(1, seed=3, ouvert=9), 'casiers_2': lambda: Q.casiers(2, seed=4, ouvert=1), 'casiers_4': lambda: Q.casiers(4, seed=5, ouvert=2),
    'armoire_classeur': lambda: V.armoire_classeur(seed=1),
    'etagere_stockage_w24': lambda: T.etagere_stockage(2.4, 1.6, 6.5, seed=3),
    'etagere_flacons': lambda: T.etagere_stockage(6.0, 2.0, 7.0, seed=4, contenu='flacons'),
    'pupitre_12': lambda: T.pupitre(12.0, seed=2, ecrans=3, allume=True),
    'paillasse_sec': lambda: L.paillasse(8.0, seed=3, evier=False),
    'cuve_petite': lambda: T.cuve(3.0, 6.0, seed=2),
    'caisse': lambda: T.caisse(1),
    'poubelle': lambda: Q.poubelle(),
    'bac_plantes_12': lambda: V.bac_plantes(12.0, seed=2), 'bac_plantes_12_h16': lambda: V.bac_plantes(12.0, seed=2, plafond=16.0),
    'table_6x3_2': lambda: Q.table_chaises(6, 3, 2, seed=1), 'table_10x3_8': lambda: Q.table_chaises(10, 3, 8, seed=2),
    'table_12x4_10': lambda: Q.table_chaises(12, 4, 10, seed=3), 'table_4x4_4': lambda: Q.table_chaises(4, 4, 4, seed=4),
    'table_6x3_metal': lambda: Q.table_chaises(6, 3, 0, seed=5, metal=True),
})
REGISTRE['rideau_lit'] = lambda: V.rideau_lit(7.0, seed=1)
