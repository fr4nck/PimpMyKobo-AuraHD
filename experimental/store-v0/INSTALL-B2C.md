# Store PMKB - L06-B2c : installation dans un repertoire de test

`install_contract.install_archive(archive_bytes, test_root)` publie uniquement les
fichiers de code d'une archive dans `test_root/apps/<app-id>`.

- Le dossier cible doit deja exister sous le repertoire temporaire du systeme
  et contenir `.pmkb-synthetic-root` avec les octets exacts
  `PMKB-STORE-SYNTHETIC-ROOT-V1\n`. L'API ne cree pas cet indicateur.
- L'archive est d'abord verifiee avec le contrat ZIP et le manifeste L06-A/B1.
  Chaque fichier est ensuite lu integralement par blocs de 64 Kio, avec limites
  de taille, verification de CRC ZIP et empreinte SHA-256 en memoire.
- Le code est ecrit dans un sous-dossier temporaire de `apps/`, puis publie en
  une operation `rename` sur le meme systeme de fichiers. Une extraction ou
  publication echouee supprime ses fichiers provisoires.
- Le dossier `data/` est **distinct et jamais modifie**. Une application deja
  installee n'est pas remplacee ; il n'y a ni mise a jour ni desinstallation.
- Les chemins existants de `apps/`, de `data/` ou de l'application qui sont des
  liens symboliques sont refuses avant extraction.

Exemple de qualification hote, sans application ni appareil :

```sh
python3 -m unittest discover -s tests -p 'test_store_install.py' -v
```

**Limites** : cette API est reservee aux racines synthetiques sous le repertoire
Temp du systeme. Le marqueur n'est pas une barriere de securite contre un
acteur local malveillant modifiant les repertoires en concurrence. La CRC ZIP
controle des erreurs accidentelles, **pas** l'authenticite du fournisseur.
Les fichiers sont copies mais jamais executes ; les permissions ARM, la
compatibilite PMKB-UI, le Store graphique, les transactions apres coupure
brutale d'alimentation, la desinstallation et l'usage Kobo restent non qualifies.
