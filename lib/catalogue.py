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
