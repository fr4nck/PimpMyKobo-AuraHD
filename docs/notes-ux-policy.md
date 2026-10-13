# PMKB Notes — règle UX normative

## Décision et périmètre

L'[ADR-005 de PMSL-Arch](https://github.com/fr4nck/PMSL-Arch/blob/main/docs/ADR/ADR-005-formulaires-densite-informationnelle.md), relue intégralement le 13 octobre 2026 (blob `4017615213eea812b8864a221a3bb4babe9ee2bf`), est la référence **obligatoire** pour PMKB Notes. Cette adaptation concerne uniquement Notes, actuellement prototype navigateur PC. Elle ne modifie ni le launcher, ni FIRST BOOT, ni les partitions, ni les images approuvées. Les API wx citées dans l'ADR se traduisent ici en règles de layout HTML/CSS, sans introduire de framework.

## Règles à conserver

1. **Largeur sémantique** : les contrôles courts utilisent les rôles communs de Notes définis dans `index.html` (`--field-number`, `--field-font`, unités `ch`, espacement `rem`). Toute nouvelle taille doit partir de ces rôles et des métriques de police. Texte long, recherche et espace de travail peuvent s'étendre ; nombre ou code court ne devient pas pleine largeur par défaut.
2. **Densité productive** : priorité à l'espace d'écriture. Aucune grande carte pour une phrase d'état, aucune marge locale arbitraire. Les contrôles temporaires (Aa, Mes notes, palette) restent repliables. Davantage de surface doit offrir davantage de contenu utile.
3. **Groupes sémantiques** : Enregistrer et son indicateur partagent un groupe compact dans la barre d'actions. Police et taille partagent le panneau Aa. Liste, recherche, export/import JSON et rappel de conservation restent dans Mes notes.
4. **État et erreurs** : l'indicateur annonce brièvement « En attente… », « Enregistré localement » ou « Non enregistré », sans cadre ni hauteur réservée. La zone d'erreur `role="alert"` est masquée sans erreur ; elle décrit le problème et l'action utile. Une sauvegarde réussie retire l'erreur de stockage, sans effacer une erreur d'import. Un export JSON réussi ne prétend jamais que le stockage local fonctionne. Les erreurs de police restent près du contrôle dans Aa. Ni traceback ni couleur seule.
5. **Labels et validation** : conserver les labels visibles, les limites du modèle, la validation complète avant enregistrement/import et la confirmation avant remplacement. Ne pas transformer destructivement une saisie pour la faire entrer dans le format. JSON reste `pmkb-notes-v1` ; les anciens interlignes sont conservés. Typographie appliquée à toute la note, sans prétendre gérer les passages ou lignes.
6. **Accessibilité** : focus visible, clavier cohérent, contraste monochrome, texte compréhensible sans couleur. Les groupes se replient à largeur réduite ; aucune troncature au zoom. Le statut utilise `role="status"` et reste associé à Enregistrer.
7. **Composants communs** : corriger les rôles et groupes communs avant d'ajouter des exceptions. Toute exception doit préciser sa justification ici. Aucun panneau de dashboard permanent dans l'éditeur.

## Garde-fous et recette avant fusion

- `tests/test_notes_host_assets.py` vérifie la position du statut, l'erreur masquée, le rappel dans Mes notes, les rôles de champs et l'absence de transport réseau/matériel.
- `tests/test_notes_app.cjs` exécute l'adaptateur réel avec DOM, stockage et horloge simulés : états vide/en attente/enregistré, quota, stockage inaccessible ou JSON local illisible, export après échec, import invalide puis valide, conservation du carnet en cas d'échec d'import.
- `tests/test_notes_core.cjs` conserve les garanties du modèle et de rétrocompatibilité. CI : contrat Python sur Windows/Linux ; modèle et adaptateur Node 22 sur Windows/Linux, sur PR et push de la branche #27.
- Ces tests ne prouvent pas le rendu, le stockage réel, le téléchargement ou le tactile. Recette navigateur requise : bureau, largeur 320–375 px, zoom 200 %, navigation clavier, panneau Aa/Mes notes replié et ouvert, autosave, import/export JSON, croquis. Vérifier l'absence de défilement horizontal et de texte coupé.
- Les PR **#25/#26/#27 ne sont pas à fusionner sans validation visuelle explicite de l'utilisateur**. La qualification navigateur n'est pas une qualification Aura HD/e-ink.

Toute évolution de Notes doit respecter cette règle, actualiser les garde-fous concernés et joindre une recette visuelle honnête. Aucun élargissement à d'autres modules n'est implicite.

## Vérification de ce lot — 13 octobre 2026

Contrôle navigateur PC réalisé : rendu bureau (914 px), rendu à 320 px sans débordement horizontal, indicateur compact, erreur absente au démarrage normal, rappel JSON dans Mes notes, panneau Aa avec champs courts, fermeture Échap et persistance du titre/texte après rechargement. Les tests locaux passent : 18 tests Node et suite Python de 282 tests (42 ignorés selon l'environnement).

Restent à qualifier dans la recette complète : zoom/DPI 200 %, parcours clavier complet, import réel de polices et fichiers JSON, téléchargement effectif, croquis/tactile. Aucune validation visuelle de l'utilisateur ni qualification matériel n'est acquise par ces contrôles. La CI distante doit confirmer les jobs Windows/Linux du commit publié.
