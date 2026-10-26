# PMKB L07-D7a — rectangles sales du Store sur hote

Apres la navigation passive page 0 -> page 1 d'un catalogue synthetique de 64 entrees, le banc C11 inspecte `pmkb_surface_take_dirty` sur le framebuffer Store reellement possede par le routeur. Le rectangle doit etre non vide, borne a la surface et consomme une seule fois. La navigation reste sans partage de framebuffer Notes/Calculatrice.

Ce test porte sur la comptabilite logicielle des zones modifiees. Il ne simule ni l'ordonnancement MXCFB, ni le marqueur EPDC, ni les effets visuels de l'E-Ink. Le test ne mesure pas encore la surface sale totale ou la reduction d'energie.

Code de test : `eefa996c077dc88769480e9f5c7aa51a88908c4f`. Attendre la CI correspondante avant de le qualifier. Store non executable, PR #30/#31 non fusionnees, FIRST BOOT/P2 et Kobo inchanges.
