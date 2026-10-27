# PMKB — revue visuelle hôte des interfaces natives V0

## Objet

Rendre consultables dans GitHub Actions les douze captures PNG déjà
calculées par le raster C11 natif : Notes, Calculatrice, Store (liste
et détail), Tableau blanc, et planche de glyphes, chacune en
320 x 480 et 1080 x 1440.

Le workflow Native PMKB UI réexécute make preview dans le répertoire
temporaire de GitHub Actions. Il vérifie la présence de 12 PNG, calcule
leurs sommes SHA-256, puis publie ces captures dans un artefact
conservé 30 jours. Les tests C11 et les sanitizers restent obligatoires.

## Recette de validation

Depuis l'onglet Actions ou la PR :
- ouvrir l'exécution Native PMKB UI ;
- récupérer l'artefact pmkb-host-native-previews ;
- contrôler les titres, glyphes, contraste et espace de saisie Notes ;
- examiner les deux lignes d'en-tête (ADR-005) et les touches tactiles ;
- comparer la zone de calcul et la grille scientifique aux deux tailles ;
- vérifier la signalétique du Store et les tracés du Tableau blanc ;
- signaler sur la PR la scène et le défaut avant toute acceptation.

Les captures ne remplacent **jamais** une validation visuelle explicite.
Elles n'établissent pas non plus la conformité des PR navigateur
#25/#26/#27 ; leur code HTML/JS diffère du raster natif C11.

## Limites

Rendu logiciel hôte uniquement : aucun test e-ink, EPDC, ZForce,
latence, consommation, autonomie ou compatibilité ARM sur Aura HD.
Aucune image Kobo, fichier privé, firmware, modification P1/P2/P3,
montage ou accès au périphérique physique. L'artefact GitHub est un
produit éphémère de CI et non une ressource sur la liseuse.
