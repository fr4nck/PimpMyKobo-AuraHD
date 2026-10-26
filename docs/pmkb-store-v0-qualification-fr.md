# PMKB — Store *.pmkb V0 : contre-qualification hors matériel

**Lot : L06-B2f — 26 octobre 2026.** Dépôt `fr4nck/PimpMyKobo-AuraHD`, PR [#31 Store V0](https://github.com/fr4nck/PimpMyKobo-AuraHD/pull/31) (OPEN, DRAFT, non fusionnée), branche `feat/pmkb-store-v0` au HEAD **`d352591d29ce108f78b612a55bfe25bfb4309152`**.

## Résultat CI vérifié

[GitHub Actions Tests #40205215577](https://github.com/fr4nck/PimpMyKobo-AuraHD/actions/runs/40205215577) : **COMPLETED / SUCCESS au HEAD exact**. **10 jobs PASS / 0 FAIL** : 8 jobs `unittest` Python 3.10–3.13 sur Ubuntu/Windows, plus 2 jobs Qt. Chacun des huit jobs Python a terminé l'étape `Run unit tests` avec `SUCCESS`. Le workflow utilise `python -m unittest discover -s tests -v`.

Lecture directe des logs Python 3.11 : **345 tests découverts** sur Linux (7 skipped, 0 fail) et Windows (46 skipped, 0 fail). Les méthodes du fichier `test_store_pending_cleanup.py` sont explicitement exécutées : les cas incompatibles avec les droits de création de symlink du runner Windows sont marqués `skipped`, **et non PASS**. Aucune nouvelle exécution locale des tests n'a été réalisée en L06-B2f ; on n'ajoute pas ces résultats aux runs CI.

## Matrice Store V0 — état prouvé

| Fonction | Verdict | Portée et limites |
|---|---|---|
| Manifeste versionné (`manifest_contract.py`) | **PASS hôte** | Validation JSON, compatibilité déclarée, dépendances et demande réseau. Aucune isolation effective du réseau. |
| Archive ZIP (`archive_contract.py`) | **PASS hôte** | Précontrôle des chemins bruts, membres, types et limites. Aucune authentification de provenance. |
| Installation (`install_contract.py`) | **PASS hôte** | Racine Temp synthétique marquée, CRC à l'extraction, inventaire SHA-256, staging, renommage et rollback simulé. Ni P3 ni Kobo. |
| Désinstallation (`uninstall_contract.py`) | **PASS hôte** | Code détaché puis purgé, `data/` conservé. Nettoyage après détachement non atomique. |
| Retraits incomplets (`pending_cleanup_contract.py`) | **PASS hôte** | Inventaire borné et non destructif des `.pmkb-remove-*`. Aucune restauration ni purge automatique. |
| Catalogue local consultable et interface Store | **NON IMPLÉMENTÉ dans ce périmètre** | Pas encore de contrat stable de découverte des applications installées à fournir au Launcher. |
| Enregistrement et lancement des applications dans PMKB-UI/Launcher | **NON QUALIFIÉ** | Aucun binaire ARM ni point d'entrée natif exécuté ; exemple de paquet fictif. |
| Permissions réelles, licences et authenticité des éditeurs | **NON QUALIFIÉ** | Déclarations et empreintes ne constituent pas une signature, une sandbox ou une autorisation effective. |
| Concurrence, récupération après coupure brutale, filesystem réel | **NON QUALIFIÉ** | Le marqueur Temp ne protège pas contre un autre processus ayant accès aux mêmes fichiers. |
| Kobo Aura HD, ARM, e-ink, microSD P3, énergie, FIRST BOOT physique | **NON EXÉCUTÉ** | Aucun accès au matériel ; partitions protégées et image scellée inchangées. |

## Suites ordonnées, à exécuter séparément

**L06-C (prochain sous-lot unique)** : contrat de **catalogue local synthétique en lecture seule**, à partir des dossiers `apps/` et de leurs manifestes. Limiter le nombre d'entrées, refuser les dossiers ambigus ou symlinks, préserver la séparation `apps/` / `data/`, et distinguer applications installées et `cleanup_pending`. Tests dans des répertoires Temp explicitement marqués ; **aucun téléchargement, lancement ni installation physique**.

**L06-D (ultérieur)** : consommation volontaire du catalogue par PMKB-UI/Launcher sans remplacer les huit illustrations ou contredire Notes ADR-005. **L06-E (ultérieur)** : contrats de permissions/identité/licences et préparation ARM ; vérifier séparément compatibilité matérielle et consommation avant usage sur Kobo.

**Invariants** : aucune fusion de la PR #31, aucune modification de FIRST BOOT, P2/recoveryfs, HWCONFIG, waveform, PRE-P1, P1/P3, aucun firmware ni dépendance téléchargé. Le LOT 06 n'est **pas clôturé**, seuls les sous-lots L06-A à L06-B2f sont qualifiés dans leurs limites.
