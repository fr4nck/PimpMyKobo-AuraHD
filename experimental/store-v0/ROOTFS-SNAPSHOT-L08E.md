# PMKB Store — L08-E : audit en lecture seule d'un snapshot rootfs extrait

## Objectif

Qualifier les bibliothèques ELF d'un **répertoire rootfs préalablement extrait**, fourni par l'opérateur sur un hôte. L'audit `rootfs_snapshot_audit.py` reçoit un chemin de répertoire et n'utilise que des lectures : pas de `mount`, `dd`, `tar`, écriture, réseau, extraction, lancement de code ARM ni modification de la Kobo.

**Aucun snapshot réel n'a été fourni ou lu lors de ce lot.** Seules des fixtures créées dans des répertoires temporaires sont utilisées pour les tests. Ne jamais présenter leurs résultats comme une preuve de disponibilité sur Kobo Aura HD.

## Contrat de lecture L08-E

`scan_rootfs_snapshot(root, source_id="…", declared_source_sha256=None)` :

- inspecte seulement les enfants immédiats de `lib/` et `usr/lib/` du répertoire fourni. D'autres chemins (par exemple des sous-répertoires multiarch) ne sont **pas couverts** : un SONAME non trouvé y reste *inconnu*, jamais « absent de la Kobo » ;
- refuse le répertoire racine du système, les racines absentes, les comptes d'entrées excessifs et les fichiers trop volumineux ; ne traverse jamais les liens symboliques, y compris les répertoires qui en sont ;
- accepte au maximum 512 candidats, 2 048 entrées par répertoire, 16 Mio par bibliothèque et 96 Mio lus au total ;
- relève nom relatif, taille, SHA-256 du contenu lu, puis l'identité ELF32 ARM EABI5 via le contrat L08-B ; relève les erreurs de format sans déclarer de compatibilité ;
- enregistre les liens symboliques comme `symlink_unresolved` : la présence d'un alias ne prouve **pas** celle de sa cible ;
- produit un SHA-256 déterministe des observations (`audit_sha256`). Le `source_id` identifie la déclaration de provenance. `declared_source_sha256` est une valeur **fournie par l'appelant et non vérifiée** : le scanner ne compare pas le répertoire au fichier-image original ;
- renseigne toujours `hardware_verified: false` et `launchable: false`. Même `arm_eabi5_shared_header` signifie seulement que l'en-tête ELF est compatible en première approximation, pas que les instructions, la libc, les versions de symboles, le loader, le noyau ou les appels système fonctionneront.

`inspect_elf_against_rootfs_snapshot(elf_bytes, root, source_id="…")` relie l'extracteur `DT_NEEDED` de L08-C à l'audit. La comparaison distingue :

| État | Interprétation limitée au snapshot |
| --- | --- |
| `arm_header_observed_only` | un fichier portant le bon nom a un en-tête ELF ARM EABI5 partagé ; ABI/runtime **non qualifiés** |
| `unresolved_symlink` | nom présent mais cible du lien **non suivie** |
| `nonmatching_library_header` | fichier portant le nom attendu, mais en-tête incompatible ou invalide |
| `ambiguous_export_name` | plusieurs candidats homonymes, aucun choix arbitraire |
| `not_observed_in_scanned_directories` | non observé dans les seuls dossiers parcourus, **pas absent du système** |

## Provenance et sécurité

La copie source doit provenir d'un export autorisé dont la provenance et la licence sont vérifiées séparément. Ne pas committer d'images, de bibliothèques Kobo ni de données propriétaires dans GitHub. Le scanner suppose un export local **immuable pendant l'analyse** ; il compare les métadonnées des fichiers avant/après lecture et emploie `O_NOFOLLOW` lorsque disponible. Il n'est pas un inspecteur sécurisé contre un adversaire modifiant le répertoire en parallèle, notamment sur plateformes sans `O_NOFOLLOW`.

L'empreinte d'inventaire ne prouve ni la provenance authentique du rootfs, ni sa correspondance avec P1, P2 ou FIRST BOOT. Il faudra une attestation explicite de la copie d'origine et une stratégie indépendante de vérification des liens et chemins multiarch pour conclure sur la disponibilité des bibliothèques.

## Qualification

`tests/test_store_rootfs_snapshot_audit.py` : fixtures en mémoire et répertoires temporaires, contrôle de hachage, ELF ARM/x86, dépendance `DT_NEEDED`, refus racine et limites, liens non suivis, ambiguïté, intégrité de provenance déclarée. Le cas de création de lien symbolique peut être ignoré sur un runner Windows qui n'en possède pas le privilège.

La CI GitHub du **commit de code** doit être confirmée avant l'adoption du lot. Tests physiques Kobo : **NON EXÉCUTÉS**. Aucune activation d'installation `*.pmkb` ni autorisation d'exécution n'est accordée par cette étape.
