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
