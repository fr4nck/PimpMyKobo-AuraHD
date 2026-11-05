# Simulation locale du remplacement de P1

`tools/restore-rootfs.py` V1 ne sait travailler que sur des **fichiers locaux**.
Il ne restaure aucun support physique, ne monte rien et ne lance aucune
commande de disque. Le mode par défaut vérifie les entrées et affiche un
plan JSON sans créer de fichier. `--simulate` crée une **nouvelle copie** du
disque local puis remplace P1 dans cette copie ; l'image source reste en
lecture seule.

## Entrées et exemple

Il faut un manifeste `legacy/imported`, les fichiers pré-P1/P2 qu'il
référence, une P1 et son rapport `rebuild-rootfs` ou `build-koreader-rootfs`, une image
disque locale complète et une destination nouvelle :

```bash
python3 tools/restore-rootfs.py legacy-import.json rootfs.img.rebuild.json rootfs.img disk-source.img disk-simulation.img --accept-legacy-import
# Après un plan ready, ajouter --simulate pour créer la copie.
```

Les manifestes natifs ne sont pas pris en charge par ce premier contrat.
Les chemins `/dev/...`, Windows PhysicalDrive, UNC, leurs alias résolus et
les entrées non ordinaires sont refusés avant lecture. Aucun mode physique
ni option permettant de contourner ces refus n'existe.

## Contrôles

L'outil relit les preuves de l'import, puis vérifie dans l'image disque :
MBR valide sans dépassement de sa taille, géométrie identique, HWCONFIG
E606C0, SHA-256 pré-P1 et P2 identiques aux preuves. Il vérifie la taille et
le SHA de la nouvelle P1, la référence au manifeste d'import, la cohérence
du rapport de reconstruction et ses contrôles déclarés complets.

Le rapport n'est pas signé. Pour `rebuild-rootfs`, le simulateur vérifie ses
contrôles filesystem déclarés. Pour `build-koreader-rootfs`, il exige le
contrat typé E606C0 (taille et SHA de P1, `complete=true`, aucune erreur,
`physical_restore_eligible=false`, `hardware_qualified=false`) et relance
`e2fsck -f -n` sur le fichier image local après comparaison des paramètres ext4 réels avec le rapport et la référence P2. Le rapport conserve le résultat de cette revalidation et `write_authorized=false`. Aucun des deux chemins ne prouve
que l'image démarrera sur la liseuse.

Après copie et remplacement, il relit P1 et compare son SHA à la nouvelle
image. Il compare les SHA avant/après de la zone pré-P1, de P2, de P3 et de
**tout le suffixe après P1**, qui couvre aussi les espaces libres et les
octets après P3. Il vérifie la taille de la copie et le SHA du disque source
inchangé. Le résultat conserve la provenance déclarée et
`physical_restore_eligible=false`.

La copie nécessite l'espace disponible correspondant à la taille logique
complète du disque, même si le fichier source est sparse. Une destination
existante, son `.part` ou son `.simulation.json` interdit l'opération.
Une erreur de copie/validation laisse au plus une copie `.part` non validée.
La publication sans écrasement exige des liens physiques dans le dossier
de destination. Si la publication du rapport échoue après celle de l'image,
le résultat est `failed` ; l'image publiée a néanmoins passé les contrôles,
et le rapport doit être conservé depuis la sortie JSON avant toute utilisation.

Le plan inclut `candidate_source` avec l'outil producteur et le SHA-256 de son
rapport; le backend Live accepte ces deux contrats explicitement et exige que
le candidat embarqué corresponde exactement au plan. Le plan conserve
`write_authorized=false` et `physical_restore_eligible=false`.

Le succès produit `disk-simulation.img` et
`disk-simulation.img.simulation.json`. Il ne constitue jamais une
autorisation de restauration physique et ne qualifie pas le contenu P3
au-delà de son maintien à l'identique.

## Validation synthétique et données manquantes

Les tests couvrent les refus, les collisions, les corruptions, un changement
de source, l'espace insuffisant et l'absence d'écriture des entrées. Sous
Linux, une chaîne synthétique réelle import → reconstruction ext4 →
simulation vérifie le remplacement exact de P1 et tous les octets préservés.

Les sauvegardes locales pré-P1/P1/P2 ne suffisent pas à constituer une image
disque historique complète : P3 et la capacité totale de la carte ne sont
pas établies par ces fichiers. Une démonstration synthétique doit être
identifiée comme telle et ne doit jamais présenter une P3 inventée comme
une sauvegarde réelle.
