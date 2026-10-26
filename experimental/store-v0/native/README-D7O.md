# PMKB D7o — contrat de marqueur asynchrone simule

Modele hote C11 `pmkb_store_eink_pending.h` : un seul marqueur en attente, identifiants croissants, refus d'une seconde soumission en attente, refus d'une confirmation d'identifiant inconnu et distinction entre echec et completion positive. Les tests couvrent la reprise apres echec, une confirmation dupliquee et le fait qu'une acceptation n'est pas une completion.

**Limite fondamentale :** ce module est un modele d'etats autonome, PAS encore raccorde a `pmkb_surface_present`. Celui-ci acquitte toujours le dirty apres retour `PMKB_OK` de son callback synchrone. Il serait incorrect de brancher directement le retour d'acceptation asynchrone dans cette interface, car les pixels seraient consideres presentes avant la confirmation EPDC. Le prochain jalon doit prevoir une vraie separation submit/complete et le traitement des modifications concurrentes.

Aucun ioctl, marqueur MXCFB reel, thread, fichier materiel, activation Store ou ecriture FIRST BOOT/P2. PR #30/#31 non fusionnees. Commit test `9634a2c8dac0f8f4c0294074006d0f2c8c5ac6cf`, CI a verifier avant PASS.
