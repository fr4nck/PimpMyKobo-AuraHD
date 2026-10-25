# PMKB Store — L06-B2e : état des nettoyages en attente

`pending_cleanup_contract.pending_removals(test_root)` renvoie uniquement un tuple
trié de **noms** de dossiers `.pmkb-remove-*` encore présents sous `apps/`.
Il n'ouvre pas leurs contenus, n'infère **aucun identifiant d'application** et
ne nettoie **rien**. L'API est utilisable uniquement avec la même racine de
test Temp marquée que L06-B2c/B2d.

Une absence de dossier donne `()`. Une entrée ressemblant à une quarantaine,
mais qui est un fichier, un lien ou une jonction, provoque un refus. Le scan
est limité à 512 entrées (applications et autres entrées comprises) ; il
signale les erreurs de lecture plutôt que de retourner un état incomplet.
Le répertoire `data/` n'est ni ouvert ni modifié.

Test synthétique, sans clone ni dépendance ajoutée :

```sh
python3 -m unittest discover -s tests -p 'test_store_pending_cleanup.py' -v
```

**Important :** un dossier signalé ne prouve ni que son code est entier ni
qu'il peut être restauré. Après une purge partielle, des fichiers peuvent déjà
manquer. Aucune suppression ou récupération automatique n'est autorisée par
cette API. Les courses filesystem, coupures électriques, P3 et la Kobo restent
hors du périmètre qualifié.
