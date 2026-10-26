# PMKB L07-E — gestes longs et limites explicites

La longueur maximale d'un trait reste **96 points**. Lorsque le 97e point est proposé, `MOVE` ou `UP` répond `PMKB_WB_LIMIT`, ne modifie pas le journal ni les pixels, et conserve le trait actif. Aucun segment n'est supprimé silencieusement. Le producteur peut finaliser les 96 points en réémettant `UP` sur la dernière coordonnée enregistrée, puis créer un second trait démarrant à la même coordonnée pour poursuivre le tracé sans rupture visuelle. Ce découpage reste volontairement explicite : pas d'allocation ni de segmentation automatique inconnue de l'appelant.

Les nouveaux scénarios C11 vérifient 95 déplacements valides, le rejet de la 97e coordonnée par MOVE puis UP, le maintien du trait provisoire, sa confirmation à la limite, les pixels effectivement dessinés et la reprise par un deuxième trait. L07-D est également corrigé : un point blanc sur fond blanc n'établit aucun rectangle `dirty`.

Contrat encore non couvert : changement de pression/échantillonnage ZForce réel, continuité tactile physique, énergie et affichage EPDC. Store/Launcher et FIRST BOOT/P1/P2/P3/recoveryfs inchangés. Test C11 sur hôtes Linux/Windows seulement ; ne pas déclarer PASS avant exécution GitHub Actions réussie.
