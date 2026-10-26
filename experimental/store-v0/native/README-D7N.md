# PMKB L07-D7n — interface de transport E-Ink simulee

`pmkb_store_eink_sim.h` fournit un adaptateur sans pilote materiel. Il transforme une soumission synchrone de rectangle de gris en `PMKBBackend`, verifie les bornes et distingue deux compteurs : soumissions effectuees et acquittements positifs. Un retour different de `PMKB_OK` n'est pas comptabilise comme acquitte ; le moteur `pmkb_surface_present` conserve alors le dirty.

Le test de routeur Store introduit un transport qui refuse une soumission puis accepte la reprise. Il verifie le maintien de dirty, les compteurs et l'absence de nouvelle soumission en `PMKB_NO_CHANGE`.

La correspondance avec les futurs marqueurs MXCFB/EPDC, les mises a jour asynchrones et la politique de waveforms ne sont **pas** implementees ni qualifiees. Aucun device, ioctl, P1/P2, FIRST BOOT, installation ou activation Store. PR #30 et #31 non fusionnees.

Code et tests : `23522265472eb1cdcd8612d3e32289070dc4a5f1`, `6bd3d10cfb21d801e275d5995abf1cf01c503f72`. Resultats CI a verifier sur le second commit.
