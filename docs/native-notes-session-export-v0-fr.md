# PMKB Native — remise JSON de Mes Notes au Launcher (V0)

## Objet

Le noyau natif C11 de PMKB contient des Notes uniquement en RAM et
un pont Launcher à une application active. La fermeture d'un carnet
non vide sans consentement explicite de perte est déjà refusée avec
PMKB_UNSAVED. Le nouveau point d'entrée :

    pmkb_app_host_notes_export_snapshot(host, generation, &json, &length)

copie le carnet dans un buffer JSON au format pmkb-notes-v1. Le
consommateur doit libérer ce buffer par free(). Aucun fichier n'est
ouvert, créé, monté ou modifié. Aucun accès P1/P2/P3, Nickel, KOReader
ou périphérique Kobo.

## Contrat

L'appel ne fonctionne que lorsque Mes Notes est l'application active,
et lorsque generation correspond au jeton non nul de la session
host.generation, différent de UINT64_MAX. Cette garde évite qu'une
réponse tardive relise une autre session ouverte après fermeture.
Un retour d'erreur sur un mauvais jeton ne modifie ni le carnet, ni
les paramètres de sortie. Le moteur C11 existant valide titre, Unicode,
timestamps, limites et format avant de copier.

Selon ADR-005, un titre vide peut rester visible pendant la saisie ;
la sortie du champ remet "Sans titre N". Un export direct avec un
titre vide non normalisé est refusé et ne corrige pas silencieusement
la saisie à la place de l'utilisateur.

## Sauvegarde non implémentée — interdiction de fausse confirmation

Le JSON n'est qu'une **copie en RAM**, pas une écriture durable. Même
après un export réussi, pmkb_app_host_close(host,false) conserve
PMKB_UNSAVED dès qu'il existe une note. L'interface ne doit pas
afficher "Enregistré" et aucun nouvel appel ne déclare la session
persistée.

Une étape distincte devra choisir un emplacement d'écriture P3
autorisé, apporter un protocole de commit atomique, puis confirmer
l'intégrité des données restaurables. Aucun emplacement P1/P2 ou
modification de récupération ne doit être ajouté.

## Qualifications et portes restantes

La CI C11 vérifie un carnet vide, un titre vide et son comportement
au changement de focus, les accents français du JSON, l'interdiction
de clôture sans discard, la péremption du jeton après nouveau lancement,
et le refus d'export depuis la calculatrice ou un hôte nul.

Le prototype navigateur Notes des PR #26/#27/#29 reste indépendant.
Les PR #25/#26/#27 exigent une **acceptation visuelle explicite** ;
leurs anciens tests CI ne prouvent pas le rendu actuel à 320–375 px,
au zoom 200 %, ni la compatibilité tactile Aura HD.

Le backend matériel, l'écriture P3, le clavier ZForce, les glyphes,
les markers EPDC, la présence des bibliothèques ARM et la carte
microSD physique restent NON QUALIFIÉS.
