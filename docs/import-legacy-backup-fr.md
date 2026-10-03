# Import d'une sauvegarde historique

`tools/import-legacy-backup.py` qualifie deux **fichiers locaux** : la zone
pré-P1 complète et l'image P2. Il ne lit aucun périphérique, ne monte rien et
ne modifie pas les images. Il crée exclusivement un nouveau manifeste JSON
(pas de copie des images ni d'écrasement d'un fichier existant).

```powershell
python tools/import-legacy-backup.py C:/Users/Ordi/AuraHD-original-boot.bin C:/Users/Ordi/AuraHD-p2-recovery.img legacy-import.json --expected-pre-p1-sha256 4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6 --expected-p2-sha256 fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a --declare-same-source
```

Les empreintes attendues proviennent de vos relevés historiques. L'outil
les compare aux fichiers lus aujourd'hui ; elles ne prouvent pas l'origine
commune des fichiers. `--declare-same-source` exprime cette association sans
la présenter comme vérifiée.

Le contrat `pmkb-legacy-rebuild-v1` porte `tool=import-legacy-backup`,
`provenance.kind=legacy/imported`, `status=qualified`, `complete=false` et
`qualified_for_rebuild=true`. Ce n'est pas un manifeste natif
`backup-aura-hd` ni une sauvegarde complète.

Vérifications réalisées : fichiers ordinaires et SHA-256 intégraux, signature
MBR, trois partitions sans chevauchement de types compatibles Aura HD,
taille pré-P1 égale à l'offset P1, HWCONFIG E606C0 au format v1.7/39,
taille P2 égale à celle du MBR, superbloc ext4 et dimensions contenues dans P2.
Les paramètres enregistrés sont les tailles de bloc/inode et les masques de
features bruts (y compris `needs_recovery`, sans les masquer).

La géométrie P1/P3 est lue dans le MBR, mais leurs **contenus restent non
qualifiés**. La capacité physique de la carte, une relecture de la source,
l'association des fichiers, la santé du filesystem et les artefacts recovery
ne sont pas vérifiés. En particulier, un superbloc lisible ne prouve pas que
P2 est saine ni que `fs.tgz` permet une reconstruction.

Les chemins des images sont relatifs au manifeste ; conserver ces fichiers
à ces emplacements ou importer à nouveau après déplacement. Le manifeste
n'est pas signé : ses empreintes permettent une comparaison avec les données
historiques, pas une authentification cryptographique de leur provenance.

```bash
python3 tools/rebuild-rootfs.py legacy-import.json /mnt/c/Users/Ordi/AuraHD-p2-recovery.img new-rootfs.img --accept-legacy-import --json
# Ajouter --build sous Linux/WSL pour construire un nouveau fichier local.
```

Sans `--accept-legacy-import`, l'import est refusé. Avec cette option, le
pré-P1 est relu au chemin enregistré, P2 est relue au chemin fourni, les
empreintes et les qualifications sont recalculées et comparées au manifeste.
La construction conserve les contrôles existants de l'archive `fs.tgz`, du
contenu et des métadonnées reconstruits, du MD5 interne lorsqu'il existe,
des paramètres ext4 et d'`e2fsck -f -n`. Les limites de provenance et
`physical_restore_eligible=false` sont conservées dans le rapport final.
L'import ne produit pas d'empreinte cible native et n'est jamais admissible
comme référence pour une restauration physique.

Les chemins de périphériques, leurs alias résolus, les chemins UNC et les
entrées qui ne sont pas des fichiers ordinaires sont refusés. Les tests
synthétiques couvrent les refus, l'absence d'écriture des entrées et, sous
Linux, la reconstruction complète avec maintien de la provenance.
