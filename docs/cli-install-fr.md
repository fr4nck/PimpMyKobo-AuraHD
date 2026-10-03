# Installer la commande pmkb sur Debian/Ubuntu et WSL

Le paquet local `pimpmykobo-aura-hd` installe la commande `pmkb`, les outils Python et leur documentation. Python 3.10 ou plus est requis. Les dépendances système sont Python, e2fsprogs, fakeroot et tar ; aucun module Python tiers obligatoire, service, règle udev ou script de maintenance n'est ajouté. L'installation ne lance aucun outil et n'accède à aucun périphérique. Aucun dump ou fichier Kobo privé n'est inclus.

## Installation et suppression

Sur Debian/Ubuntu ou leur distribution WSL, depuis le dossier contenant le paquet :

```sh
sudo apt install ./pimpmykobo-aura-hd_0.2.0_all.deb
pmkb --version
pmkb --help
pmkb rebuild-rootfs --help
```

APT peut installer les dépendances système nécessaires. Pour supprimer uniquement ce paquet :

```sh
sudo apt remove pimpmykobo-aura-hd
```

L'outil n'enregistre aucun service ni configuration système. Les données privées, rapports et images restent dans les dossiers que l'utilisateur choisit ; la suppression du paquet ne les supprime pas.

## Commandes

| Commande | Usage |
|---|---|
| `pmkb inspect` | Inspection en lecture seule d'une image ou d'un périphérique ; sans source, recherche des disques accessibles comme l'inspecteur existant. |
| `pmkb verify-recovery` | Vérifier un dossier recovery déjà extrait. |
| `pmkb import-legacy` | Qualifier des fichiers de sauvegarde historique. |
| `pmkb rebuild-rootfs` | Plan local par défaut ; `--build` reconstruit P1 dans un nouveau fichier. |
| `pmkb simulate` | Plan local par défaut ; `--simulate` crée une nouvelle image complète avec P1 remplacée. |
| `pmkb prepare-p1` | Produire un plan vérifiable de restauration P1 à partir des preuves locales. |
| `pmkb restore-p1` | Vérifier les fichiers locaux par défaut ; modes physiques explicites réservés à Linux natif. |

Les arguments, sorties JSON et codes de retour sont ceux des scripts correspondants : ajouter `--help` après le nom de la commande. Sans commande, `pmkb` affiche l'aide uniquement. Il n'élève jamais automatiquement les privilèges. Les scripts directs du dépôt restent utilisables.

Exemple d'inspection de fichier, sans détection de périphériques :

```sh
pmkb inspect /chemin/full-card.img --json --hash-boot
```

Sous WSL, qualification, reconstruction et simulation sur fichiers sont possibles. `pmkb restore-p1` continue à refuser les modes physiques sous WSL ; l'installation du paquet ne change pas ce contrôle. La première restauration reste prévue sur Linux Live USB natif, après autorisation explicite distincte : voir [la procédure](restore-p1-linux-fr.md). Préparer ou installer l'application ne donne pas cette autorisation.

## Construction du paquet local

Dans le dépôt, depuis Debian/Ubuntu ou WSL avec `dpkg-deb` :

```sh
python3 tools/build-deb.py /dossier/existant/pimpmykobo-aura-hd_0.2.0_all.deb \
  --maintainer 'Votre nom <votre-adresse@example.org>'
```

Renseigner une identité de contact réelle pour votre paquet. Le constructeur utilise une liste explicite de scripts et documents, normalise les fins de ligne Linux, fixe propriétaires et horodatages pour une archive reproductible, et refuse d'écraser une sortie existante. Il ne nécessite pas root et n'installe rien. Le fichier `build-info.json` dans la documentation installée contient les SHA-256 des scripts/documents et la version. Il s'agit d'un paquet construit localement, pas d'une publication dans les dépôts Debian ou Ubuntu.

Les outils sont installés dans `/usr/lib/pimpmykobo-aura-hd`, le lanceur dans `/usr/bin/pmkb`, et les documents dans `/usr/share/doc/pimpmykobo-aura-hd`. La liste des fichiers exclut les sauvegardes, firmware, tests et le constructeur lui-même.

L’atelier graphique optionnel est disponible avec `pmkb gui` lorsque Qt/PySide6 est installé pour le même interpréteur. Voir [l’interface locale](gui-fr.md). La CLI fonctionne sans Qt.
