# PMKB PowerLab V0 — calcul hors matériel

Lire d'abord [la feuille de route noyau/autonomie](../../docs/kernel-energy-roadmap-fr.md).

Ce module Python est volontairement **inerte**. Il n'est ni un driver, ni un collecteur sysfs, ni un service de gestion d'énergie, ni un benchmark validé. Aucun fichier ou périphérique n'est ouvert par ses fonctions.

- analyze(trace) valide un dictionnaire et intègre les échantillons tension/courant en énergie mWh, charge mAh et puissance moyenne mW.
- analyze_json(text) décode strictement une chaîne JSON en mémoire ; clés dupliquées et constantes non JSON sont refusées.
- compare(baseline, candidate) n'accepte que des traces de même provenance, scénario, instrument déclaré, charge de travail, radio, frontlight et durée proche (+/- 5 %). Le champ kernel peut changer.
- Les provenances synthetic et user_entered ne prouvent jamais l'authenticité d'une mesure. Aucun rapport n'affirme un gain énergétique vérifié ni une qualification matérielle.
- Contrat limité à la décharge sur batterie : temps croissant à partir de zéro, tension positive en mV, courant non négatif en mA, champs exacts. Pas d'estimation d'autonomie restante.

Pour tester à la racine du dépôt : python -m unittest discover -s tests -p test_power_trace.py -v

Ne jamais publier une sauvegarde privée, un firmware MCU, une waveform propriétaire ou des données d'utilisateurs.
