# PMKB L07-D7m — bilan du contrat de presentation Store

## Perimetre
Le Store reste un apercu passif, avec son propre framebuffer, un backend injecte de type `PMKBBackend`, et aucune route applicative Store activable. Les tests utilisent le vrai pont Launcher / PMKB-UI natif mais des doubles Notes/Calculatrice et des callbacks de presentation sur hote.

## Verifications acquises
- D7a : zones dirty de page et acquittement sur surface de test ;
- D7b : presentation backend simule, erreur, reprise, pas de modification ;
- D7c : second rectangle refuse, dirty global conserve, retransmission prudente ;
- D7d : mutation reentrante *synchrone* du framebuffer ;
- D7e : backend absent / callback manquant ;
- D7f : contrat public `pmkb_store_router_present` et controles d'identite et separation ;
- D7g : changement d'identite du Launcher avant presentation, refus et liberation ;
- D7h : Store ferme, refus de presentation, reouverture explicite ;
- D7i : changement de dimensions et validite du nouveau framebuffer ;
- D7j : erreur apres redimensionnement et nouvel essai ;
- D7k : echec puis fermeture sans presentation residuelle ;
- D7l : trois erreurs successives avant reussite ;
- D7m : scenario integre erreur -> reprise -> aucune modification -> fermeture -> reouverture -> presentation -> shutdown.

Les CI des jalons D7a a D7l ont ete observees SUCCESS sur leurs commits de test. D7m doit encore etre valide par CI sur son commit `5bc1db263b86dfaf5d74a98890e550af842bfb95`.

## Non prouve
Aucun test sur le vrai controleur EPDC i.MX50, ni validation des ioctl MXCFB, marqueurs de rafraichissement, niveaux de gris, modes partiels/complets, ghosting, latence, consommation, batterie, tactile ou RAM residentielle cible. Aucun test de concurrence preemptive ou reentrance de fermeture pendant callback : cela demande un contrat specifique.

## Garde-fous
Aucune modification de la microSD de la Kobo, FIRST BOOT, P1/P2/P3 ou recoveryfs. Pas de fusion des PR #30 et #31, ni de Store executable. La phase suivante doit privilegier les limites du contrat d'appel et un adaptateur E-Ink simulable avant essai materiel.
