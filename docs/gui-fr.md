# Atelier local Qt/PySide6

Première interface graphique : lecture de rapports, inspection d'une image explicitement sélectionnée, import historique, préparation/reconstruction de P1, simulation et préparation d'un plan. Aucun bouton de restauration physique, détection de carte ou élévation de privilèges. Les fichiers de sortie doivent être nouveaux. L'association des fichiers historiques reste déclarée et non vérifiée ; l'acceptation de cette provenance est explicite.

## Lancer depuis le dépôt

Python 3.10 ou plus et Qt/PySide6 sont nécessaires pour l'interface uniquement. Installer Qt dans un environnement virtuel, puis lancer depuis le dépôt :

```sh
python -m venv .venv
# Linux : .venv/bin/python ; Windows : .venv/Scripts/python.exe
.venv/bin/python -m pip install PySide6-Essentials==6.10.2
.venv/bin/python tools/pmkb.py gui
```

Sur Windows, remplacer `.venv/bin/python` par `.venv/Scripts/python.exe`. La reconstruction effective est désactivée dans l'interface Windows ; elle nécessite Linux ou WSL avec e2fsprogs, fakeroot et tar. Sous WSL, l'affichage Qt nécessite un environnement graphique fonctionnel. Aucun passage automatique de Windows vers WSL n'est effectué.

Après installation du paquet Debian, `pmkb gui` utilise le Python système : Qt doit être disponible dans cet interpréteur. Si Qt est installé dans un environnement virtuel, utiliser explicitement son Python :

```sh
.venv/bin/python /usr/lib/pimpmykobo-aura-hd/pmkb.py gui
```

Le paquet ne contient et n'installe pas Qt. `pmkb gui --help` et les commandes CLI fonctionnent sans Qt.

## Rapports et opérations

La progression indique seulement qu'une opération est en cours, sans pourcentage estimé. Attendre sa fin avant de fermer la fenêtre. Les commandes existantes travaillent dans un sous-processus sans shell ; leur validation reste obligatoire. Une interruption peut laisser un fichier temporaire : examiner les diagnostics avant de relancer.

Lire un rapport ne rejoue pas les contrôles et ne prouve pas son authenticité. Les rapports et diagnostics sont limités à 16 Mio dans l'interface. L'enregistrement crée une copie JSON sans écraser de fichier existant. Les tests utilisent uniquement des fichiers synthétiques ; ils ne qualifient pas le démarrage ni une restauration matérielle.
