# PMKB — Paquet système compact V1 (hors matériel)

**Statut : prototype de conditionnement local, non installable.**
**Cible : Kobo Aura HD N204 / E606C0, FIRST BOOT #1 scellé.**

## Décision

La sauvegarde brute de notre carte interne 32 Go (31 914 983 424 octets) reste
conservée **intacte** et séparée du dépôt. Elle n'est **pas** le format de
distribution de PMKB.

Un paquet ZIP privé ne contient que les régions indispensables au système :

| Archive ZIP | Origine exacte | Taille décompressée |
| --- | --- | ---: |
| `system/pre-p1.bin` | Pré-P1 conservée et vérifiée, dont MBR, HWCONFIG et chaîne de boot | 9 961 472 octets |
| `system/p1-first-boot.img` | **P1 FIRST BOOT scellée**, pas la P1 Kobo d'origine | 268 435 968 octets |
| `system/p2-recoveryfs.img` | P2 recovery Kobo conservée et vérifiée bit à bit | 268 435 968 octets |
| `pmkb-system.json` | Manifeste généré et lié à `candidate.json` | Quelques Ko |

**Total système non compressé : 546 833 408 octets (521,5 Mio).**
La taille ZIP dépend des contenus réels et ne peut pas être déduite uniquement
des tailles de partitions : **ne pas annoncer une taille compressée mesurée
avant de construire le paquet réel**.

P3, les livres et les données de l'utilisateur sont **exclus**.
Une future opération d'installation créera séparément P3 en FAT32
`KOBOeReader` adaptée à la capacité réelle de la microSD cible.
Ce futur lien vers l'installateur n'est **pas** implémenté par ce prototype.

## Identité du candidat figé

- Image : `PMKB-FIRST-BOOT-1-0b00d858.img`
- Provenance : `0b00d858e26c8c65c5764ef939052704350eaaa9`
- P1 SHA-256 : `7980fec15cb62ca3c2cabcb64cbbb683446fbf64070d75b45acf9a5e99e0f67c`
- Pré-P1 SHA-256 : `4b0c72f9d38a2d81d4d5ffb316b1b0d1efcb8e4bf0fa8610025e75fef837c2b6`
- P2 SHA-256 : `fe7885d391a5627cf2b04bd75518cf8fb5b0f379b29032727adb29cba35b968a`

Source de vérité : [manifest du candidat](../live/pmkb-qualification/candidate.json).
Ne pas recalculer de nouvelles références arbitraires pour les faire correspondre
à des fichiers inattendus.

## Outil

`tools/pack-pmkb-system.py` propose seulement :

- `build` : vérifie la géométrie et les SHA-256 attendus, compresse les trois
  fichiers en ZIP DEFLATE, inscrit le manifeste et relit **le ZIP complet**
  avant publication atomique de la sortie ;
- `verify` : refuse les membres inconnus, dupliqués, chemins indirects,
  liens symboliques, tailles non conformes, données altérées et manifeste
  ne correspondant pas au candidat épinglé.

Les entrées sont des **fichiers réguliers locaux** ; chemins `/dev/*`, volumes
Windows `PhysicalDrive`, UNC et liens symboliques sont refusés.
Aucune fonction n'ouvre un disque, ne fabrique P3, n'écrit une partition, ne
monte un filesystem ou ne lance un firmware.

La réussite prouve la concordance **avec les empreintes déclarées** et
l'intégrité de l'archive obtenue, **pas** la provenance authentique des
empreintes, la capacité de récupération ni le démarrage réel sur Aura HD.
Les entrées doivent avoir été acquises et qualifiées indépendamment.
Le projet dispose déjà de `backup-aura-hd.py` et
`verify-backup-aura-hd.py` pour une sauvegarde **par régions**, sans P3 par
défaut ; leurs manifestes ne sont pas interchangeables avec ceux des
acquisitions historiques.

### Exemple de fabrication sur fichiers déjà vérifiés

Environnement **Windows 11, PowerShell**, dans le dépôt PMKB :

~~~powershell
cd C:\Users\Ordi\Documents\GitHub\PimpMyKobo-AuraHD
python .\tools\pack-pmkb-system.py build --manifest .\live\pmkb-qualification\candidate.json --pre-p1 D:\PMKB-prive\pre-p1.bin --p1 D:\PMKB-prive\PMKB-FIRST-BOOT-1-0b00d858.img --p2 D:\PMKB-prive\p2-recoveryfs.img --output D:\PMKB-prive\PMKB-system-0b00d858.zip
python .\tools\pack-pmkb-system.py verify --manifest .\live\pmkb-qualification\candidate.json --package D:\PMKB-prive\PMKB-system-0b00d858.zip
~~~

Ces **chemins sont des exemples**, pas des emplacements constatés.
L'outil **n'extrait pas** automatiquement des données d'une carte ou d'une
sauvegarde de 32 Go ; il consomme les trois fichiers attendus.
Il refuse d'écraser un ZIP existant.

## Bornes de responsabilité

- **Sauvegarde intégrale de 32 Go** : conserver privée, immuable, indépendante.
  C'est le recours historique ; un ZIP système n'en est pas l'équivalent.
- **Archive système compacte** : privée, non publiable sur GitHub / Releases
  sans qualification des droits sur bootloader, recovery et runtime.
- **Dépôt Git public** : uniquement outils, tests synthétiques, manifeste de
  références et documentation ; aucun dump ou firmware propriétaire.
- **MicroSD de test 16 Go** : taille prévue, pas une preuve de compatibilité.
  Aucune opération sur cette carte n'est réalisée ici.
- **FIRST BOOT matériel** : `UNQUALIFIED` tant qu'il n'a pas démarré
  réellement sur l'Aura HD avec rapport écran / tactile / éclairage / P3.

Le backend `tools/replace-microsd-linux.py` sait **déjà** ajuster P3 à la
taille d'une nouvelle carte, mais il lit actuellement une **carte donneuse en
lecture seule**. Son alimentation éventuelle depuis le paquet ZIP compact
représente un **lot distinct**, à qualifier avant toute écriture. Ne pas le
présenter comme déjà compatible avec ce ZIP.

## Tests et publication

Tests synthétiques ciblés :
`python -m unittest discover -s tests -p test_pack_pmkb_system.py -v`.
CI Linux et Windows à observer à la révision de code correspondante.

Les tests ne contiennent aucun bloc Kobo réel, et aucun résultat synthétique
ne doit promouvoir les contrôles matériels à `PASS`.
