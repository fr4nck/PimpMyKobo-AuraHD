# PMKB Store V0 — L06-B2d : desinstallation synthetique

`uninstall_contract.uninstall_app(test_root, app_id)` n'agit que dans une racine de test
Temp deja creee et munie du marqueur exact `.pmkb-synthetic-root`. Il reutilise
le contrat de racine de l'installateur L06-B2c. Aucune partition de la Kobo,
aucun repertoire utilisateur reel et aucun service n'est accessible via cette API.

- Identifiant d'application strictement valide ; l'application doit etre un
  dossier ordinaire dans `apps/<app-id>` avec un manifeste valide correspondant.
- Parcours borne de l'arborescence code (512 entrees, 24 Mio) ; refus des liens
  symboliques, des types speciaux et des arbres surdimensionnes. Ni `apps/` ni
  `data/` ne doivent etre des liens symboliques. Les jonctions Windows sont
  egalement refusees lorsque Python expose `os.path.isjunction`.
- Premiere phase : renommage sur le meme volume vers `apps/.pmkb-remove-*`.
  Un echec avant ce renommage laisse l'application complete a sa place.
- Seconde phase : suppression du dossier de retrait. Si elle echoue, l'appel
  renvoie l'erreur `cleanup_pending` et son attribut `pending_path`. L'application
  ne figure plus dans `apps/<app-id>`, mais un nettoyage du dossier de retrait
  reste necessaire. **Il n'y a pas de garantie de rollback apres suppression
  partielle**, ni de nettoyage automatique des dossiers orphelins.
- `data/<app-id>` n'est jamais cree, lu, modifie ou supprime par la desinstallation.
  Les donnees utilisateur restent presentes apres une desinstallation reussie.

Commande de qualification hote, exclusivement sur repertoires temporaires
synthetiques :

```sh
python3 -m unittest discover -s tests -p 'test_store_uninstall.py' -v
```

Ce contrat ne gere ni mises a jour, ni fichiers tenus ouverts, ni acces
concurrents malveillants, ni interruption electrique brutale. Le marqueur Temp
n'est pas une barriere de securite contre un processus local ayant les memes
droits. Un succes sur hote ne qualifie pas l'installation sur P3, les permissions
ARM, la restauration apres coupure ou le lancement d'applications sur Aura HD.
