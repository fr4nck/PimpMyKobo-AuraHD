# PMKB Qualification Live payload

Contenu public du Live USB de qualification.

Le candidat `.img` et le plan de restauration revu ne sont volontairement pas versionnés : `tools/build-qualification-live.sh` les injecte uniquement lors de la construction locale après validation.

Le Live contient :

- `candidate.json` : identité et géométrie figées du candidat FIRST BOOT #1 ;
- `restore-plan.json` : plan revu, injecté localement et scellé par son SHA-256 ;
- `BUILD-IDENTITY.json` : empreintes du manifest, du candidat et du plan ;
- `pmkb-qualification.service` : lancement automatique de l'interface sur tty1 ;
- `/usr/local/sbin/pmkb-qualification` : interface opérateur ;
- `kbd` + `console-data` : outils et ensemble de keymaps console ;
- le splash GRUB est remplacé par le logo PMKB versionné lors de la construction ;
- `/opt/pmkb/tools/restore-p1-linux.py` et ses dépendances : backend strict de restauration P1 sur la carte originale ;
- `/opt/pmkb/tools/replace-microsd-linux.py` : backend séparé de création d'une nouvelle microSD à partir d'une donneuse lue uniquement.

L'interface ne possède aucun moteur d'écriture propre. Toute opération physique est déléguée à l'un des deux backends renforcés selon le contrat choisi ; l'interface elle-même n'ouvre jamais un périphérique bloc.

Au premier lancement, l'interface demande la langue (FR par défaut / EN) puis le clavier avant toute saisie de cible. Tous les keymaps embarqués sont sélectionnables. Le menu expose des actions explicites `Redémarrer` et `Éteindre` via systemd ; l'ancien `Quitter` sans console de reprise n'est plus proposé.

Aucun fichier de ce dossier n'effectue une écriture physique pendant la construction de l'ISO.


## Parcours de réparation recommandé

Le premier choix du menu crée une **nouvelle microSD PMKB** :

1. lecture seule de la microSD originale ;
2. capture en RAM de PRE-P1/HWCONFIG et P2/recoveryfs ;
3. retrait de la carte originale ;
4. insertion d'une nouvelle microSD d'une capacité suffisante ;
5. préparation d'un plan lié à cette cible ;
6. confirmation destructive explicite ;
7. création de PRE-P1 + P1 PMKB + P2 recovery + P3 FAT32 `KOBOeReader` adaptée à la capacité réelle ;
8. relecture et vérification.

La carte originale n'est jamais ouverte en écriture par ce parcours.


Les lectures/écritures longues du parcours de remplacement affichent une progression texte : pourcentage, MiB traités et débit. Aucun effet graphique n'est ajouté au Live FIRST BOOT.


## Identité de l'ISO

Une ISO PMKB embarque désormais deux HEAD distincts dans `BUILD-IDENTITY.json` :

- `candidate_head` : provenance du candidat P1 figé ;
- `live_head` : commit exact du code Live et des backends embarqués.

Le nom de l'ISO contient les deux identifiants courts afin qu'une reconstruction du Live ne puisse pas être confondue avec une ancienne ISO utilisant le même candidat P1.
