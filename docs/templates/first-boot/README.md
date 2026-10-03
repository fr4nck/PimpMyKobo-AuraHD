# Dossier de preuves FIRST BOOT

**Français** | [English](README.en.md)

Modèles texte vierges uniquement. Aucun essai matériel, accès microSD ni modification
de P2. Le [protocole de qualification](../../first-boot-qualification-fr.md) à
`ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf` définit attendus, procédures et STOP
pour les 25 IDs ; ils ne sont pas dupliqués ici.

## Préparer le dossier privé

Copier le [compte rendu](trial-report-fr.md), le [rapport d'incident](incident-report-fr.md)
si nécessaire et l'[index de preuves](evidence-index.tsv) dans un dossier **hors
du dépôt**, sur le PC. Garder le lien/commit du protocole lors de la copie ;
les liens relatifs fonctionnent dans Git, utiliser le
[protocole en ligne figé](https://github.com/fr4nck/PimpMyKobo-AuraHD/blob/ff4e8c1a97d77fe02fe5b1d487c2299633d44fcf/docs/first-boot-qualification-fr.md)
dans les copies privées. Jamais P2/P3 comme emplacement de preuves.

ID essai : UTC `AAAAMMJJTHHMMSSZ-fbNN`, NN étant le numéro local de tentative.
Un dossier/compte rendu par POWER ; relier les incidents correspondants.
Contenu privé proposé (créer seulement ce qui est utile) :

- `trial-report.md`, `incident-01.md`, `evidence-index.tsv`
- `photos/`, `videos/`, `logs/`, `hashes/`, `preflight/`
- `serial/` uniquement si un canal de capture est qualifié ultérieurement.

Noms : `<id-essai>_<id-test-ou-BOOT>_<séquence>_<description-neutre>.<ext>`.
Exemple de **nom seulement** : `20261004T090000Z-fb01_B03_001_screen.png`.
Noms ASCII, sans espaces, noms personnels, numéros de série ou titres de livres.
Conserver les captures originales intactes ; dérivés retouchés/anonymisés avec
nom distinct et référence au parent. L'extension correspond au format réel.

## Convention des preuves

| Type | Format / informations |
| --- | --- |
| Photos | JPEG/PNG originaux ; date, orientation physique, éclairage/exposition ; pas de faux avant/après |
| Vidéos | Format original disponible (ex. MP4) ; référence temporelle/précision, repère POWER, coupes déclarées |
| Logs | Octets/texte brut capturés ; source/outil/version/encodage, heure civile–uptime noyau, trous/resets ; conserver complet et extraits |
| Hashes | SHA-256 du fichier local/capture ; chemin, taille, date/méthode et périmètre mesuré |
| Preflight | Rapports image/contenu originaux, commande/version, hash image et lien avec arbre extrait ; sans FAIL ne vaut pas PASS matériel |
| Série | Seulement si disponible/qualifiée plus tard ; outil/réglages/canal et temps, brut conservé ; aucun brochage/niveau supposé |

Index TSV : une ligne par fichier, ID, chemin relatif, type, IDs de tests, date
capture, T+ (vide si inconnu), taille, SHA-256, source/outil, notes/parent.
Séparer plusieurs IDs de tests par virgules. Hash/taille/temps inconnus restent
vides avec raison dans les notes ; ne rien inventer. UTF-8, tabulations, une ligne
physique par entrée ; espaces plutôt que tabulations/retours dans les champs.
Chaque test référence un ID de l'index ou un chemin relatif. Déclarer les preuves
indisponibles dans le compte rendu. Le hash prouve l'intégrité du fichier, pas
l'authenticité ni la réussite du boot.

## Préremplissage et saisie

Seuls IDs/libellés, dix prérequis, repères chronologiques, rappels de blocage et
**NOT TESTED** sont préremplis. Aucun script/collecteur : rien ne découvre l'image,
ne lit de périphérique, ne calcule de hash ni n'attribue PASS automatiquement.
On peut copier/référencer les rapports existants après contrôle de provenance.
Candidat/version/hashes réels, temps, observations, preuves/logs, verdicts, décisions
de blocage et **confirmation P2 sont renseignés manuellement**.
La confirmation P2 initiale est NON CONFIRMÉE, jamais déduite d'un formulaire vide.

## Confidentialité et transmission

Git ne contient que les modèles. Preuves réelles brutes conservées hors Git :
aucun dump carte/rootfs/recovery, binaire propriétaire/waveform, .kobo.zip,
device.xml, série, bibliothèque/base personnelle ou chemin privé.
Avant publication d'un rapport sélectionné, relire/anonymiser identifiants,
images et logs ; garder les originaux privés et signaler les dérivés expurgés.
Ne pas saisir un essai réel dans les modèles versionnés. Le repreneur reçoit
compte rendu, incident, index et preuves partageables ensemble.
Ce dossier n'autorise aucun boot, écriture ou restauration.
