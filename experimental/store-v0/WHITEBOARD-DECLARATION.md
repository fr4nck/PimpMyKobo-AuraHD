# Store V0 — Tableau blanc : catalogue et paquet non installable

Le manifeste `example/whiteboard-manifest.json` déclare `org.pmkb.whiteboard` pour `dragon` et `pmkb-ui-v0`, sans réseau ni dépendance.

Ce manifeste est **un exemple de déclaration**, pas une offre d'installation. Le Store natif n'autorise pas le lancement d'une application au seul vu du manifeste ; son protocole `pmkb-store-view-v1` représente des installations synthétiques avec `launchable=false`.

Le test `tests/test_whiteboard_store_manifest.py` vérifie le manifeste réel, les refus cible/runtime/réseau/chemin et soumet un ZIP synthétique contenant seulement ce manifeste au prévol réel `archive_contract.inspect_archive`. Ce ZIP doit être rejeté avec `missing_entrypoint`. Il n'y a aucun exécutable ARM ou installation sur Kobo.

Étapes restant à qualifier séparément : contrat d'entrée exécutable natif depuis un paquet vérifié, artefact ARM reproductible, politique de provenance/signature, mise en quarantaine et tests sur système simulé avant tout essai physique. Ne pas faire passer l'application intégrée au Launcher pour un paquet `*.pmkb` installé.

CI de la PR #33 nécessaire avant sortie du brouillon. Aucune écriture FIRST BOOT, P1/P2/P3 ni microSD réelle.
