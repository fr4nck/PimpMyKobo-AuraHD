# PMKB L07-D7c — echec du second rectangle de presentation

Le banc C11 du routeur Store cree deux ilots de pixels tres eloignes, puis utilise le vrai `pmkb_surface_present` avec un backend simule qui accepte le premier rectangle et refuse le second. La zone dirty doit rester en attente, sans acquittement global. Une nouvelle presentation reussie doit retransmettre les deux regions et consommer l'etat dirty ; l'appel suivant doit retourner `PMKB_NO_CHANGE`.

L'essai est volontairement conservateur : apres l'erreur de la deuxieme region, le premier rectangle est egalement retransmis, car le logiciel ne dispose pas de preuve d'acquittement global. Aucun acces MXCFB, EPDC, materiel ou stockage. Pas de partage de buffers Notes/Store.

Commit de test : `fc7c296f8bf799eb24b5a23f0329a416a6e08e96`. A qualifier par CI sur le SHA exact. Store non executable, PR #30/#31 non fusionnees, FIRST BOOT/P2 inchanges.
