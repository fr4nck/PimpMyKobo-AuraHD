# PMKB D7i — presentation apres redimensionnement

Le banc C11 ouvre le Store en 320x480 puis en 1080x1440 avant d'appeler la presentation du routeur sur son framebuffer nouvellement alloue. Le callback simule exige les nouvelles dimensions et un rectangle dirty borne ; apres acquittement le dirty disparait. Une fermeture explicite interdit toute nouvelle presentation.

Commit du test : `7360e9a1a80067b919ab9c6db92985be8420e23b`. CI a verifier avant qualification du lot. Ce test ne mesure pas l'e-ink physique ni les buffers du pilote. Aucune fusion PR #30/#31, Store non executable, FIRST BOOT/P2 inchanges.
