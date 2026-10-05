# PMKB Qualification USB — Aura HD E606C0

Cette branche prépare un environnement Live dédié au candidat FIRST BOOT #1 figé.

## Identité du candidat

- HEAD : `0b00d858e26c8c65c5764ef939052704350eaaa9`
- image : `PMKB-FIRST-BOOT-1-0b00d858.img`
- taille : `268435968` octets
- SHA-256 : `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`

Le manifest public conserve la géométrie Aura HD, l'empreinte PRE-P1, l'empreinte P2/recoveryfs et l'identité du candidat.

## Un seul backend physique

L'interface `tools/pmkb-qualification-usb.py` n'implémente plus d'écriture bloc.

Toute ouverture de périphérique, qualification matérielle et éventuelle écriture P1 passe par le backend unique :

`tools/restore-p1-linux.py`

Le Live utilise un plan produit par `prepare-p1-restore.py`. Le SHA-256 exact de ce plan est scellé dans l'ISO lors de sa construction.

Avant une écriture, le backend impose notamment :

- Linux natif/Live root ; WSL, conteneurs et espaces de montage séparés refusés ;
- cible disque complet explicitement saisie par l'opérateur ;
- disque amovible exposé via USB ;
- aucune partition montée, aucun swap actif, aucun holder LVM/RAID/device-mapper ;
- ouverture exclusive et identité noyau conservée ;
- comparaison SHA-256 de la carte complète avec la sauvegarde vérifiée attendue par le plan ;
- staging du candidat et `e2fsck -f -n` ;
- journal durable hors de la carte cible ;
- sauvegarde durable de la P1 originale avant le premier octet écrit ;
- journalisation durable de l'intention d'écriture ;
- écriture strictement bornée à la plage P1 ;
- relecture de P1 et vérification de tous les octets hors P1 ;
- aucun retry automatique et aucun rollback automatique implicite.

P2/recoveryfs et P3 ne sont jamais des zones d'écriture.

## Construction locale de l'ISO

Le candidat et le plan de restauration ne sont pas versionnés dans le dépôt public.

Dépendances de construction : `live-build`, `xorriso`, `squashfs-tools`, `python3`.

Exemple :

```bash
sudo tools/build-qualification-live.sh \
  /chemin/vers/PMKB-FIRST-BOOT-1-0b00d858.img \
  /chemin/vers/restore-plan.json
```

Le builder :

1. vérifie la taille et le SHA-256 du candidat ;
2. valide le contrat du plan scellé et sa correspondance avec le candidat/manifest ;
3. embarque l'interface PMKB, le backend physique unique et ses dépendances Python ;
4. embarque localement le candidat et le plan ;
5. inscrit dans `BUILD-IDENTITY.json` les SHA-256 du manifest, du candidat et du plan ;
6. produit `private/qualification-usb/PMKB-Qualification-USB-0b00d858.iso` et son fichier `.sha256`.

Le Live démarre l'interface texte PMKB automatiquement sur tty1. L'option « Quitter » arrête réellement l'interface ; systemd ne la relance pas automatiquement.

## Création de la clé USB sous Windows avec Rufus

Une clé USB de **4 Go ou plus** suffit ; **8 Go** est confortable. Son contenu sera entièrement effacé par Rufus.

Pour la qualification réelle actuellement préparée, l'ISO locale utilisée est :

`private/qualification-iso-real-529c1e02-2026-10-04/PMKB-Qualification-USB-0b00d858.iso`

SHA-256 attendu :

`9f0790415097a16ad0fb8977e204d8334886a27fcc2864da081bdea8c7141822`

Sous Windows :

1. brancher la clé USB destinée à PMKB ;
2. ouvrir Rufus ;
3. sélectionner **PMKB-Qualification-USB-0b00d858.iso** comme image de démarrage ;
4. vérifier très soigneusement que le périphérique sélectionné est bien la clé USB et non un autre disque ;
5. conserver les paramètres proposés par Rufus pour l'image ISO hybride, sauf besoin matériel particulier ;
6. lancer l'écriture et confirmer l'effacement de la clé ;
7. attendre la fin de l'opération puis éjecter proprement la clé.

Cette opération écrit uniquement la clé USB de qualification. **Elle ne doit jamais viser la microSD interne de la Kobo.**

L'ISO réelle ci-dessus embarque le candidat FIRST BOOT et le plan scellé utilisés pour la qualification matérielle. Elle reste un artefact privé local et n'est pas publiée dans Git. Une future ISO publique légère devra exclure ces artefacts privés et tout composant dont la redistribution n'est pas explicitement qualifiée.

## Utilisation

Pour une qualification en lecture seule, l'opérateur saisit explicitement le disque complet, par exemple `/dev/sdb`.

Pour autoriser l'écriture P1, il faut en plus fournir un répertoire persistant distinct de la carte cible. Ce stockage reçoit :

- le journal durable ;
- le candidat staged ;
- la copie de la P1 originale.

Si ce stockage n'est pas reconnu comme persistant et extérieur à la cible, l'écriture est refusée.

## CI

La CI construit réellement une ISO Debian Live à partir d'un bundle synthétique dédié aux tests. Elle vérifie le SHA-256 de l'ISO et la présence du payload PMKB dans le squashfs.

Le bundle CI est synthétique et ne peut pas être utilisé sur un périphérique physique. Aucun artefact privé n'est publié.

Le démarrage matériel de l'Aura HD reste **UNQUALIFIED** tant que le protocole FIRST BOOT sur l'appareil réel n'a pas été exécuté et documenté.
