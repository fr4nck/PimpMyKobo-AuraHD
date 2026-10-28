# Store `*.pmkb` V0 — sous-lot L06-A

Contrat **expérimental hors ligne**, sans installation de paquet, sans exécution et sans accès au matériel.

Le futur paquet `*.pmkb` devra porter un `manifest.json` UTF-8 de **4 Kio maximum**.
Ce lot valide **uniquement** son contenu JSON. La structure de l'archive, l'intégrité des fichiers, la gestion des liens symboliques, les chemins d'installation, les données utilisateur, les désinstallations et la gestion des conflits restent à définir/tester dans L06-B. Ne pas utiliser cette API comme vérification complète d'une archive inconnue.

Champs requis : `manifest_version` (entier `1`), `id` (identifiant à segments minuscules), `name` (nom lisible), `version` (`MAJOR.MINOR.PATCH`), `target` (`dragon`), `runtime` (`pmkb-ui-v0`), `entrypoint` (chemin interne relatif normalisé), `dependencies` (identifiants sans doublon), `network` (booléen). Les champs inconnus et les doublons sont refusés plutôt qu'ignorés.

Le profil cible est volontairement **strict** : le validateur refuse les autres appareils, les runtimes inconnus, les dépendances non présentes dans la liste fournie et l'accès réseau sans autorisation explicite du futur hôte. `read_manifest(...)` n'accorde **aucune permission réelle** et ne lance aucune application. `pmkb-ui-v0` est une étiquette de compatibilité envisagée, pas la preuve d'un runtime déployé sur la Kobo.

`example/manifest.json` est purement synthétique : `bin/demo` **n'existe pas** et le paquet n'est pas installable. La validation s'effectue en Python standard 3.10+, sans dépendance externe :

```sh
python3 -m unittest discover -s tests -p 'test_store_manifest.py' -v
```

**NON QUALIFIÉS :** création d'archive `*.pmkb`, installation/désinstallation, P3, lancement ARM, intégration Launcher, écriture matérielle, signatures et compatibilité E606C0 réelle.


## État intégré — Store natif hors ligne V0

Le Store est maintenant une application enregistrée dans le Launcher natif sur
`main`. Le lancement alloue sa propre surface PMKB-UI, sans partager les pixels
de Notes ou de la Calculatrice. L'hôte peut lui transmettre une charge bornée
`pmkb-store-view-v1` ; un JSON invalide est refusé sans remplacer le catalogue
précédent.

Fonctions qualifiées sur hôte :

- lancement et fermeture via `PMKBAppHost`, avec génération de cycle ;
- catalogue vide ou jusqu'à 64 applications installées non vérifiées ;
- pagination par gauche/droite ou zones tactiles du pied de page ;
- ouverture tactile d'une fiche : nom, version, identifiant, déclaration réseau
  et état explicitement non lançable ;
- retour à la liste sans service résident ;
- présentation par le backend PMKB injecté, avec conservation des régions
  `dirty` en cas d'échec ;
- captures C réelles liste/détail en 320×480 et 1080×1440 dans la QA hôte.

Le Store V0 reste **hors ligne et non installateur sur la Kobo**. Les archives
`*.pmkb`, l'installation et la désinstallation restent qualifiées uniquement
dans des racines temporaires synthétiques par les contrats Python existants.
Aucun paquet n'est exécuté, aucun réseau n'est activé et aucune écriture P3,
FIRST BOOT, P1, P2 ou microSD physique n'est ajoutée.

## Contrôles de provenance ARM (L08-A à L08-H)

Le prévol ELF (identité ARM EABI5, `PT_INTERP`, `DT_NEEDED`) et les inventaires bibliothèques de L08 sont des **outils hôte de diagnostic**, séparés du Store embarqué. Ils ne constituent ni une autorisation d'installation, ni une garantie de compatibilité avec un noyau de Kobo Aura HD.

Les composants L08-E/F/G analysent un export rootfs **déjà extrait**, consignent SHA-256 et liens, puis contrôlent la cohérence interne de l'observation : [ROOTFS-SNAPSHOT-L08E.md](ROOTFS-SNAPSHOT-L08E.md), [ROOTFS-ALIASES-L08F.md](ROOTFS-ALIASES-L08F.md), [ROOTFS-EVIDENCE-L08G.md](ROOTFS-EVIDENCE-L08G.md).

Le lot L08-H ajoute une comparaison *archive TAR.GZ fournie en mémoire ↔ fichiers exportés* sans extraction ni écriture : [ROOTFS-TAR-RECONCILE-L08H.md](ROOTFS-TAR-RECONCILE-L08H.md). Cette comparaison ne prouve pas la correspondance avec une image ext4 d'origine, ni l'authenticité de l'archive. Aucun snapshot Kobo réel n'a été qualifié par ce lot ; aucune donnée de la liseuse n'est modifiée.
