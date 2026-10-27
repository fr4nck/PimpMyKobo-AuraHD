# PMKB Store L08-J : preuve image ext4 vers export rootfs

Le module ext4_export_provenance.py compare, sans lecture hôte, les octets
d'une image ext4 fournie en mémoire et le rapport export L08-E cohérent
selon L08-G. Il calcule le SHA-256 de l'image et le confronte à l'empreinte
attendue fournie par l'appelant ET à la valeur déclarée dans le snapshot.

L'API compare_ext4_image_to_snapshot(image_bytes, snapshot,
expected_image_sha256=..., expected_audit_sha256=None,
expected_source_id=None) n'ouvre aucun fichier, ne monte, ne décompresse,
ne modifie aucune partition et n'exécute aucun code ARM.

## Périmètre de la vérification

Le lecteur inspecte indépendamment les inodes, extents, répertoires,
fichiers et liens symboliques de lib/ et usr/lib/ dans les octets ext4.
Il contrôle les enfants immédiats contenant .so (512 maximum, 16 Mio
par bibliothèque, 96 Mio cumulés), et compare tailles/SHA-256/cibles
des liens avec l'inventaire exporté. Il détecte les fichiers présents
dans l'image mais absents de l'export et réciproquement.

Les images prises en charge sont des ext4 classiques 32 bits, blocs
1/2/4 Kio, extents de profondeur zéro, fonctionnalités historiques
restreintes. Rejet explicite de 64bit, metadata_csum, inline_data,
extents profonds, répertoires htree indexés, image sale ou tout format
non reconnu. Image entrée de 2 Kio à 320 Mio ; aucune carte entière.

Verdicts : scoped_image_export_match (concordance sur les deux dossiers),
partial_scope (inventaire incomplet), mismatch (divergences).
Le booléen image_to_export_link_verified_for_scanned_scope n'est vrai
que pour la première situation. Tout échec de lecture est un refus,
jamais une preuve que la bibliothèque est absente de la Kobo.

## Limites essentielles

L'empreinte attendue est fournie par l'appelant. Son égalité avec celle
de l'image et la déclaration de l'export ne l'authentifie pas.
L'outil ne démontre ni l'origine physique de P1/N204/E606C0, ni la
complétude du rootfs, ni les droits, le noyau, la libc, la compatibilité
d'exécution ou le lancement d'une application. Tous les indicateurs
image_authenticated_as_kobo_p1, source_provenance_authenticated,
whole_rootfs_verified, hardware_verified, runtime_compatible et
launchable restent FAUX.

Les tests emploient des images et exports synthétiques. Sous Linux CI
avec e2fsprogs, une vraie image ext4 synthétique est construite en
fichier temporaire avec mke2fs et examinée octet par octet. Aucune
archive Kobo ni firmware privé ne sont versés au dépôt.

Ce lot est uniquement une qualification hôte. P1 physique, P2/recoveryfs,
PRE-P1, P3, FIRST BOOT et les images scellées restent inchangés.
L'essai d'une vraie sauvegarde conservée se fera ultérieurement,
avec preuve de provenance indépendante et accord explicite.

## Revue complémentaire (27 octobre 2026)

Les géométries bloc/groupe d'inodes incohérentes, tables d'inodes sortant
de l'image, entrées de répertoire invalides (y compris "."/"..") et
extents physiques se recouvrant sont refusés. Les tests négatifs sont
inclus dans la suite hôte. La vérification par lecture des octets n'est
**pas** équivalente à un fsck ni à l'authentification de toutes les
métadonnées : filesystem_metadata_integrity_verified reste toujours
False. Même avec un résultat scoped_image_export_match, un contrôle
indépendant de l'image d'origine et de l'intégrité du système ext4 sera
nécessaire avant une décision d'installation.
