# RobloxBlenderModel

Modèles 3D pour un jeu Roblox d'horreur, générés par scripts Python exécutés dans Blender (sans fenêtre) via GitHub Actions.

- `jobs/<nom>/main.py` : script Blender d'un travail ; `jobs/CURRENT` : le travail à lancer.
- Chaque push sur `main` qui touche `jobs/` lance le workflow `Blender`.
- Les résultats (rendus, `.fbx`/`.glb`, journal) sont publiés sur la branche `sorties`, dans un dossier au nom du travail.
