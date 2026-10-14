# PMKB Notes — règle UX normative

## Décision et périmètre

L'[ADR-005 de PMSL-Arch](https://github.com/fr4nck/PMSL-Arch/blob/main/docs/ADR/ADR-005-formulaires-densite-informationnelle.md), relue intégralement le 13 octobre 2026 (blob `4017615213eea812b8864a221a3bb4babe9ee2bf`), est la référence **obligatoire** pour PMKB Notes. Cette adaptation concerne uniquement Notes, actuellement prototype navigateur PC. Elle ne modifie ni le launcher, ni FIRST BOOT, ni les partitions, ni les images approuvées. Les API wx citées dans l'ADR se traduisent ici en règles de layout HTML/CSS, sans introduire de framework.

## Règles à conserver

1. **Largeur sémantique** : les contrôles courts utilisent les rôles communs de Notes définis dans `index.html` (`--field-number`, `--field-font`, unités `ch`, espacement `rem`). Toute nouvelle taille doit partir de ces rôles et des métriques de police. Texte long, recherche et espace de travail peuvent s'étendre ; nombre ou code court ne devient pas pleine largeur par défaut.
2. **Densité productive** : priorité à l'espace d'écriture. Aucune grande carte pour une phrase d'état, aucune marge locale arbitraire. Les contrôles temporaires (Aa, Mes notes, palette) restent repliables. Davantage de surface doit offrir davantage de contenu utile.
   **Contrainte utilisateur du 14 octobre 2026 : deux lignes maximum pour tout le haut de l'écran**, titre et onglets inclus. Ligne 1 : commandes. Ligne 2 : titre et Texte/Croquis. Aucun bandeau de présentation ni label supplémentaire au-dessus du contenu. Présentation et palette de dessin sont accessibles dans Plus ; liste et sauvegardes dans Mes notes, typographie dans Aa. À petite largeur, Nouvelle/Mes notes/Plus utilisent leurs icônes avec noms accessibles et infobulles. Les commandes gardent une cible de 44 px. Une erreur ou un panneau explicitement ouvert reste une exception utile ; le contenu de la note n'est pas limité à deux lignes.
   L'état transitoire d'enregistrement remplace le libellé visuel dans la surface du bouton, avec son nom accessible inchangé : il ne repousse jamais les autres raccourcis.
   Exporter reste sur la seconde ligne avec Texte/Croquis : TXT pour le texte, PNG pour le croquis ; un seul export est visible à la fois. À petite largeur, son icône garde un nom accessible et une infobulle précisant le format. Le JSON du carnet reste dans Mes notes.
3. **Groupes sémantiques** : Enregistrer et son indicateur partagent un groupe compact dans la barre d'actions. Police et taille partagent le panneau Aa. Liste, recherche, export/import JSON et rappel de conservation restent dans Mes notes.
4. **État et erreurs** : aucun indicateur au chargement normal ou au repos, aucun espace réservé entre les raccourcis. L'indicateur apparaît pour « En attente… », puis « Enregistré » pendant deux secondes après réussite. « Non enregistré » reste visible en cas d'échec, sans cadre ni hauteur réservée. Toute nouvelle modification annule la disparition programmée du message précédent. La zone d'erreur `role="alert"` est masquée sans erreur ; elle décrit le problème et l'action utile. Une sauvegarde réussie retire l'erreur de stockage, sans effacer une erreur d'import. Un export JSON réussi ne prétend jamais que le stockage local fonctionne. Les erreurs de police restent près du contrôle dans Aa. Ni traceback ni couleur seule.
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

## Sources d'inspiration complémentaires

Consultées le 14 octobre 2026 ; l'ADR-005 et la contrainte utilisateur des deux lignes restent normatives.

- [GNOME HIG — Header Bars](https://developer.gnome.org/hig/patterns/containers/header-bars.html) : peu de commandes, contenu adapté au mode actif, infobulles et groupes fonctionnels. Application dans Notes : l'export suit Texte/Croquis. Les contraintes de déplacement d'une fenêtre desktop ne sont pas transposées à la liseuse.
- [reMarkable — interface 2.0](https://remarkable.com/blog/remarkable-2-0-software-update-new-user-interface-home-screen-gestures-and-sharing-options) : outils de création regroupés dans une barre pour donner plus de place au travail. Inspiration e-ink pour la sobriété et les outils sur demande ; aucune promesse de stylet actif ou de capacité matérielle équivalente sur l'Aura HD.
- [Apple Notes — dessins sur iPad](https://support.apple.com/guide/ipad/add-drawings-and-handwriting-ipada87a6078/ipados) : outils de dessin accessibles au sein d'une note. Inspiration limitée au choix texte/dessin et à la palette contextuelle, sans reprendre les fonctions riches ou l'intégration cloud.

## Vérification de ce lot — 13 octobre 2026

Contrôle navigateur PC réalisé : rendu bureau (914 px), rendu à 320 px sans débordement horizontal, indicateur compact, erreur absente au démarrage normal, rappel JSON dans Mes notes, panneau Aa avec champs courts, fermeture Échap et persistance du titre/texte après rechargement. Les tests locaux passent : 18 tests Node et suite Python de 282 tests (42 ignorés selon l'environnement).

Restent à qualifier dans la recette complète : zoom/DPI 200 %, parcours clavier complet, import réel de polices et fichiers JSON, téléchargement effectif, croquis/tactile. Aucune validation visuelle de l'utilisateur ni qualification matériel n'est acquise par ces contrôles. La CI distante doit confirmer les jobs Windows/Linux du commit publié.

### Ajustement du 14 octobre 2026

À la demande de l'utilisateur, suppression de l'état permanent « Notes locales chargées » et regroupement de tout le haut en deux lignes. Contrôles navigateur réalisés au bureau, à 320 px et en portrait 540 × 720 : commandes sur une ligne, titre et onglets sur la suivante, aucun débordement horizontal, mode Croquis sans troisième ligne de palette. Retour d'enregistrement temporaire dans le bouton, puis disparition au repos. 19 tests Node et 7 tests Python ciblés passent. Ces dimensions restent des essais navigateur, pas une qualification physique Kobo.

L'export contextuel a ensuite rejoint la seconde ligne. Tests actualisés : 20 tests Node et 7 tests Python ciblés passent, avec bascule TXT/PNG et téléchargement dans l'adaptateur simulé. Contrôle navigateur à 320 et 540 px : toujours deux lignes, un seul export visible selon le mode, aucun débordement horizontal. Pas de qualification matérielle ajoutée.
