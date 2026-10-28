# L06-B1 — contrôle des membres des archives PMKB

Ce contrat expérimental examine **en mémoire** une archive ZIP destinée au futur Store `*.pmkb`, avec `inspect_archive(bytes)`. Il ne lit que le contenu du manifeste, n'extrait aucun fichier et ne touche pas aux partitions de la Kobo.

- Limites V0 : ZIP compressé ≤ 8 Mio ; 128 entrées ; 8 Mio par fichier ; total déclaré décompressé ≤ 24 Mio.
- Refus : chemin absolu/traversant, doublons insensibles à la casse, lien symbolique, périphérique, chemin incohérent ou non canonique, chiffrement ZIP et compression non prévue.
- Exige `manifest.json` à la racine et un `entrypoint` présent sous forme de fichier non vide ; la validité du manifeste dépend du validateur L06-A et du consentement réseau explicite.
- Test : `python3 -m unittest discover -s tests -p 'test_store_archive.py' -v`.

**La réussite du précontrôle n'autorise aucune installation.** Les contenus des fichiers autres que le manifeste ne sont ni décompressés ni authentifiés ; leurs CRC ne sont pas contrôlées ici. L06-B2 devra vérifier les octets pendant une extraction bornée dans un répertoire temporaire, installer atomiquement et préserver les données utilisateur. Aucun téléchargement, lancement natif ou test matériel ne fait partie de L06-B1.
