# PMKB L06-D6b — contrat de présentation et zones sales

Qualification sur les **vrais fichiers** de la PR #30 : `pmkb_ui.h`,
`pmkb_surface.c` et `pmkb_backend.c`, épinglés au commit
`e2907a19920100ef2a32ec6587e724ccb5116bc7` et vérifiés
individuellement par leur empreinte Git. Le banc ne télécharge pas de
firmware, de dépôt complet ni de dépendance ; il ne travaille qu'en CI.

Le nouveau `native/test_store_present_contract.c` relie la passerelle
Store D6a au moteur réel de dessin **et au contrat réel**
`pmkb_surface_present()` via un backend synthétique en mémoire. Les
contrôles couvrent :

- pixels non blancs couverts par les rectangles effectivement transmis ;
- nombre de zones 1 ou 2 selon le coût du rectangle englobant ;
- deux modifications très éloignées produisant deux callbacks ;
- acquittement après réussite, avec remise à zéro de `has_dirty`,
  `changed_pixels` et du compteur des îlots ;
- cache-hit sans nouveau callback de présentation ;
- erreur du backend et refus de backend invalide **sans effacer** les
  rectangles sales, puis succès à la reprise ;
- modification réentrante du buffer pendant une présentation : les
  zones doivent rester sales jusqu'à la prochaine présentation stable ;
- notification explicite d'un dessin étranger puis restauration du Store.

Cette qualification ne mesure **ni** le temps de rafraîchissement EPDC,
**ni** la consommation, le ghosting ou les 16 niveaux de gris réels.
Le test ne doit déclencher aucune action du Launcher, aucun réseau sur la
Kobo et aucune écriture physique.

Le Store reste `runnable=false` dans la PR #30 ; aucun composant Store
n'est transféré dans cette PR, et les PR #30/#31 ne sont pas fusionnées.
Une CI verte qualifie uniquement le contrat de présentation sur hôte,
pas le comportement matériel.

**Suite : L06-D6c** — vérifier les résultats CI et, en cas de succès,
consolider les conditions nécessaires avant tout branchement effectif
au Launcher ; en cas d'échec, corriger d'abord le défaut démontré.
