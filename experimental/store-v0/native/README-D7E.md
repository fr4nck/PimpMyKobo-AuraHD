# PMKB L07-D7e — backend de presentation absent

Le banc natif C11 couvre deux erreurs avant tout callback de presentation Store : un backend NULL et un backend sans fonction `present`. Dans les deux cas, le vrai `pmkb_surface_present` doit renvoyer `PMKB_INVALID` et conserver le rectangle dirty de la surface. Une reprise avec un backend simule valide doit ensuite presenter les pixels et acquitter ce rectangle.

Il s'agit d'une regression sur le contrat existant, sans modification du moteur PMKB-HAL, sans simulation de marqueur EPDC et sans mesure d'autonomie. Le test utilise le vrai pont Launcher et un double de backend, pas une Kobo.

Commit C11 : `78b222c62c5da2b0389ac6b8de4ca662af899a90`. CI a verifier au SHA exact avant toute declaration PASS. Store reserve/non executable, PR #30/#31 non fusionnees, FIRST BOOT/P2 inchanges.
