# PMKB Qualification USB — Aura HD E606C0

Cette branche prépare un environnement Live dédié au candidat FIRST BOOT #1 figé.

## Identité du candidat

- HEAD : `0b00d858e26c8c65c5764ef939052704350eaaa9`
- image : `PMKB-FIRST-BOOT-1-0b00d858.img`
- taille : `268435968` octets
- SHA-256 : `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`

Le manifest public conserve la géométrie Aura HD, l'empreinte PRE-P1, l'empreinte P2/recoveryfs et l'identité du candidat.

## Deux contrats physiques séparés

L'interface `tools/pmkb-qualification-usb.py` n'implémente plus d'écriture bloc.

La restauration conservatrice de P1 sur la carte originale passe par :

`tools/restore-p1-linux.py`

La création d'une carte de remplacement passe par :

`tools/replace-microsd-linux.py`

Ce second backend réutilise les contrôles Linux natifs et l'ouverture protégée de périphérique définis dans `restore-p1-linux.py`, mais garde un contrat d'écriture distinct : il construit volontairement une **nouvelle** carte et ne doit jamais assouplir le contrat « P1 seulement » de la carte originale.

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

Dans le mode historique de restauration **sur la carte originale**, P2/recoveryfs et P3 ne sont jamais des zones d'écriture.

Le Live possède désormais un second contrat, séparé, pour **créer une nouvelle microSD**. Dans ce mode, la carte originale est ouverte uniquement en lecture ; PRE-P1 et P2 sont capturés en staging Live, puis la nouvelle carte reçoit PRE-P1 adapté à sa capacité, P1 PMKB, une copie exacte de P2 et une P3 FAT32 `KOBOeReader` neuve. Voir `docs/remplacement-microsd-fr.md`.

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
3. embarque l'interface PMKB, les deux backends physiques séparés et leurs dépendances Python ;
4. embarque localement le candidat et le plan ;
5. inscrit dans `BUILD-IDENTITY.json` les SHA-256 du manifest, du candidat et du plan, ainsi que deux identités Git distinctes : `candidate_head` pour l'image P1 figée et `live_head` pour le code du Live réellement embarqué ;
6. refuse un checkout Git suivi modifié ;
7. produit une ISO dont le nom contient les deux identités courtes, par exemple `PMKB-Qualification-USB-0b00d858-c2a8ae54.iso`, avec son fichier `.sha256`.

Le Live démarre l'interface texte PMKB automatiquement sur tty1. Avant toute saisie d'un périphérique `/dev/...`, l'opérateur choisit la langue de l'interface (français par défaut ou anglais) puis le clavier console. Le français/AZERTY est proposé par défaut ; tous les keymaps présents dans l'image peuvent être affichés et sélectionnés. Le menu permet ensuite de changer langue/clavier, de redémarrer ou d'éteindre proprement le PC. Il n'existe plus d'option « Quitter » laissant tty1 sur un curseur sans interface.

Le menu GRUB de la clé utilise le visuel PMKB à la place du splash Debian d'origine lorsque le logo versionné est disponible.

## Récupérer le candidat depuis un ancien Live

Le candidat privé et le plan scellé sont déjà présents dans toute ancienne ISO/clé PMKB construite avec eux, sous `/opt/pmkb` dans le SquashFS du Live. Il n'est donc pas nécessaire de rallumer le poste de construction uniquement pour récupérer ces deux artefacts.

L'outil `tools/recover-live-bundle.py` permet de les extraire depuis une racine Live ou directement depuis `live/filesystem.squashfs`. Il recalcule et croise :

- la taille et le SHA-256 du candidat ;
- le SHA-256 de `candidate.json` ;
- le SHA-256 du plan scellé ;
- les empreintes enregistrées dans `BUILD-IDENTITY.json` ;
- les drapeaux du plan `write_authorized=false` et `physical_restore_eligible=false`.

Il refuse les chemins `/dev/*` et n'effectue aucune lecture brute ni écriture sur une microSD.

```bash
python3 tools/recover-live-bundle.py \
  /media/PMKB/live/filesystem.squashfs \
  ~/pmkb-recovered
```

La reconstruction du nouveau Live doit ensuite réutiliser **exactement** le candidat et le plan ainsi récupérés ; le builder les revalidera de nouveau avant construction.

## Création de la clé USB sous Windows avec Rufus

Une clé USB de **4 Go ou plus** suffit ; **8 Go** est confortable. Son contenu sera entièrement effacé par Rufus.

Pour la qualification réelle actuellement préparée, l'ISO locale utilisée est :

`private/qualification-iso-real-<LIVE_HEAD>-<date>/PMKB-Qualification-USB-0b00d858-<LIVE_SHORT>.iso`

Le SHA-256 attendu doit être celui du fichier `.sha256` produit avec cette nouvelle ISO ; l'ancien SHA-256 `9f0790…1822` correspond uniquement au Live précédent et ne doit pas être réutilisé.

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

Le parcours recommandé est **Créer / réparer une nouvelle microSD PMKB** : carte originale comme donneuse en lecture seule, retrait de la donneuse, insertion d'une autre microSD, plan lié à cette cible, confirmation destructive explicite, puis construction et relecture de la nouvelle carte. La capacité de la cible n'a pas besoin d'être identique à celle de l'originale ; le backend adapte P3 au reste disponible et impose actuellement au moins 1 Gio de P3 (soit environ 1,51 Gio de capacité minimale théorique totale).

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
