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
ciblés : aucun lien symbolique n'est suivi. La fonction validate_snapshot reçoit le document déjà chargé en mémoire.
Pour partir du texte JSON, utiliser validate_snapshot_json(text) : elle décode
une chaîne déjà fournie sans ouvrir de fichier.

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

## Lecture JSON stricte et fixtures versionnées

L'audit du lot initial n'a pas trouvé de divergence avec les contrôles documentés
sur le dictionnaire en mémoire. Il a démontré une perte d'information en amont :
json.loads ordinaire retient la dernière valeur d'une clé répétée. Un texte avec
schema_version=0 puis schema_version=1, ou un dev invalide puis valide dans le
même record, peut ainsi devenir un dictionnaire accepté par validate_snapshot.

La nouvelle entrée pure validate_snapshot_json(text) refuse les clés JSON
dupliquées à tous les niveaux (duplicate_json_key), NaN/Infinity, la syntaxe
invalide et les textes de plus de 131072 caractères. Elle ne lit aucun chemin.
La limite porte sur des caractères de la chaîne Python, pas sur des octets ou
sur une taille de fichier. Une profondeur faisant échouer le décodeur est
rapportée comme invalid_json ; ce n'est pas une politique de collecte live.

validate_snapshot reste disponible pour les dictionnaires déjà chargés. Elle ne
peut pas reconstituer les clés effacées par un décodeur précédent : ne pas lui
attribuer cette garantie. Utiliser l'entrée JSON stricte pour les fixtures texte.

Les douze fixtures sont dans tests/fixtures/sysfs-v1 ; cases.json donne leurs
résultats attendus, indépendamment du contrôle. Les tests lisent uniquement ces
fichiers ordinaires versionnés et utilisent le décodeur strict. Les cas de
doublons JSON sont intentionnels et ne doivent pas être « nettoyés » par un
formateur qui garderait seulement la dernière valeur.

framebuffer-present-unverified.json reprend volontairement les mêmes attributs
que minimal.json : aucun champ du snapshot ne prouve hw_ready. Son résultat
coherent doit conserver hardware_verified=false, boot_qualified=false et la
disponibilité de l'écran dans unverified.

Les fixtures sont des exemples construits, jamais des relevés de l'Aura HD.
Les nombres et les noms plausibles ne prouvent ni un binding driver ni la
complétude du snapshot. La correspondance numéro input/driver reste hors v1 ;
l'ajouter exigerait une preuve source et une évolution documentée du contrat.

La [spécification du futur démarrage](offline-startup-spec-fr.md) distingue ces
contrôles de données des préconditions matérielles encore non qualifiées.
