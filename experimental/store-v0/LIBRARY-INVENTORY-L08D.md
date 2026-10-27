# PMKB — L08-D : confrontation des SONAME à un inventaire synthétique

## Portée exacte

L08-C (PR #35, intégrée à `main`) extrait `DT_NEEDED` d'un ELF32 ARM EABI5 **sans charger le programme**. L08-D ajoute `arm_library_inventory.py`, qui confronte ces noms à un jeu de métadonnées fourni en mémoire. Aucun répertoire, bibliothèque ou périphérique n'est inspecté, y compris sur l'hôte. Le traitement ne lance, ne télécharge et n'installe rien.

Le format d'entrée JSON UTF-8 (maximum 16 Kio, 128 SONAME) est intentionnellement limité aux exemples :

```json
{
  "schema": "pmkb-elf-libraries-v1",
  "scope": "synthetic_fixture",
  "coverage": "partial",
  "libraries": ["libc.so.6"]
}
```

Seules `partial` et `complete` sont des valeurs de couverture valides. `complete` veut **uniquement** dire que la liste est complète au sens de la fixture synthétique ; cela n'atteste rien sur la Kobo. Toute déclaration de portée `kobo_verified` ou toute structure inconnue est refusée. Les doublons JSON, SONAME ambigus et chemins sont refusés. Les listes et tailles sont bornées.

## Sémantique de la comparaison

- `matched_in_fixture` : même SONAME cité par l'ELF et par la fixture ; ne prouve pas la présence d'une bibliothèque sur l'appareil ;
- `not_observed` : SONAME absent d'un inventaire **partiel** (inconnu, pas nécessairement manquant) ;
- `not_in_fixture` : SONAME absent d'un inventaire déclaré complet **uniquement au sein de la fixture** ;
- `launchable: false` : invariant de toutes les sorties, même quand tous les noms coïncident.

Le rapprochement ne couvre pas l'ABI de la libc, les versions de symboles, le loader dynamique, les chemins réels, la provenance des binaires, les instructions ARM effectivement utilisées ni les modules/noyau historiques. Les noms seuls ne permettent pas de déterminer qu'un programme fonctionne.

## Qualification et suite

La suite `tests/test_store_arm_library_inventory.py` utilise de vrais parseurs L08-B/C avec un ELF synthétique, puis exerce les comparaisons partielles/complètes et les entrées malformées. La qualification CI de la PR du lot est obligatoire avant toute conclusion PASS.

**L08-E séparé** : constituer un inventaire *en lecture seule et avec provenance* à partir d'un snapshot légalement disponible du rootfs Kobo, puis qualifier chaque bibliothèque (chemin, hachage et ABI) et le chargeur. Aucune preuve de présence réelle n'est fournie par L08-D. Ne pas toucher à FIRST BOOT, P1/P2/P3, microSD, ni démarrer de téléchargement ou de toolchain.
