# PMKB Native — checkpoint Notes sur hôte, sans P3 (V0)

## But et périmètre vérifiable

Après la PR #51, le Launcher natif peut obtenir une copie du carnet en
RAM au format pmkb-notes-v1, avec jeton de génération de session.
Ce lot étudie **comment conserver et récupérer ces octets sur un
ordinateur hôte** sans prétendre écrire sur la partition P3.

Module autonome :
experimental/native-ui/tools/notes_checkpoint_host.py

Il ne propose AUCUNE commande CLI, AUCUN pilote physique et refuse
les chemins hors d'un sous-dossier déjà existant du répertoire
temporaire du système (tempfile.gettempdir()). En particulier,
l'application Kobo ne l'appelle pas. Les tests se limitent aux
dossiers TemporaryDirectory et n'ont accès à aucune microSD.

## Contrat de données

L'adaptateur impose la forme actuellement exportée par le C11 :
carnet pmkb-notes-v1 ; au plus 100 notes ; titres et textes UTF-8
avec limites en unités UTF-16 (100 et 120 000) ; identifiants uniques,
timestamps UTC valides, champs strokes=[] et typographie native
mono/17/1.6. JSON malformé, clés répétées, NUL ou surrogates isolés
sont refusés. Les croquis et polices du prototype navigateur sont
refusés, jamais supprimés silencieusement.

Taille du JSON limité à 3 000 000 octets comme dans l'export C11.
Les checkpoints contiennent une signature de format, longueur,
SHA-256 et les **octets originaux** du JSON. Le hash est un contrôle
d'intégrité accidentelle, pas une signature de provenance.

## Écriture contrôlée et récupération

- Sous un dossier temporaire, création d'un fichier staging
  mkstemp exclusif, écriture, fsync du fichier et fermeture.
- Lors d'une mise à jour, la version courante valide est recopiée
  en staging puis promue vers notes-previous.chk avant remplacement
  de notes-current.chk par le nouveau staging.
- os.replace est utilisé uniquement entre fichiers du même dossier.
  Sur POSIX, le dossier est synchronisé après chaque remplacement.
  Windows ne garantit pas ici de fsync portable du répertoire.
- Après commit, relecture intégrale du checkpoint courant, validation
  du format, du SHA et du JSON. La réponse porte explicitement
  host_snapshot_verified, pas une preuve d'écriture Kobo.
- Un ancien hash exact est obligatoire pour remplacer une version
  existante. Les fichiers corrompus, liens symboliques et chemins
  invalides sont refusés avant réécriture.
- Si current est absent ou corrompu, previous peut être récupéré
  en **lecture seule**, avec recovery_required=true. Aucun succès
  de restauration native n'est annoncé.

Les tests injectent une interruption avant promotion, vérifient que
current et previous restent alors intacts, et altèrent current pour
vérifier un retour contrôlé à previous. Le protocole est prévu pour
**un seul écrivain coopératif**. Le contrôle de hash n'est PAS un
compare-and-swap atomique face à deux processus concurrents ; il faut
une stratégie de verrouillage/transaction validée avant production.

## Frontières de sûreté

Ce prototype fonctionne exclusivement en hôte et sur répertoire
temporaire. Il n'ouvre pas de raw device, ne monte ni n'efface P1,
P2/recoveryfs ou P3, n'installe aucun paquet ni daemon, ne fait pas
de réseau, et ne nécessite aucun accès KOReader/Nickel.

Ce mécanisme **ne rend pas Mes Notes persistantes sur l'Aura HD** :
il manque un emplacement P3 explicitement qualifié, la gestion de
synchronisation/rotation FAT32, les pannes d'alimentation réelles,
les permissions, le rejeu de récupération et le parseur d'import
pmkb-notes-v1 dans le C11. Les promesses d'atomicité système et de
durabilité sont encore liées aux particularités du FS et de l'OS.
Le format des deux slots pourra changer quand P3 sera qualifiée.

Le Launcher continue de refuser la fermeture sans discard explicite
de Notes non vides, même après export ou checkpoint hôte validé.
L'interface ne doit PAS afficher Enregistré à la place de l'utilisateur.

## Preuve et tests

- tests/test_native_notes_checkpoint.py : octets UTF-8, rotation,
  corruption et repli, crash avant remplacement, conflit de version,
  liens, dépassements, JSON et timestamps malformés ;
- experimental/native-ui/tests/check_native_json.py : fixture JSON
  **produite par le code C11 réel** passée dans l'adaptateur hôte,
  puis relue octet par octet ;
- matrice Python Windows/Linux et CI C11 native.

Une CI verte ne prouve ni le montage P3, ni une restauration des
données dans l'éditeur natif, ni une exécution sur Kobo Aura HD.
