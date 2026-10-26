# PMKB L07-D7x — annulation après mutation du framebuffer

Le test natif C11 lance une soumission asynchrone du Store, modifie les pixels alors que le marqueur est en attente, puis annule explicitement cette soumission. Il vérifie que les pixels restent `dirty`, qu'une confirmation tardive du marqueur annulé est refusée et qu'une nouvelle soumission reçoit un marqueur distinct. Seule la confirmation de ce nouveau marqueur peut acquitter les zones modifiées.

Cette qualification est limitée au modèle séquentiel sur hôte : aucun DMA, EPDC, MXCFB, thread, pilote réel ou mesure de latence. Le Store demeure non exécutable et les PR #30/#31 ne sont pas fusionnées. FIRST BOOT et P2 restent intacts.

Commit du test : `44bfd3906d93a12b946eee76127efea6befd2a73`. CI à vérifier avant déclaration PASS.
