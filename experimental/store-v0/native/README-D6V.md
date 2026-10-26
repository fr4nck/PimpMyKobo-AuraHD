# PMKB L06-D6v — apercu Store invalide fail-closed

Une demande de previsualisation sans catalogue (`catalogue == NULL`) ne doit pas conserver la surface du dernier apercu : le routeur detache le garde, libere le framebuffer Store et retourne `PMKB_STORE_PAINT_INVALID`. L'hote Notes/Calculatrice n'est pas ferme.

Le banc C11 ajoute le parcours apercu valide -> catalogue absent -> compteur pixels nul, pointeur gris nul et garde detache -> nouvel apercu valide. Ce comportement evite la conservation de pixels et de references obsoletes apres une erreur de requete.

Production `4e2ea8685edf7a5f30a3de16b33e7d4165b6d24a`, test `363d28dbe669812ec33672c96c3b40036ca7b290`. CI au SHA test a verifier avant declaration PASS. Store demeure non executable, PR #30/#31 non fusionnees, aucun acces a FIRST BOOT/P2 ou au materiel Kobo.
