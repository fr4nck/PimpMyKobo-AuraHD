# PMKB L07-D7d — mutation reentrante durant la presentation

Le test du routeur Store utilise le vrai `pmkb_surface_present` et un backend hote simule qui modifie synchroniquement le framebuffer au premier callback. Cette mutation doit laisser un rectangle dirty en attente au lieu de l'acquitter accidentellement. Un deuxieme appel, sans nouvelle modification, doit consommer l'etat dirty.

Le callback de test applique une seule modification de couleur (gris 123) pour qu'elle soit observable, meme si la surface initiale contient du noir. Il n'y a ni thread ni concurrence preemptive dans cet essai : le contrat est strictement la reentrance synchrone.

Tests au commit `454d5f94d4821b258dd6a8774b416051eae8ebe7`. CI a verifier avant qualification PASS. Pas de pilote MXCFB, d'ecran reel ou d'ecriture physique ; Store demeure non executable, PR #30/#31 distinctes.
