# PMKB L06-D6t — transition refusee et Notes non sauvegardees

Le banc de test du routeur passif verifie une tentative de lancement Calculatrice alors que Notes est deja active et contient une note non sauvegardee. Le bridge natif de PR #30 retourne `PMKB_INVALID` : l'instance Notes et son contenu doivent rester intacts. La route passive detache et libere son buffer Store avant la tentative, donc le compteur logique des pixels Store doit revenir a zero.

Commit test : `437215a527fdbc0035991310b770bde962e42ccb`. Le vrai bridge Launcher est compile dans la matrice CI existante, mais Notes/Calculatrice restent des doubles metier. Aucun changement de production. Valider la CI au SHA du test avant de qualifier D6t.

Store `runnable=false`, PR #30/#31 distinctes et non fusionnees ; aucune ecriture FIRST BOOT, P2, microSD ou Kobo reelle.
