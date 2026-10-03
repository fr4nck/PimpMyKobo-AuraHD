# FIRST BOOT #1 — préparation de convergence documentaire/Git

Audit du 3 octobre 2026. Documentation uniquement ; aucune fusion, construction,
exécution du candidat, écriture périphérique ou modification de P2.
Les résultats ci-dessous sont limités aux commits figés, pas à un futur HEAD
de reconstruction. Ce document ne remplace ni protocole ni compte rendu d'essai.

## 1. Références examinées

| Branche | HEAD exact |
| --- | --- |
| main | `f2234302203525ac1118e6243c213e96471e0135` |
| integration/pmkb-first-boot-1 | `a8ce226bcd46483feb8e35e49f826fa076098bfb` |
| docs/first-boot-qualification | `ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf` |
| docs/first-boot-evidence | `d64a6e82d10ab1bb8833f3dbd9f464a27de1777a` |

L'intégration et la qualification descendent de ce main. La branche preuves
descend de la qualification : les quatre fichiers de la qualification sont
donc aussi présents dans preuves par ascendance, pas par duplication indépendante.
Cette branche de préparation part de main et modifie seulement les README
racine FR/EN et ajoute le présent rapport.

## 2. Fichiers communs et conflits

| Lot / base de comparaison | Documentation modifiée |
| --- | --- |
| Intégration / main | ROADMAP FR/EN, tools/README.md ; ajouts audit, builder, prototype, état FIRST BOOT et preflight |
| Qualification / main | docs/README.md, docs/README.en.md ; ajout du protocole FR/EN |
| Preuves / qualification | docs/README.md, docs/README.en.md ; ajout de sept modèles/conventions/index |
| Préparation README / main | README.md, README.en.md ; ajout de ce rapport |

Les seuls fichiers documentaires modifiés en commun par qualification et preuves
sont **docs/README.md et docs/README.en.md**, dans une chaîne parent/enfant.
L'intégration ne les modifie pas. Les README racine ne changent dans aucun des
trois lots audités ; ils ne recouvrent donc pas les nouveaux changements ici.
Le fichier tools/README.md est un autre index, modifié par l'intégration seule.

Contrôle par `git merge-tree --write-tree` sur les **six paires** parmi les quatre
branches : code 0 partout, aucun conflit textuel. Aucun ref, index ou arbre de
travail fusionné ; seuls des objets Git temporaires de simulation sont produits.
Les trois modifications se combinent également sans conflit dans l'ordre proposé
(à recontrôler dès que les HEAD changent).

**Risques futurs** : nouveaux changements de Codex dans README/ROADMAP/index,
rebase, squash ou cherry-pick peuvent changer l'ascendance et cette conclusion.
Après un squash de qualification, preuves peut réafficher ses ajouts de protocole :
rebaser le lot preuves sur le nouveau main ou reprendre uniquement son commit
`d64a6e8`, puis vérifier le diff. Ne pas résoudre les index en remplaçant tout
le fichier par une seule version : conserver protocole et dossier de preuves.

## 3. Liens et doublons

Vérification des destinations locales des liens Markdown explicites, dans tous
les fichiers .md suivis des quatre branches : **aucun chemin local manquant**.
Cela ne vérifie pas les ancres, liens implicites, URL externes ou contenus privés.
Les destinations GitHub figées nouvellement utilisées dans les README ont été
contrôlées contre les arbres Git correspondants ; aucun appel HTTP nécessaire.

Les chemins `experimental/offline-rootfs`, `experimental/offline-audit`,
`tools/build-koreader-rootfs.py`, `tools/audit-arm-runtime.py` et
`tools/preflight-koreader.py` existent dans l'intégration, **pas dans main**.
Ne pas créer prématurément des liens relatifs vers eux dans main. Les nouveaux
README emploient des liens GitHub figés, utilisables avant fusion.

Pas de seconde copie des 25 procédures dans preuves : les modèles référencent
les IDs et le protocole. Les README, ROADMAP, contrat builder et état FIRST BOOT
répètent légitimement le statut, mais leurs instantanés doivent être distingués.
L'histoire de reconstruction Kobo/P1 dans les README n'est **pas** une preuve
de boot PMKB : la nouvelle section explicite cette séparation.

## 4. Textes obsolètes ou incohérences à traiter à la convergence

Ces fichiers ne sont pas modifiés par ce lot. Les corriger documentairement
lors de la convergence validée, sans en déduire un changement matériel.

| Texte dans l'intégration a8ce226 | Écart constaté / action documentaire |
| --- | --- |
| ROADMAP FR/EN, en-tête « feat/rebuild-rootfs-spec » | Instantané d'une ancienne branche ; dater et rattacher à la convergence retenue |
| ROADMAP FR §5 / EN §6 : audit parallèle « non fusionné ici », scanner non adopté | Déjà fusionné et adopté dans a8ce226 ; conserver l'historique daté ou remplacer par l'état d'intégration |
| ROADMAP : userspace et intégration KOReader présentés comme à construire ; EN « still untested against real inputs » | Distinguer outil/prototype existant et validation du candidat réel encore attendue ; actualiser seulement avec le résultat Codex |
| docs/build-koreader-rootfs-spec-{fr,en}.md, lien avec les chantiers | Références à une fusion jetable et correctif preflight à adopter : désormais intégrés ; ne plus présenter ces phrases comme état courant |
| Même contrat, refus général de nickel_conf.lua | La table FIRST BOOT distingue compatibilité dormante et accès Nickel réel ; harmoniser le texte sans promettre l'absence de tous les modules de compatibilité |
| docs/preflight-koreader-fr.md : appel _copy_tree/_scan_for_nickel | Le code a8ce226 appelle scan_tree_for_nickel ; décrire l'interface actuelle |
| docs/audit-arm-runtime-fr.md : quatre scripts bootstrap, réglages Nickel encore actifs | Code courant inclut pmkb-check-onboard et defaults.custom.lua ; les deux réglages sont désactivés dans le profil intégré |
| tools/README.md : « futur preflight fusionné » | Le preflight est déjà présent dans la même intégration |
| docs/pmkb-first-boot-1-{fr,en}.md : aucun chantier fusionné dans main | Vrai à l'instantané ; marquer l'historique après fusion, ne pas le laisser comme constat courant |
| Commentaire defaults.custom.lua « Not installed » | Contredit l'installation par le builder et l'état d'intégration ; signalé seulement, aucune modification rootfs/profil dans ce lot |
| README main : KOReader/userspace/Qt et outil natif encore à intégrer | README FR/EN préparés ici : disponibilité locale séparée de qualification physique |

Les chiffres de tests des anciens audits sont des résultats de leurs lots,
pas ceux du futur candidat. Ne pas remplacer ces chiffres par une estimation
ni reprendre une matrice CI sans l'associer au commit effectivement validé.
Les guides de sauvetage et ROADMAP historiques restent utiles mais ne peuvent
autoriser la nouvelle image FIRST BOOT.

## 5. Ordre de fusion proposé — aucune fusion exécutée

1. **Attendre le résultat Codex et figer l'intégration finale** : commit,
   SHA-256/ taille P1, manifeste, audits image/contenu reliés aux octets de
   l'image, résultats de tests. Résoudre les FAIL et les inconnues logicielles
   applicables. Actualiser les passages obsolètes ci-dessus dans un lot
   documentaire approuvé. Ce gate logiciel n'autorise ni écriture ni boot.
2. **Intégration → main**, après revue/validation de ce commit final.
   Elle apporte les outils et documents auxquels les lots suivants se réfèrent.
3. **Qualification → main**, en conservant si possible son ascendance pour
   ne pas recréer les ajouts dans preuves. Vérifier que les références figées
   du protocole correspondent au candidat ou noter les écarts, sans changer
   NOT TESTED en PASS.
4. **Preuves → main** : vérifier que le diff restant ne contient que les sept
   modèles et les deux liens d'index, sans seconde copie du protocole.
5. **README/convergence → main**, après relecture des phrases d'instantané
   et remplacement des liens courants par les chemins locaux désormais présents.
   Garder les liens figés comme provenance lorsque nécessaire.

Rejouer le contrôle Git sur les HEAD retenus avant chaque fusion.
Si le candidat n'est pas validé, les lots documentaires peuvent rester prêts
sur leurs branches ; ne pas faire une fusion de code anticipée pour les débloquer.

## 6. Ce que le résultat Codex devra encore renseigner

- Commit exact de construction et identité de l'image : SHA-256 P1, taille,
  manifeste, versions KOReader/runtime et relation arbre/image.
- Verdicts applicables des audits/preflight, éventuels FAIL/UNQUALIFIED restants
  et résultats de tests associés à ce commit.
- État « reconstruction en cours » à remplacer seulement par une validation
  hors ligne réellement démontrée ; disponibilité dans main après fusion effective.
- Inconnues d'observabilité pré-UI et écarts aux références du protocole si
  le bootstrap change, sans les masquer dans un README optimiste.

Les résultats Codex de reconstruction ne peuvent jamais remplir PASS pour
framebuffer/tactile/frontlight/P3/USB ou hardware_boot. Tant qu'aucun essai PMKB
réel n'est consigné, ces fonctions restent **UNQUALIFIED** ; les lignes d'essai
restent **NOT TESTED**. Calibre est une exigence V1 toujours non qualifiée
matériellement, même si un premier écran KOReader devient ensuite utilisable.
