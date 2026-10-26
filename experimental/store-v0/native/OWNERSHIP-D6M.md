# PMKB L06-D6m — contrat de propriete des surfaces

## Etat audite

Le vrai `pmkb_launcher_bridge.c` de la PR #30 possede exactement une instance de Notes ou de Calculatrice. Le lancement alloue l'instance ; `pmkb_surface_init` alloue son buffer gris ; `pmkb_app_host_close` appelle le destructeur applicatif puis libere l'instance. Le `PMKBAppHost` est initialise par l'appelant, mais le bridge ne possede aucun framebuffer Store.

La PR #31 propose un garde `PMKBStoreLauncherGuard` qui emprunte `PMKBAppHost *` et `PMKBSurface *` ; il ne possede et ne libere ni l'un ni l'autre. Le garde refuse les surfaces Notes/Calculatrice alias, les plages chevauchantes et les transitions d'identite d'application. Il ne peut pas eviter un use-after-free si le routeur detruit ses emprunts sans detach.

## Responsable futur : routeur natif

- Allouer ou fournir la surface Store exclusivement au niveau du routeur, et rendre sa propriete explicite.
- Initialiser le garde avant premiere entree; ne jamais copier le garde avec ses pointeurs empruntes.
- Avant toute destruction, reinitialisation ou remplacement de la surface Store **ou de l'hote**, appeler `pmkb_store_launcher_guard_before_destroy`.
- Un changement de Notes/Calculatrice doit detacher le Store avant fermeture effective, y compris si la fermeture renvoie `PMKB_UNSAVED` ; la note ne doit pas etre abandonnee sans consentement.
- Garantir l'absence de chevauchement entre buffers. La comparaison actuelle utilise les intervalles de tailles `width * height`, mais seule une allocation reelle separee et vivante fonde la propriete memoire.
- Toute entree et tout dessin Store utilisent `pmkb_store_launcher_guard_enter/draw`, jamais les fonctions brutes de preview.
- La surface Store n'est pas un framebuffer resident obligatoire : le routeur peut la creer uniquement pendant la vue et la detruire a sa fermeture, sous reserve du contrat de detach.
- `PMKB_APP_STORE` reste `runnable=false` tant qu'une integration explicite n'est ni codee ni qualifiee. Aucun service, thread, processus ou reseau en arriere-plan.

## Criteres de recette future

1. Le routeur possede effectivement la surface; le garde n'est qu'un emprunteur.
2. Destruction/recreation de surface et passage Notes/Calculatrice sans ecriture croisee ni pointeur perime.
3. Refus de sortie Notes non sauvegardees preserve.
4. Profil memoire mesure, y compris la surface 1080x1440 de 1 555 200 octets en gris 8 bits et les allocations du vrai routeur.
5. Test ARM et Kobo physique sur environnement protege, seulement apres une autorisation materielle specifique.

## Limites

Ce fichier est de la documentation, pas du code de routeur ni une validation physique. CI D6l a verifier separement. PR #30 et #31 restent non fusionnees. FIRST BOOT, P2/recoveryfs et microSD ne sont pas touches.
