# Audit local du runtime ARM

Le prochain jalon est P1 minimal → KOReader directement, sans Nickel. Le prototype de démarrage est déjà présent sur la branche `feat/rebuild-rootfs-spec` (commits `bec7fd5`, `6522092`), mais pas dans `main` au moment de cet ajout. Cet outil complète ce chantier sans reproduire son init ni construire une autre image.

```sh
python3 tools/pmkb.py audit-arm-runtime /chemin/rootfs-local
```

Utiliser uniquement un répertoire extrait localement, jamais une carte montée. L'outil ne monte rien, n'exécute aucun ELF, ne lance pas `ldd` et n'écrit aucun fichier. Il refuse les chemins spéciaux `/dev`, `/proc`, `/sys`, les fichiers non réguliers et les liens sortant de l'arbre. Les liens absolus sont interprétés dans le rootfs invité, pas dans le système hôte. P2/recoveryfs n'est pas un argument ni une destination.

Le JSON sur stdout contient les SHA-256 et les dépendances `DT_NEEDED` de chaque ELF, ainsi que `PT_INTERP`. Code de sortie 0 : contrôles statiques satisfaits ; 1 : dépendance absente/invalide, ELF incompatible ou erreur de lecture. Tous les ELF doivent être ARM ELF32 little-endian de type exécutable ou bibliothèque. Les scripts et autres fichiers ordinaires sont ignorés ; les bibliothèques transitives sont contrôlées lors du parcours complet. Un répertoire sans ELF est refusé.

Le contrat de recherche retenu pour ce premier audit est `/opt/koreader/libs`, `/lib`, `/usr/lib`, dans cet ordre. Une dépendance trouvée mais invalide bloque la résolution. RPATH/RUNPATH et les dépendances à chemin relatif sont refusés pour examen séparé. Le cache du chargeur, ses variantes de recherche, les versions de symboles, les attributs ARM/ABI flottante, les permissions d'exécution, les chargements `dlopen` et les bibliothèques choisies par Lua ne sont pas qualifiés. Adapter la configuration effective du futur lanceur à ce contrat reste nécessaire.

**Validation : tests synthétiques locaux seulement.** Aucun binaire Kobo n'est redistribué. Un verdict `ok` ne prouve ni l'absence de dépendance à Nickel, ni un démarrage matériel, ni la compatibilité avec le noyau Aura HD. Le rapport porte toujours `physical_restore_eligible=false` et `hardware_qualified=false` ; il ne remplace aucun rapport ou garde-fou de restauration.

## Résultat du lot (3 octobre 2026)

Sur l'hôte Linux : 250 tests exécutés, 244 réussis, 5 ignorés (Qt indisponible), 1 échec préexistant : `LinuxDestinationDetectionTests.test_unknown_device_is_undetermined`. Ce dernier a été reproduit avec les fichiers de `main` inchangés dans un répertoire temporaire. Les 5 tests du nouvel audit, l'intégration CLI et le paquet Debian passent. Les tests de construction d'images synthétiques nécessitent une exécution hors du confinement fakeroot de cet hôte. La matrice Windows reste à vérifier en CI.

Audit de non-écriture : le nouvel outil ne contient aucune ouverture en écriture, aucun sous-processus et aucun chemin de restauration ; ses fixtures seules écrivent dans des répertoires temporaires. Aucun périphérique physique ni P2 n'a été modifié.
