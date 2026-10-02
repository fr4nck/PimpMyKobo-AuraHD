# Vérifier une sauvegarde existante

**Français** | [English](verify-backup-aura-hd-en.md)

`tools/verify-backup-aura-hd.py` contrôle **hors ligne** un dossier produit par [`backup-aura-hd.py`](backup-aura-hd-fr.md). Aucune Kobo n'a besoin d'être connectée.

L'outil est **strictement en lecture seule** : chaque fichier du dossier est ouvert en `rb`, et rien n'est créé, renommé ou modifié, pas même les `.part` ou `.FAILED` laissés par une copie interrompue.

> **Portée.** Un verdict « valide » prouve que les fichiers sont **cohérents avec leur manifeste**. Il ne prouve ni leur **authenticité** (un manifeste et des fichiers peuvent avoir été remplacés ensemble), ni leur **aptitude à être restaurés** sur une carte donnée. La sauvegarde ne couvre par ailleurs que les composants sélectionnés, pas l'intégralité de la carte.

## Utilisation

```bash
python3 ./tools/verify-backup-aura-hd.py ~/Aura-backup
```

```powershell
python .\tools\verify-backup-aura-hd.py D:\Aura-backup
```

Options :

- `--json` : seul le rapport JSON est écrit sur la sortie standard. Les caractères non ASCII y sont échappés, ce qui le rend lisible sur toute console Windows ;
- `--lang en` : sortie humaine en anglais.

## Les quatre verdicts

| Verdict | `status` | Code | Signification |
|---|---|---|---|
| **SAUVEGARDE VALIDE** | `valid` | `0` | tous les composants demandés sont relus et concordent avec le manifeste, `SHA256SUMS` et l'empreinte cible |
| **SAUVEGARDE INCOMPLÈTE, INTERROMPUE OU DÉCLARÉE ÉCHOUÉE** | `incomplete` | `1` | aucune incohérence trouvée, mais la sauvegarde n'est pas terminée : manifeste `interrupted`, `in_progress` ou `failed`, composant non vérifié, `complete: false` |
| **SAUVEGARDE INCOHÉRENTE OU CORROMPUE** | `inconsistent` | `2` | au moins une contradiction démontrée : fichier absent, tronqué ou modifié, empreintes contradictoires, `SHA256SUMS` divergent, empreinte cible ou géométrie qui ne concorde pas, chemin dangereux, `complete: true` démenti |
| **MANIFESTE INVALIDE** | `invalid` | `3` | dossier inaccessible, manifeste absent, illisible, au JSON invalide, au schéma non pris en charge ou à la structure incomplète |

Si une incohérence est trouvée, le verdict est `inconsistent`, même si la sauvegarde était par ailleurs incomplète.

Une sauvegarde **déclarée échouée** par l'outil de sauvegarde (par exemple une relecture de destination divergente, conservée en `.FAILED`) est classée `incomplete` : le défaut est déjà enregistré dans le manifeste, et le vérificateur confirme seulement que le reste est cohérent. Il faut refaire la sauvegarde.

## Ce qui est contrôlé

**Manifeste**

- `schema_version` pris en charge (actuellement `1`, un entier) et `tool` égal à `backup-aura-hd` ;
- présence et types des champs ;
- jeu exact des quatre composants.

**`complete: true` n'est jamais cru sur parole.** Il doit être confirmé par :

- `status: complete` ;
- chaque composant demandé relu et valide ;
- `identity_recheck.matches` ;
- l'absence d'erreurs enregistrées.

**Composants**

- Pré-P1, P1 et P2 sont toujours demandés. P3 ne l'est que si `options.include_userdata` vaut `true` : son absence est alors normale.
- Pour un composant enregistré comme `verified` :
  - le fichier porte son nom canonique et est un fichier régulier, pas un lien ;
  - sa taille réelle est égale à `size`, `bytes_written` et `destination_size` ;
  - le SHA-256 recalculé est égal à `sha256`, `sha256_destination` et `sha256_stream`.
- `sha256_source_reread` doit être présent et égal si la sauvegarde a relu la source. Il doit être **absent** pour une sauvegarde `--single-pass`.
- Pour `pre_p1`, l'empreinte doit aussi être égale à celle mesurée lors de l'identification (`expected_sha256`).
- Un `.part` ou un `.FAILED` n'est **jamais** un composant valide. Il est signalé comme reste d'une copie inachevée ou échouée.
- Un fichier final présent alors que le manifeste ne le marque pas `verified` n'est pas pris en compte.

**`SHA256SUMS`**

- Il doit lister exactement les composants vérifiés, avec les empreintes recalculées.
- Son absence est une incohérence pour une sauvegarde terminée (`complete` ou `failed`). Elle est normale pour une sauvegarde interrompue.

**Valeurs relues depuis les fichiers et valeurs seulement déclarées**

Valeurs **relues** depuis les fichiers :

- `pre-p1.bin` est réanalysé avec le parseur qualifié de l'inspecteur. On en tire :
  - le MBR : SHA-256 du secteur 0, type, LBA, taille et offset de P1 à P3 ;
  - le HWCONFIG : v1.7, 39 octets, PCB 28 et ses champs ;
  - l'**empreinte cible**, recalculée avec l'algorithme même de l'outil de sauvegarde.

  Chaque champ est comparé à sa valeur déclarée. La cohérence interne de `fingerprint_sha256` est également vérifiée.
- Les offsets et tailles des composants sont comparés à la géométrie relue.
- Les labels de système de fichiers sont relus dans les images valides : P1 `rootfs`, P2 `recoveryfs`, et P3 si elle est présente.

Valeurs **seulement déclarées**, signalées comme telles dans `declared_only` :

- chemin et taille de la source, horodatages, `identity_recheck` ;
- concordance avec la source réelle. La carte n'étant pas connectée, `sha256_stream` et `sha256_source_reread` ne peuvent être comparés qu'aux fichiers, pas à la carte.

**Chemins**

Le vérificateur refuse sans jamais les lire :

- les chemins absolus, les traversées `..` et les séparateurs de dossier ;
- les noms de lecteur Windows (`C:…`) ;
- les liens symboliques : composant, `SHA256SUMS` ou manifeste ;
- tout nom qui se résout hors du dossier de sauvegarde.

## Rapport JSON

Principaux champs :

- `schema_version` (format du rapport : `1`), `status`, `ok` ;
- `invalid_reasons[]`, `inconsistencies[]`, `incomplete_checks[]`, `warnings[]` ;
- `components[]` : `result`, `declared_status`, `actual_size`, `sha256_recomputed` ;
- `sha256sums`, `fingerprint` (`declared`, `recomputed`, `fields`, `matches`), `labels_reread` ;
- `leftovers` (`.part`, `.FAILED`), `declared_only`, `scope`.

## Décisions retenues

1. L'empreinte cible est un **indice de concordance**, jamais le seul critère autorisant une restauration.
2. L'unicité de la zone pré-P1 entre deux Aura HD **reste inconnue**.
3. La sauvegarde stricte reste le comportement par défaut. Un futur mode de secours pour une P1 corrompue sera un chantier distinct, non implémenté.
4. La sauvegarde couvre les composants sélectionnés, **pas l'intégralité de la carte**.
