# PMKB Store L06-D2 — lecteur C11 passif du protocole V1

Le lecteur `pmkb_store_view_parse(bytes, len, &view)` interprète **uniquement** la forme JSON canonique émise par `store_view_contract.encode_store_view()` : clés alphabétiques, sérialisation compacte ASCII avec échappements Unicode, sans espace interjeté. Un autre ordre de champs, une version inconnue ou une charge partiellement analysée sont **refusés**, pas réparés silencieusement.

Contrat mémoire : **32 Kio maximum en entrée**, **64 applications**, **512 nettoyages en attente**. Une structure de sortie à capacité fixe (~30 Kio) contient id, nom d'affichage UTF-8, version et indicateur réseau déclaratif. Pas de `malloc`, pas de bibliothèque JSON externe, pas de fichier, pas de réseau, pas de boucle permanente. Le titre d'application supporte 80 caractères Unicode au plus (320 octets UTF-8), dont les séquences `\uXXXX` et les paires de substitution valides. U+0000, Unicode invalide et chaînes tronquées sont refusés. Le statut `launchable` demeure toujours faux. Une erreur remet la sortie à zéro.

**Frontière volontaire :** ces métadonnées restent purement descriptives. La présence d'une ligne ne prouve ni un binaire ARM valide, ni une autorisation d'exécution, ni une permission réseau. Le pont C11 `pmkb_launcher_bridge.c` de la PR #30 conserve `store` non exécutable et **n'est pas modifié**. Le branchement UI viendra après contre-qualification et examen de la coexistence des PR #30/#31 ; aucune fusion automatique.

La suite `test_store_view_c11.py` compile, lorsque déjà présent, un compilateur `cc`, `gcc` ou `clang` en C11 strict, exécute les assertions C, puis alimente le lecteur avec de vraies sorties Python `encode_store_view` (Unicode, 64 lignes, compteurs et refus). Lorsqu'aucun compilateur n'est présent sur le runner, elle marque clairement un **SKIP**, jamais un PASS natif. Aucune installation de toolchain ni dépendance téléchargée.

**Non qualifiés :** GUI de Store, launcher, P3, consommation RAM mesurée sur ARM, tactile et écran E-Ink, récupération après coupure, authenticité des paquets. La Kobo et le FIRST BOOT scellé restent inchangés.
