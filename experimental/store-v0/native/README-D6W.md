# PMKB L06-D6w — prevalidation du proprietaire de surface

`PMKBStoreSurfaceOwner` detache et libere l'ancienne surface, puis verifie l'etat du `PMKBAppHost` **avant** l'appel a `pmkb_surface_init`. Un hote inactif avec instance non nulle, un hote actif sans instance, ou un identifiant non gere (dont Store) sont immediatement refuses. Cette validation economise l'allocation des pixels pour les etats manifestement incoherents, sans contourner le garde complet au moment de l'attachement.

Le banc C11 etend les cas de refus apres fermeture : hote NONE/instance non nulle puis STORE/instance nulle, avec etat du proprietaire toujours vide et garde detache. Il ne mesure pas le nombre exact des `malloc` ni le RSS. L'absence de fuite materielle n'est pas etablie par ces tests.

Code `f312738fef52ce49fca76b9e7d44938d17f2570b` ; test `e9e39cf3c0cff94e48455a6c423925a053a2f6fe`. Qualification CI au SHA du test a confirmer. Store `runnable=false`, PR #30/#31 non fusionnees, pas d'ARM/Kobo/EPDC ni d'ecriture FIRST BOOT/P2.
