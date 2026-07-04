# Scripts map

## do_ — génère des fichiers

| Script | Description |
|--------|-------------|
| `do_billing.py` | Génère les PDFs de toutes les factures de la période définie dans `configs.py` |
| `do_report.py` | Génère un rapport HTML avec la liste des factures dans `exports/billings/` |
| `do_zip_backup.py` | Crée un zip de `database/` horodaté dans `exports/backups/` — à copier sur le cloud manuellement |
| `do_zip_restore.py` | Extrait le zip le plus récent de `exports/backups/` pour reconstruire `database/` sur un nouveau PC |

## view_ — génère un HTML interactif

| Script | Description |
|--------|-------------|
| `view_billing.py` | Vue d'ensemble de la facturation : totaux par année, répartition par client, statut des paiements |
| `view_wiring.py` | Suivi des virements reçus : quelles factures sont payées, ce qui reste à encaisser |
| `view_tasks_summary.py` | Tous les jours travaillés regroupés par mois, avec le détail par projet |
| `view_tasks_project.py` | Tâches regroupées par projet : jours facturés, non facturés, et jours à zéro |
| `view_tasks_calendar.py` | Calendrier mensuel avec une barre de couleur par jour montrant le temps passé par projet |

## shell_ — affichage terminal uniquement

| Script | Description |
|--------|-------------|
| `shell_tva.py` | Affiche le HT, TVA et TTC de chaque facture |
| `shell_workdays.py` | Affiche le nombre de jours travaillés et manquants par mois |
| `shell_labels.py` | Affiche les libellés des transactions du relevé bancaire |
| `shell_unpaid.py` | ⚠️ WIP — rapprochement factures / relevé bancaire |
