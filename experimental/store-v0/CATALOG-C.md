# Store PMKB V0 — L06-C : catalogue local synthétique

`catalog_contract.read_catalog(test_root)` renvoie un catalogue **en lecture seule** depuis une racine temporaire déjà marquée. Le contrat réutilise la validation de racine L06-B2c, le manifeste de L06-A et le suivi des quarantaines L06-B2e.

- `installed` : tuple trié de métadonnées (`id`, `name`, `version`, `entrypoint`, `network_declared`, `state=installed_unverified`). Un dossier ne compte comme installé que si son nom, son manifeste, ses dépendances et son fichier d’entrée non vide sont cohérents. Un état *installed* **n’autorise ni lancement, ni réseau**.
- `cleanup_pending` : noms des dossiers `.pmkb-remove-*`, sans inférence de propriétaire, restauration ou suppression. Un dossier de staging `.pmkb-stage-*` provoque `installation_incomplete` plutôt qu’un faux résultat.
- Refus des dossiers ambigus ou inattendus, des symlinks/jonctions, des manifestes incompatibles et des chemins d’entrée détournés. Au maximum 512 entrées analysées et 64 applications installées ; manifeste lu à 4096 octets maximum.
- `data/` n’est ni lu ni modifié. Aucun accès au réseau, aucun processus lancé, aucun paquet téléchargé. Le catalogue n’effectue aucune écriture.

Tests synthétiques hôte :

```sh
python3 -m unittest discover -s tests -p 'test_store_catalog.py' -v
```

**NON QUALIFIÉS** : concurrence ou modifications du système de fichiers pendant la consultation, lecture sur P3, lancement d’un binaire ARM, intégration au Launcher, autorisations de réseau, signature ou origine des paquets, fonctionnement physique Aura HD. La présence d’un manifeste ne garantit pas l’intégrité ou l’authenticité du code installé.
