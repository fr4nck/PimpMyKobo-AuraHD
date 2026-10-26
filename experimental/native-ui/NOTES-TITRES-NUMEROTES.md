# Mes notes — titres automatiques numerotes (ADR-005)

Le titre initial des nouvelles notes natives suit l'identifiant croissant du carnet : `Sans titre 1`, `Sans titre 2`, etc. Le titre ne change pas tant qu'il est renseigne librement. Lorsqu'un champ titre est vide ou constitue uniquement d'espaces Unicode, son propre numero est restaure au moment de quitter le champ, et jamais au milieu de la saisie.

Le numero est derive de l'identifiant `pmkb_NNNNNN` deja present en RAM, sans nouveau compteur, allocation permanente, fichier ou service. Il n'est pas recycle durant la session ; une note renommee ne change pas la numerotation des nouvelles notes. Le banc C11 verifie les titres 1 a 100, les changements de focus et la conservation des titres personnalises.

Ce prototype ne sauvegarde toujours pas ses notes sur disque, et ne fournit pas de mecanisme de rechargement entre deux demarrages. Pas de modification Kobo physique ni P1/P2.
