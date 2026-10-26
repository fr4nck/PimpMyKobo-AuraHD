# PMKB L08-D8a — génération du cycle Launcher

## Défaut traité

Le garde Store comparait l’application active et son pointeur d’instance. Après une
fermeture puis une réallocation à la même adresse, ces deux valeurs pouvaient
redevenir identiques et laisser une ancienne vue Store paraître valide.

## Contrat

La PR #30 ajoute à `PMKBAppHost` un compteur `generation` de 64 bits. Il avance
uniquement après chaque lancement ou fermeture réellement réussi. Les refus
(Store non exécutable, application déjà active, Notes non sauvegardées et
fermeture à vide) ne le modifient pas. Le compteur sature sans reboucler.

La PR #31 capture cette génération lors de l’entrée du Store et la revérifie
avant dessin, présentation, soumission et confirmation asynchrone. Une différence
détache la vue et refuse l’opération. La valeur saturée `UINT64_MAX` est refusée
à l’entrée : aucun emprunt Store ne repose sur un jeton qui ne peut plus avancer.

## Qualification

- PR #30 : tests du cycle Launcher, dont échecs et fermeture Notes refusée.
- PR #31 : changement de génération avec `active` et `instance` inchangés,
  détachement sans écriture, refus de la saturation, puis réentrée explicite.
- Le test croisé épingle le commit PR #30 `209324c3b3246c752e1c57b5220ee46955ad412e`
  et les empreintes Git exactes des deux fichiers Launcher.

La CI des deux commits doit réussir avant qualification. Aucun Store exécutable,
pilote EPDC, thread, réseau, écriture Kobo, modification FIRST BOOT/P1/P2/P3 ou
fusion de PR n’est introduit.
