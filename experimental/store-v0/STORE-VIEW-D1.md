# PMKB Store V0 - L06-D1 : contrat de consultation pour PMKB-UI

`store_view_contract.snapshot_store_view(test_root)` appelle le catalogue
synthetique L06-C en **lecture seule** et retourne une charge JSON ASCII/UTF-8
deterministe, sans aucun fichier genere. Cette charge est une **proposition de
passerelle de donnees**, et non une interface graphique ou une application
Store executable sur la Kobo.

## Schema `pmkb-store-view-v1`

- `schema` : identifiant de protocole `pmkb-store-view-v1`.
- `scope` : valeur fixe `synthetic_read_only`.
- `items` : tableau trie de 0 a 64 entrees, sans identifiant de fichier a
  executer. Chaque entree porte `id`, `label`, `version`, `network_declared`,
  `state=installed_unverified` et `launchable=false`.
- `cleanup_pending_count` : nombre de suppressions incompletes, de 0 a 512.
  Les **noms et chemins** de quarantaine ne sont pas transmis.
- Charge complete bornee a **32768 octets** ; aucune troncature silencieuse.
  Les textes utilisateur restent de simples donnees JSON, jamais du HTML.

Le code PMKB-UI existant dans la PR #30 garde `PMKB_APP_STORE` avec
`runnable=false`. L06-D1 ne modifie pas ce pont et n'accorde aucune
permission d'execution ou de reseau. Un consommateur futur devra traiter
`label` comme texte, jamais comme `innerHTML` ou commande. Le schema devra etre
valide explicitement avant toute presentation sur l'ecran e-ink.

### Qualification

`python3 -m unittest discover -s tests -p test_store_view.py -v`

L'API pure `encode_store_view(catalog)` est testable avec des fixtures sans
acces disque. Sur l'hote local L06-D1, ses 12 tests utilisent des doubles du
catalogue pour isoler le protocole. La CI GitHub doit confirmer l'importation
avec les modules reels ; ceci ne qualifie pas le lancement ARM ni P3.

**Hors L06-D1** : lecture par le pont C11 du Launcher, dessin d'une liste sur
PMKB-UI, actions d'installation/desinstallation, demarrage d'application,
telechargement, service permanent et essai Kobo. L06-D2 peut verifier un
consommateur natif sans modifier Notes ADR-005 ni les huit visuels manga.
