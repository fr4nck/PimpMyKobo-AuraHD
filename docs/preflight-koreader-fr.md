# Préflight KOReader hors matériel

```sh
pmkb preflight-koreader /chemin/rootfs-extrait
pmkb preflight-koreader /chemin/P1-locale.ext4
# Depuis les sources : python3 tools/pmkb.py preflight-koreader ...
```

Ce rapport JSON répond uniquement aux contrôles réalisables sur l'entrée locale fournie. Aucun montage, extraction, lancement ARM, init, restauration ou accès à une carte. Il ne lit pas P2 et n'autorise aucune écriture P1/P2/P3. L'entrée image doit être un fichier de filesystem ext autonome, pas une image disque complète avec MBR. Les chemins physiques, UNC et fichiers spéciaux sont refusés ; utiliser une extraction locale, jamais un rootfs sur une carte montée.

## Verdicts

- `PASS` : contrôles applicables à cette entrée exécutés et réussis hors matériel, dans les limites des outils réutilisés.
- `FAIL` : défaut vérifié par un contrôle disponible, ou entrée invalide. Corriger/examiner avant d'envisager un essai.
- `UNQUALIFIED` : données ou outil manquants pour un contrôle applicable ; aucune conclusion positive globale.

Code de sortie : 0 / 1 / 2 respectivement. `FAIL` prend priorité sur `UNQUALIFIED`. `offline_checks_satisfied` vaut `true`, `false` ou `null` ; `offline_coverage_complete` concerne seulement les contrôles applicables à l'entrée, pas la qualification d'une image complète. Les résultats matériels ne peuvent pas devenir `PASS`. `hardware_qualified=false`, `physical_restore_eligible=false`, `complete=false` et `device_write_attempted=false` sont invariants. Ce rapport a son propre identifiant `preflight-koreader` ; il ne remplace aucun contrat de restauration recovery ou autorisation physique.

## Réutilisation et limites

| Contrôle | Répertoire local extrait | Image ext locale |
| --- | --- | --- |
| Filesystem / intégrité | Répertoire accepté ; intégrité de l'image explicitement `UNQUALIFIED`, non applicable à cette entrée. | `rebuild-rootfs.read_ext_parameters`, puis `e2fsck -f -n`. SHA-256 avant/après via le helper existant. Manque des outils : `UNQUALIFIED`. |
| ELF ARM / dépendances dynamiques | `audit-arm-runtime.audit` ; mêmes limites ABI, symboles, dlopen et recherche du chargeur. | `UNQUALIFIED` : contenu non extrait. |
| Init / bootstrap / bits d'exécution | `audit-arm-runtime.bootstrap` ; contrat exact du prototype, POSIX requis. | `UNQUALIFIED`. |
| /mnt/onboard | `audit-arm-runtime.storage` ; un répertoire n'est pas une preuve de montage. | `UNQUALIFIED`. |
| Présence KOReader | Résultat des contrôles existants de LuaJIT et reader.lua ; pas une validation exhaustive du paquet. | `UNQUALIFIED`. |
| Références Nickel | Scanner du constructeur réutilisé s'il est installé dans le même checkout. | `UNQUALIFIED`. |

Une image dont le filesystem est sain reste globalement `UNQUALIFIED` tant que son contenu n'a pas été audité. Aucun rapport d'un autre répertoire n'est présenté comme une preuve du contenu de cette image. Le préflight ne compare pas l'image à une géométrie P1 préservée, ne vérifie pas ses features contre le noyau conservé, ne certifie pas un paquet KOReader complet ni l'absence de toute dépendance Kobo.

Le contrôle Nickel n'est pas dupliqué : après le fetch initial, la PR #6 sur `feat/build-koreader-rootfs` est apparue avec un scanner, mais sans préflight agrégé. L'agrégateur utilise uniquement `_copy_tree(..., write=False)` puis `_scan_for_nickel` de ce constructeur, lorsqu'il se trouve à côté du préflight. Aucune fonction de construction n'est appelée. Aucun fichier de cette branche n'est copié ou mergé dans `feat/audit-arm-runtime`. L'absence du constructeur ou une interface indisponible donne `UNQUALIFIED`, y compris sur la présente branche. Des références détectées donnent `FAIL` pour examen : ce scanner est un filtre de signatures, pas une preuve sémantique d'utilisation de Nickel ; des faux positifs restent possibles. Un résultat sans référence ne prouve pas une indépendance exhaustive.

Le changement minimal de l'audit ELF signale aussi les erreurs de parcours de répertoires ; il ne doit plus produire un verdict positif après avoir ignoré silencieusement un sous-arbre illisible.

## Qualification laissée au matériel

Framebuffer réel, tactile réel, frontlight, montage réel de P3, USB/Calibre réel et démarrage matériel sont toujours `UNQUALIFIED`, même avec un verdict statique global `PASS`. Ce lot ne prépare pas de protocole d'écriture physique, de retour arrière, d'export USB ou de correction du bootstrap.

## Validation et non-écriture

Fixtures sans firmware : réussite des contrôles statiques applicables avec résultat de scanner synthétique injecté ; refus bootstrap, runtime et stockage ; outil Nickel absent ; réutilisation de son interface sans écriture ; image ext synthétique vérifiée avec conservation intégrale de ses octets. Tous les éléments matériels restent `UNQUALIFIED` dans les scénarios réussis et refusés.

Seul sous-processus direct : `e2fsck -f -n` sur un fichier régulier validé. Le helper de paramètres appelle `dumpe2fs -h`, sans mode d'écriture. Les fonctions de construction, extraction, restauration et montage ne sont jamais appelées. Les fixtures seules créent des fichiers/images dans leurs répertoires temporaires. Le chargement des outils pairs désactive temporairement les écritures de bytecode Python, afin de ne créer aucun cache dans le checkout ou le paquet. Le préflight émet son JSON sur stdout.

Validation locale : 11 tests du préflight et le nouveau test de parcours ELF passent. Suite complète Linux hors confinement fakeroot : 272 tests, 266 réussis, 5 ignorés, 1 échec préexistant (`test_unknown_device_is_undetermined`, déjà reproduit sur main avant ce lot). La CLI et le paquet Debian passent ; la matrice Windows reste à vérifier en CI. Aucun essai matériel n'a été réalisé.
