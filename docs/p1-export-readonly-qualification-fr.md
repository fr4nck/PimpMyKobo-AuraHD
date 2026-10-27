# PMKB L08-K — sauvegarde P1 vers export, lecture seule

## Objectif

Relier trois preuves sur un hôte, sans action sur la liseuse :

1. La cohérence des fichiers de sauvegarde avec leur manifeste, validée
   par le vérificateur déjà présent : tools/verify-backup-aura-hd.py.
2. Le SHA-256 du fichier canonique p1-rootfs.img, recalculé après cette
   vérification, avec identité/taille du fichier surveillées pendant la lecture.
3. Les bibliothèques de lib/ et usr/lib comparées octet par octet depuis
   l'image ext4 avec l'inventaire d'un export rootfs préexistant, via L08-E/J.

L'outil est tools/qualify-p1-export.py. Il utilise le lecteur ext4 intégré
à PMKB, en mémoire et dans ses limites (image de 320 Mio maximum).

## Préconditions

Disposer d'une **sauvegarde complète et cohérente** créée par
backup-aura-hd.py, incluant P1, ainsi que d'un répertoire rootfs
déjà extrait. Ne pas confondre une archive fs.tgz présente en P2 avec
un véritable dump P1 : L08-K ne transforme pas P2 en preuve P1.

Une fois ces artefacts disponibles, commande indicative, à lancer
sur un ordinateur hôte et jamais sur la liseuse :

    python3 tools/qualify-p1-export.py /chemin/vers/backup /chemin/vers/rootfs-export

L'outil émet exclusivement une réponse JSON sur la sortie standard.
Aucun fichier de sortie, extraction, montage, formatage, flasher, dd,
réseau ou exécution ARM. Il lit les fichiers de sauvegarde et les
bibliothèques exportées en mode lecture seule. Aucune commande
utilisateur n'est nécessaire pour valider ce lot en CI.

## Codes retour et résultats

- 0 : concordance des octets des bibliothèques observées dans le
  **périmètre limité** lib/ et usr/lib entre la P1 sauvegardée et l'export.
- 1 : incohérence ou portée partielle de la comparaison.
- 2 : source refusée (sauvegarde incomplète/incohérente, image absente,
  lien symbolique, taille non admise, SHA divergents ou ext4 non pris en charge).

Les champs image_authenticated_as_kobo_p1, backup_manifest_authenticated,
whole_rootfs_verified, filesystem_metadata_integrity_verified,
hardware_verified, runtime_compatible et launchable restent faux.

Un fichier et un manifeste modifiés simultanément peuvent passer le
vérificateur de sauvegarde : il n'existe **aucune authentification physique
ni signature cryptographique** apportée par L08-K. Le contrôle ne
prouve pas l'état actuel de la microSD, le démarrage du noyau, les
versions de symboles, les bibliothèques transitives ni l'ABI réelle.

## Tests

tests/test_p1_export_readonly_qualification.py utilise une image ext4
**synthétique**, un export temporaire et une réponse de vérificateur
**simulée**. Il couvre l'acceptation limitée, les divergences,
les sauvegardes incomplètes, les empreintes erronées, liens, tailles,
répertoires manquants et l'absence d'écriture. Le vérificateur réel
de sauvegarde possède sa propre suite de tests dans le dépôt.

**Aucun test sur une sauvegarde P1 réelle n'a été réalisé.** Si aucune
sauvegarde P1 d'origine n'est disponible, conserver UNKNOWN pour
cette étape et ne pas inférer une provenance depuis P2, Nickel ou
une image générée artificiellement.

Préserver FIRST BOOT, pré-P1, P1, P2/recoveryfs, P3 et les artefacts
de récupération. Toute écriture physique exigera une autorisation
explicite et un protocole distinct.
