# Bills

Les fichiers de factures sont dans `database/bills/`.
Un fichier par projet, nommé `{projectUid}.bill`.

## Syntaxe

```
YYYY-MM-DD: YYYY-MM-DD, YYYY-MM-DD
  keyword: valeur
```

- Première date — date de facturation
- Deuxième et troisième dates — début et fin de la période facturée
- Les lignes suivantes (indentation facultative) — overrides de la facture

## Keywords

| Keyword | Effet |
|---------|-------|
| `objet` | Remplace le nom du projet dans la section OBJET |
| `designation` | Texte affiché au-dessus du tableau de lignes |
| `label` | Remplace `Prestation x N j` dans la ligne du tableau |
| `jours` | Force le nombre de jours affiché |
| `forfait` | Montant HT fixe (désactive le calcul jours × taux) |
| `frais` | Ligne supplémentaire : `label, prix_unitaire, quantité` |

## Exemples

### Facture standard
```
2026-01-31: 2026-01-01, 2026-01-31
```

### Avec frais
```
2026-01-31: 2026-01-01, 2026-01-31
  frais: Petits déjeuners, 6.70, 3
  frais: Repas, 19.40, 3
```

### Forfait fixe
```
2026-03-31: 2026-03-01, 2026-03-31
  forfait: 1500
  jours: 3
  label: Maintenance mensuelle
```

### Label et désignation custom
```
2024-12-15: 2024-12-01, 2024-12-30
  objet: Onboarding Pass - Cie Samuel Mathieu
  designation: Forfait prestation + frais
  label: Accompagnement et conseil en développement
  frais: Petits déjeuners, 6.70, 3
  frais: Repas, 19.40, 3
```

## Commentaires

`#` en début de ligne = commentaire.
