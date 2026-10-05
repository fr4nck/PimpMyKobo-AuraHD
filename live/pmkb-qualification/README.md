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
- `/opt/pmkb/tools/restore-p1-linux.py` et ses dépendances : unique backend d'accès physique.

L'interface ne possède aucun moteur d'écriture propre. Toute opération physique est déléguée au backend renforcé commun.

Au premier lancement, l'interface demande la langue (FR par défaut / EN) puis le clavier avant toute saisie de cible. Tous les keymaps embarqués sont sélectionnables. Le menu expose des actions explicites `Redémarrer` et `Éteindre` via systemd ; l'ancien `Quitter` sans console de reprise n'est plus proposé.

Aucun fichier de ce dossier n'effectue une écriture physique pendant la construction de l'ISO.
