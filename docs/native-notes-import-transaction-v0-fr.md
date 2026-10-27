# PMKB L09-B — Réimport transactionnel des Notes en C11

## Objectif

Après L09-A (checkpoint temporaire sur ordinateur hôte), pouvoir
réinjecter dans le modèle natif la copie pmkb-notes-v1, sans effet
sur une microSD ou une partition P3.

API :

- pmkb_notebook_import_native_json(book, json, length)
- pmkb_app_host_notes_import_snapshot(host, generation, json, length,
  replace_existing)

Le parseur décode et valide complètement les octets dans un carnet
provisoire. Aucun ancien pointeur du carnet n'est libéré avant
l'acceptation intégrale. Sur erreur de format, de limites, d'Unicode
ou d'allocation, toutes les notes existantes restent en mémoire.

## Format actuellement pris en charge

Il s'agit du format JSON **canonique du C11**, dans l'ordre
exact des clés émises par pmkb_notebook_export_json :

- carnet de 100 notes maximum, 3 000 000 octets maximum ;
- ID pmkb_000001 à pmkb_999999, sans doublons ; prochaine création
  après le numéro maximal pour ne pas réutiliser d'identifiant ;
- titres significatifs, limites en unités UTF-16 de 100 / 120 000 ;
- échappements textuels émis par le sérialiseur C11 et UTF-8 valide ;
- strokes vide et typographie mono/17/1.6 ;
- timestamps UTC reconnus par le moteur natif.

Un export différent du prototype navigateur (croquis, polices,
autres clés ou ordre de champs différent) est refusé au lieu de
perdre silencieusement des données. Ce n'est PAS un parseur JSON
général ni une migration du carnet enrichi.

## Pont Launcher et UX

L'import exige Notes actif, le jeton exact et non saturé de la
session, et replace_existing=true si le carnet courant contient
des notes. Le jeton est inchangé si l'import échoue ; sur succès,
il avance pour invalider les opérations issues de l'ancien carnet.
Le Launcher ferme le clavier, remet la liste des notes et repeint
la simulation native seulement après import réussi.

Le carnet importé reste volatil. Le statut PMKB_UNSAVED protège
toujours contre la fermeture sans consentement explicite ; aucun
bouton ne peut annoncer une persistance P3 à partir de cet import.

## Qualifications et limites

Les tests C11 couvrent un carnet à deux notes, les accents,
les sauts de ligne, la compatibilité export → import → export,
les refus d'entrées tronquées et le maintien des anciennes notes,
la continuité des IDs, le carnet vide et les jetons obsolètes.
La CI native effectue compilation stricte et ASan/UBSan.

L09-B reste **hôte et RAM uniquement**. Il ne fournit pas de pilote
FAT32, stockage P3, montage, journal de récupération au boot,
validation de la microSD, accès ZForce ni rafraîchissement EPDC.
L'activation matérielle exige une qualification et une autorisation
distinctes ; P2/recoveryfs reste inchangée.
