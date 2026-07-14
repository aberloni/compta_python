# Micro-entreprise — taux et seuils

Charges et seuils applicables à l'auto-entrepreneur, chargés depuis `database/infos/impots.info`
via `packages/database/impots.py → Impots`. Activité : profession libérale BNC, prestations de
services, régime général (non-CIPAV).

## Cotisations sociales (BNC, régime général non-CIPAV)

| Période | Taux |
|---|---|
| jusqu'au 30/09/2022 | 22,0 % |
| 01/10/2022 → 2024 | 21,1 % |
| 2025 | 22,2 % *(déduit : 24,6 % total − 0,2 % CFP − 2,2 % libératoire, pas vérifié sur avis réel)* |
| à partir du 01/01/2026 | **23,2 %** — confirmé sur un avis URSSAF réel du foyer (T1 2026) |

⚠️ Attention à la terminologie : le "25,6 %" largement cité dans la presse pour 2026 est le **taux
total** (cotisations + CFP + libératoire combinés), pas les cotisations seules — confusion faite une
première fois dans cette doc, corrigée après vérification sur un avis réel. Le "23,2 %" est aussi,
par coïncidence, le taux CIPAV (professions réglementées) — sans rapport, ne pas confondre les deux
23,2 % qui désignent des choses différentes.

## CFP — contribution formation professionnelle

**0,2 %**, stable pour les professions libérales depuis l'unification de 2017 (0,3 % artisanal,
0,1 % vente, 0,2 % services/libéral). Confirmé sur un avis URSSAF réel (T1 2026).

## Versement libératoire de l'impôt sur le revenu

**2,2 %** pour les BNC, stable depuis longtemps (1 % vente, 1,7 % prestations BIC, 2,2 % BNC).
Option soumise à conditions de revenu fiscal de référence (RFR).

## Total combiné (si versement libératoire actif)

23,2 % (cotisations) + 0,2 % (CFP) + 2,2 % (libératoire) = **25,6 %** en 2026.

*Exemple illustratif (valeurs fictives, pas le CA réel) : pour 10 000 € de CA encaissé,*
*cotisations 2 320 €, CFP 20 €, libératoire 220 €, total 2 560 € (25,6 %).*
*Le taux de 25,6 % en lui-même a été confirmé sur un avis URSSAF réel — seuls les montants en €*
*ci-dessus sont un exemple, pas les chiffres réels du foyer.*

## Seuil de franchise en base de TVA — prestations de services (BNC)

| Période | Seuil de base |
|---|---|
| 2018-2019 | 35 200 € |
| 2020-2022 | 34 400 € |
| 2023-2024 | 36 800 € |
| 2025-2026 | 37 500 € |

Seuil différent pour la vente de marchandises (85 000 € en 2025-2026) — ne pas confondre.
Un projet de seuil unique à 25 000 € puis 37 500 € (PLF 2025/2026) a été étudié puis abandonné ;
les seuils par activité restent donc en vigueur.

## Sources

- [Évolution des taux de cotisations sociales des auto-entrepreneurs — Urssaf.fr](https://www.urssaf.fr/accueil/actualites/taux-cotisations-autoentrepeneur.html)
- [Charges micro-entreprise 2026 : taux URSSAF et calcul — swim.legal](https://www.swim.legal/blog/charges-micro-entreprise-2026-taux-urssaf-calcul-obligations-d9294)
- [Baisse des taux de cotisations sociales en octobre 2022 — portail-autoentrepreneur.fr](https://www.portail-autoentrepreneur.fr/actualites/baisse-taux-cotisation-auto-entrepreneur-2022)
- [Le versement libératoire — impots.gouv.fr](https://www.impots.gouv.fr/professionnel/le-versement-liberatoire)
- [CFP micro-entreprise — lamicrobyflo.fr](https://lamicrobyflo.fr/contribution-formation-professionnelle/)
- [Seuils TVA Micro-entreprise 2026 — petite-entreprise.net](https://www.petite-entreprise.net/aucune/seuils-tva-micro-entreprise-2026.html)
- [Micro-entreprise : les nouveaux seuils pour 2023, 2024 et 2025 — lecoindesentrepreneurs.fr](https://www.lecoindesentrepreneurs.fr/nouveaux-seuils-micro-entreprise-2023-2024-2025/)
