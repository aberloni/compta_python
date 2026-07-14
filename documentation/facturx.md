# Facturation électronique obligatoire — Factur-X / EN 16931

Recherche effectuée le 2026-07-14. À revérifier périodiquement, la réforme évolue.

## Calendrier — auto-entrepreneur (BNC)

| Date | Obligation |
|---|---|
| 1er septembre 2026 | **Réception** de factures électroniques via une plateforme agréée (PA) |
| 1er septembre 2027 | **Émission** de factures électroniques structurées pour les clients professionnels + **e-reporting** |

Concerne tous les auto-entrepreneurs assujettis à la TVA, y compris ceux en franchise en base
(exonérés de collecter la TVA mais toujours assujettis au sens de la réforme).

## Obligations principales

- **Plateforme agréée (PA)** obligatoire avant septembre 2026, pour réception puis émission des factures.
- **Format structuré** : Factur-X, UBL ou CII (le format doit permettre le traitement automatisé + le suivi par
  l'administration fiscale).
- **E-reporting** : transmission des données de facturation au fisc (numéros de facture, montants TVA, dates de
  paiement) — notamment pour le B2C et les opérations internationales, en plus du B2B structuré.
- **Nouveaux champs obligatoires** à terme : SIREN du client, adresse de livraison si différente de l'adresse de
  facturation, nature de l'opération (vente de bien, prestation de service, ou mixte).

## Le format Factur-X

Un fichier Factur-X est un **PDF hybride** :
- un **PDF/A-3** lisible normalement par un humain (identique en apparence à un PDF classique),
- + un **fichier XML embarqué en pièce jointe** (`factur-x.xml`), structuré selon la norme **CII**
  (Cross Industry Invoice, UN/CEFACT), elle-même conforme au modèle sémantique européen **EN 16931**.

Donc : même PDF visible, plus une couche de données machine-readable à côté. Alternative pure XML : **UBL**
(l'autre syntaxe reconnue par EN 16931, non hybride).

`EN 16931` est le standard sémantique européen (champs obligatoires/optionnels d'une facture), indépendant du
format de transport (CII ou UBL). Révisé le 13 février 2026 pour intégrer les échanges B2B.

## Profils Factur-X (niveaux de détail du XML)

| Profil | ~Champs | Usage |
|---|---|---|
| MINIMUM | 25 | quasi obsolète |
| BASIC WL | 45 | en-tête/pied seulement, pas de lignes |
| BASIC | 60 | + détail des lignes |
| **EN 16931** | 160 | standard complet, recommandé pour interopérabilité totale |
| EXTENDED | 200+ | données sectorielles (douane, logistique) |

Aucun profil n'est légalement imposé, mais **EN 16931** est recommandé pour être compatible avec toutes les
plateformes agréées.

## Exigences du profil EN 16931

- **Détail des lignes** : désignation, quantités, prix unitaire, taxe par ligne
- **Cohérence arithmétique** : le total HT doit égaler la somme des lignes
- **Ventilation TVA** par catégorie et taux
- **Identifiants obligatoires** : numéro de facture, date, codes de type de document

## Contraintes techniques — XML embarqué dans le PDF

- Le XML doit être nommé `factur-x.xml`
- Validé contre un schéma XSD propre au profil
- Conforme aux règles métier Schematron (codes `BR-*`) : cohérence arithmétique, présence conditionnelle de
  champs, listes de codes valides (devises ISO 4217, codes UNTDID)
- Déclaré dans les métadonnées XMP du PDF avec un `ConformanceLevel` correspondant
- Le PDF lui-même doit être strictement **PDF/A-3** : polices intégrées, pas de JavaScript, pas de chiffrement

## Implications concrètes pour compta_python

Le pipeline actuel (`packages/export/exporter.py` → WeasyPrint → PDF depuis `bill_template.html`) génère déjà un
PDF classique. Pour devenir conforme un jour :

1. **Générer un XML CII** à partir des données déjà calculées dans `Bill`/`Project`/`Client` (HT/TVA/TTC déjà
   disponibles — il « suffit » de les sérialiser dans la structure CII)
2. **Attacher ce XML au PDF** en pièce jointe conforme PDF/A-3, avec les métadonnées XMP correctes
3. **Garantir la conformité PDF/A-3** du PDF généré par WeasyPrint (polices intégrées, pas de JS, pas de
   chiffrement — WeasyPrint le fait généralement déjà, à vérifier)
4. **Ajouter des champs manquants** au modèle de données actuel : SIREN du client (absent de `clients/{uid}.compta`
   aujourd'hui), adresse de livraison si différente, nature de l'opération

Bibliothèques Python existantes pour éviter de tout coder à la main : `factur-x`, `drafthorse` (génération XML
CII + attachement PDF/A-3).

## Priorité

Rien d'urgent : l'obligation d'émission tombe en **septembre 2027** pour un auto-entrepreneur. Ce qui peut être
anticipé dès maintenant sans attendre : ajouter le **SIREN client** et la **nature de l'opération** au modèle de
données (`clients/{uid}.compta` / `projects/{uid}.compta`), sur le même principe que `country`/`tva` déjà ajoutés.
Le reste (génération XML CII, conformité PDF/A-3) peut attendre une lib dédiée, ou passer par une plateforme
agréée qui s'en charge à la place du code.

## Sources

- [La facturation électronique : obligatoire au 1er septembre 2026 — Urssaf.fr](https://www.urssaf.fr/accueil/actualites/facturation-electronique.html)
- [Facture électronique auto-entrepreneur : obligations, calendrier 2026 et solutions — Pennylane](https://www.pennylane.com/fr/fiches-pratiques/facture-electronique/obligation-pour-les-auto-entrepreneurs)
- [Facturation électronique obligatoire pour les auto-entrepreneurs : guide 2026-2027 — portail-autoentrepreneur.fr](https://www.portail-autoentrepreneur.fr/academie/gestion-auto-entreprise/facturation/facture-electronique-obligatoire)
- [Factur-X EN — fnfe-mpe.org](https://fnfe-mpe.org/factur-x/factur-x_en/)
- [Factur-X : le guide technique complet — FactureValide](https://facturevalide.fr/blog/factur-x-guide-technique-complet.html)
- [Tout savoir sur la facturation électronique pour les entreprises — economie.gouv.fr](https://www.economie.gouv.fr/tout-savoir-sur-la-facturation-electronique-pour-les-entreprises)
