# Tasks

Les fichiers de tâches sont dans `database/tasks/`.
Un fichier par mois, nommé `YYYY-MM.task`.

## Syntaxe

```
DD: project
DD: project duration
```

- `DD` — jour du mois (01 à 31)
- `project` — uid du projet
- `duration` — fraction de journée (optionnel, défaut = 1)

## Durée

| Valeur | Signification |
|--------|--------------|
| *(omis)* | journée entière |
| `0.5` | demi-journée |
| `0.25` | quart de journée |
| `0.75` | trois-quarts |
| `1/2` `1/4` | fractions |
| `0` | présence sans facturation |

## Commentaires

`#` en début de ligne = commentaire ou jour exclu.

```
# semaine off
#08: project
#09: project
```

## Exemple

```
# 2026-01

08: micromega
09: micromega

15: micromega
16: tinies 0.5
16: mirliflore 0.5

29: micromega 0.25
29: tinies 0.5
```
