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
| `view_homepage.py` | Page d'accueil de l'app : liens vers toutes les autres pages |
| `view_billing.py` | Vue d'ensemble de la facturation : totaux par année, répartition par client, statut des paiements |
| `view_tva.py` | TVA à déclarer par mois (selon les paiements reçus) + déclarations faites |
| `view_trimester.py` | Charges URSSAF par trimestre (cotisations, CFP, libératoire) + déclarations faites |
| `view_wiring.py` | Suivi des virements reçus : quelles factures sont payées, ce qui reste à encaisser |
| `view_tasks.py` | Jours travaillés par mois (tous projets), ou détail facturé / non facturé par projet |
| `view_tasks_calendar.py` | Calendrier mensuel avec une barre de couleur par jour montrant le temps passé par projet |
| `view_bills_edit.py` | Édition des factures (dates, ajout, PDF à la demande) |
| `view_clients.py` | Édition des clients |
| `view_backups.py` | Sauvegarde : export / import de la base (zip) et dossiers de copie |

L'app (`app_gui.py`) affiche ces pages dans une fenêtre et branche leurs boutons.

## shell_ — affichage terminal uniquement

| Script | Description |
|--------|-------------|
| `shell_tva.py` | Affiche le HT, TVA et TTC de chaque facture |
| `shell_workdays.py` | Affiche le nombre de jours travaillés et manquants par mois |
| `shell_labels.py` | Affiche les libellés des transactions du relevé bancaire |
| `shell_unpaid.py` | ⚠️ WIP — rapprochement factures / relevé bancaire |

## tools/ — utilitaires

| Script | Description |
|--------|-------------|
| `tools/pdf_to_csv.py` | Convertit les relevés bancaires PDF de `database/releves/` en CSV (à lancer à la main) |
| `tools/routine_tasks.py` | Pré-génère les fichiers de tâches d'une année entière (à lancer à la main) |
| `tools/calendar_export.py` | Import des tâches depuis Google Agenda (utilisé par la page Calendrier) |
| `tools/bill_editor.py`, `client_editor.py`, `wire_editor.py`, `bill_pdf.py` | Écriture des fichiers factures / clients / virements et PDF à la demande (utilisés par l'app) |
