# PMKB Qualification Live payload

Contenu public du Live USB de qualification. Le candidat `.img` n'est volontairement pas versionné : `tools/build-qualification-live.sh` l'injecte uniquement lors de la construction locale après validation de sa taille et de son SHA-256.

- `candidate.json` : identité et géométrie figées du candidat FIRST BOOT #1.
- `pmkb-qualification.service` : lancement automatique de l'interface de qualification sur tty1.
- runtime : `tools/pmkb-qualification-usb.py`.

Aucun fichier de ce dossier n'effectue une écriture pendant la construction de l'ISO.
