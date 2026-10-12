# Contrat de snapshot sysfs synthétique

Ce lot est séparé du prototype de démarrage. Il ajoute uniquement une fonction
Python pure : `validate_snapshot(snapshot)`, dans
`experimental/offline-audit/sysfs_snapshot.py`. Elle ne lit aucun fichier,
n'ouvre aucun périphérique et ne lance aucune commande. Aucun collecteur,
CLI, création de nœuds ou intégration au boot n'est fourni.

## Format minimal v1

Un snapshot est un document JSON ordinaire contenant les textes de fichiers
sysfs **synthétiques**. Les chemins sont des identifiants relatifs, jamais des
chemins à ouvrir. Les liens sysfs sont représentés par les textes des attributs
ciblés : aucun lien symbolique n'est suivi. Le consommateur lui fournit le
document déjà chargé en mémoire.

```json
{
  "schema_version": 1,
  "provenance": "synthetic",
  "files": [
    {"path": "class/graphics/fb0/dev", "text": "29:0\n"},
    {"path": "class/graphics/fb0/bits_per_pixel", "text": "16\n"},
    {"path": "class/graphics/fb0/rotate", "text": "0\n"},
    {"path": "class/input/event5/device/name", "text": "zForce-ir-touch\n"},
    {"path": "class/input/event5/dev", "text": "13:69\n"},
    {"path": "class/misc/ntx_io/dev", "text": "10:190\n"}
  ]
}
```

`files` est une liste pour que les chemins dupliqués restent détectables.
Chaque record a exactement `path` et `text`. Les seules clés racine admises
sont schema_version, provenance et files. La provenance est obligatoirement
synthetic : un document réel ou prétendument qualifié ne peut pas entrer dans
ce contrat v1.

Limites : 256 records, chemins de 128 caractères maximum, textes ASCII de
256 caractères maximum sur une ligne, éventuellement terminée par LF.
Les indices fbN/eventN sont décimaux canoniques, sans zéros initiaux, au plus
quatre chiffres. Ce sont des limites du contrat, pas une découverte des
limites physiques du matériel.

Les numéros sont des paires décimales major:minor, sans signe ni zéros initiaux :
major 1–4095, minor 0–1048575. Leur présence ne prouve aucun binding de pilote.
Les paires doivent être distinctes entre les entrées décrites.

## Identification et refus

| Élément | Données exigées | Ce qui est vérifié |
| --- | --- | --- |
| Framebuffer | class/graphics/fb0/dev, bits_per_pixel et rotate | Un seul framebuffer décrit, à fb0, paire 29:0, profondeur 8/16/32 et rotation 0–3 |
| Tactile | Pour chaque eventN décrit : dev et device/name | Exactement un parent nommé zForce-ir-touch ; son indice peut changer |
| Frontlight NTX | class/misc/ntx_io/dev | Paire 10:190 correspondant à l'interface NTX auditée |

Les autres entrées input peuvent être décrites si leur nom et leur numéro sont
complets ; elles ne sont pas identifiées comme boutons fonctionnels.
Les capacités evdev, la calibration et la correspondance entre le numéro input
et son driver ne sont pas qualifiées dans ce contrat minimal.

Refus : structure incorrecte, attribut inconnu, chemin absolu ou traversant,
texte invalide, attribut obligatoire absent, identité tactile absente/dupliquée,
plusieurs framebuffers décrits, modes hors du périmètre ou numéros incohérents.
Aucun périphérique de remplacement n'est inventé. En cas de refus,
identified est vide : les résultats partiels ne constituent pas une qualification.

## Résultat limité

Un succès signifie seulement :

- status = coherent ;
- snapshot_coherent = true ;
- hardware_verified = false ;
- boot_qualified = false ;
- physical_restore_eligible = false.

Le résultat liste toujours les preuves manquantes : complétude/authenticité du
snapshot, binding framebuffer et panneau prêt, capacités/coordonnées tactiles,
probe MCU et lumière effective, watchdog, alimentation, USB et réseau.
Même un document cohérent peut omettre un deuxième tactile réel : la complétude
est déclarée, jamais démontrée par cette fonction.

Aucun attribut ready n'est admis et aucun délai ou attente de fichiers réels
n'est introduit. Le numéro 29:0 identifie ici le slot framebuffer ; il ne prouve
pas que son pilote est EPDC. Une profondeur admise n'autorise aucune conversion
matérielle, et une rotation admise ne garantit pas l'orientation correcte.

Les interfaces proviennent des audits
[matériel](offline-hardware-qualification-fr.md) et
[conditions de boot](offline-boot-gates-fr.md), basés sur les sources Netronix.
La présence de fb0 précède potentiellement hw_ready. Le nom zForce-ir-touch
vient du pilote ZForce ; ntx_io est le misc device minor 190, major 10.
Ce contrôle ne modifie pas rcS, les réglages Nickel, la recovery ou une image.

## Validation

Tests proposés : indices event1/event5/event17, données manquantes ou partielles,
identités dupliquées/inconnues, framebuffer supplémentaire, numéros malformés,
collisions, faux attribut ready et garantie d'absence d'ouverture de fichiers
ou de lancement de helpers pendant la validation.

Après récupération du commit contenant le lot :

```sh
python -m unittest discover -s tests -p test_sysfs_snapshot.py -v
python -m unittest discover -s tests -v
git diff --check
```

Ces commandes ne sont pas une procédure d'essai matériel. Le premier essai
autorisé devra encore confirmer la géométrie et les rafraîchissements E-Ink,
les coordonnées et réponses tactiles, puis la gradation/extinction du frontlight.
Watchdog, veille, USB et absence de trafic ne sont pas certifiés ici.
