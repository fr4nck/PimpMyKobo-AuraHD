# PMKB D6p — echec d'attachement apres allocation

Un test negatif sur le proprietaire `PMKBStoreSurfaceOwner` introduit un hote incoherent (application NONE avec instance non nulle). `owner_open` alloue un framebuffer synthetique 320 x 480, puis `guard_enter` refuse l'hote. Le test exige la liberation de la surface, le detachement du garde et un cout de pixels nul. Une ouverture correcte ulterieure doit reussir.

Commit : `cb22f13f4754418d7cbec5c18fb088f32b2a5f70`. CI a verifier au SHA exact avant declaration PASS. Aucun changement au code de production, ni route Store executable, ni operation sur la Kobo ou ses partitions. PR #30/#31 restent non fusionnees.
