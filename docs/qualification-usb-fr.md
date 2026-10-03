# PMKB Qualification USB — Aura HD E606C0

Cette branche prépare un environnement Live dédié au candidat FIRST BOOT #1 figé.

## Identité du candidat

- HEAD : `0b00d858e26c8c65c5764ef939052704350eaaa9`
- image : `PMKB-FIRST-BOOT-1-0b00d858.img`
- taille : `268435968` octets
- SHA-256 : `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`

L'environnement vérifie automatiquement la géométrie Aura HD, l'empreinte PRE-P1, l'empreinte P2/recoveryfs et l'empreinte du candidat. Toute divergence provoque un STOP.

Le runtime refuse toute opération physique sous WSL. Il exige Linux natif/Live, une cible unique, des partitions non montées, une confirmation locale spécifique au candidat et une revalidation de la cible après confirmation. Le périphérique disque complet n'est jamais ouvert en écriture ; P2/recoveryfs et P3 ne sont jamais des cibles d'écriture.

## Construction locale de l'ISO

Le candidat n'est pas versionné dans le dépôt public. `tools/build-qualification-live.sh` assemble localement un ISO Debian Live après avoir contrôlé la taille et le SHA-256 du fichier candidat fourni en argument.

Dépendances de construction : `live-build`, `xorriso`, `squashfs-tools`, `rsync`, `python3`.

Exemple :

```bash
sudo tools/build-qualification-live.sh /chemin/vers/PMKB-FIRST-BOOT-1-0b00d858.img
```

Sortie : `private/qualification-usb/PMKB-Qualification-USB-0b00d858.iso` et son fichier `.sha256`.

Le Live démarre l'interface texte PMKB automatiquement sur tty1. Le logo du projet est inclus dans l'ISO pour le branding, sans ajouter de dépendance graphique au chemin critique.

Le démarrage matériel de l'Aura HD reste UNQUALIFIED tant que le protocole FIRST BOOT sur l'appareil réel n'a pas été exécuté et documenté.
