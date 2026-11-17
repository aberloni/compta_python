# Facturation électronique — Factur-X / EN 16931

Comment compta_python produit et transmet les factures électroniques, puis le contexte réglementaire
(recherche du 2026-07-14, à revérifier périodiquement : la réforme évolue).

---

## Dans l'app

### Principe

Tout est généré **dans l'app** : XML CII, PDF/A-3, métadonnées XMP. La plateforme agréée (**SUPER PDP**) sert
uniquement de **tunnel de transmission** pour les fichiers Factur-X produits par compta_python. Elle ne génère
ni ne met en forme aucune facture (l'endpoint `/invoices/convert` de l'API n'est pas utilisé).

Aucune dépendance supplémentaire : le XML est écrit à la main (`xml.etree`), le PDF/A-3 est produit par
WeasyPrint, déjà utilisé pour les factures classiques.

| Fichier | Rôle |
|---|---|
| `runtime/tools/einvoice.py` | Construction du Factur-X (données → XML CII → PDF/A-3b) + pipeline vérifier / envoyer |
| `runtime/modules/superpdp.py` | Client de l'API SUPER PDP (authentification, validation, envoi, statuts) |
| `runtime/view_digital.py` | Page « Digital » de l'app |
| `runtime/app_gui.py` | Méthodes `digital_*` appelées par les boutons de la page |

### Données à renseigner

| Donnée | Où | Usage dans le Factur-X |
|---|---|---|
| SIREN vendeur | `infos/autoe.info` → `siren:` | **obligatoire** (refus sinon) ; identifiant légal + adresse électronique `0225:{SIREN}` |
| N° TVA, email, téléphone vendeur | `infos/autoe.info` → `tva:`, `email:`, `phone:` | identification + contact vendeur |
| Mention RCS/RM | `infos/statics.info` → `dispense:` | informations légales du vendeur |
| Nature de l'opération | `infos/statics.info` → `operation:` | cadre de facturation BT-23 : `S1` si le texte contient « service », `B1` si « bien », sinon `M1` |
| RIB | `infos/rib.info` → `iban:`, `bic:`, `titulaire:` | moyen de paiement (virement SEPA, code 58) |
| SIREN client | `clients/{uid}.cli` → `siren:` (ou les 9 premiers chiffres de `siret:`) | identifiant légal de l'acheteur + adresse électronique par défaut |
| Adresse électronique client | `clients/{uid}.cli` → `eaddress:schéma:valeur` | routage de la facture ; par défaut `0225:{SIREN}` (annuaire PPF). Ex. client belge sur Peppol : `eaddress:0208:0123456789` |
| Pays, N° TVA client | `clients/{uid}.cli` → `country:`, `tva:` | adresse + catégorie de TVA |
| Taux TVA + mention par pays | `infos/{ISO}.info` → `tva:`, `mention:` | taux appliqué ; la `mention` devient le motif d'exonération |

Un client sans SIREN, sans SIRET et sans `eaddress:` ne peut pas recevoir de facture électronique : l'app
refuse avec un message indiquant quoi ajouter dans son fichier `.cli`. SIREN et SIRET se saisissent sur la page
Clients (le bouton « Annuaire » ouvre l'annuaire des entreprises pour retrouver le SIREN). Le SIREN et la nature
de l'opération s'affichent aussi sur le PDF classique.

L'adresse (`rue|…|93100 MONTREUIL`) est découpée ainsi : la dernière partie donne le code postal et la ville,
les précédentes (3 au maximum) les lignes d'adresse.

### Page « Digital »

- **Identifiants** : ouvre `runtime/superpdp.conf` (`client_id:` / `client_secret:`, clé API créée dans le
  tableau de bord SUPER PDP). Fichier gitignoré, hors de `database/` : il n'est ni commité ni inclus dans les
  sauvegardes zip. Bac à sable ou production : c'est la clé qui le décide.
- **Tester la connexion** : affiche l'entreprise à qui appartient la clé et l'environnement.
- **Vérifier** (par facture) : génère le Factur-X puis demande le rapport de validation à SUPER PDP, sans rien
  envoyer. Sans identifiants, génère seulement le fichier.
- **Envoyer** (par facture) : génère, valide, puis transmet **uniquement si le rapport est valide**. Envoi
  définitif, après confirmation. Une facture déjà envoyée ne peut pas l'être une seconde fois.
- **Rafraîchir les statuts** : récupère le dernier statut de chaque facture envoyée.
- **Dossier Factur-X** : ouvre `exports/digital/`.

La page elle-même n'appelle jamais le réseau : les statuts affichés sont les derniers enregistrés.

### Construction d'un Factur-X (`make_facturx`)

1. **Données** (`invoice_data`) : mêmes lignes et totaux que le PDF classique.
   - forfait (`forfait:`) → 1 ligne, quantité 1 (unité `C62`) ;
   - `jours:` → 1 ligne, N jours (unité `DAY`) au taux du début de facture ;
   - sinon → 1 ligne par mois, « {label ou Prestation} {mois} {année} », jours × taux du mois, avec la période
     couverte ;
   - `frais:` → 1 ligne chacun, « {type} : {libellé} », unité `C62`.

   Le TTC recalculé doit égaler celui du PDF (à 1 centime près), sinon refus.
2. **TVA** : catégorie `S` si le taux est > 0 ; sinon `E` (client FR, exonéré), `AE` (client UE,
   autoliquidation) ou `G` (hors UE, export), avec la `mention` du pays comme motif d'exonération.
3. **XML CII** (`build_cii`) : profil **EN 16931** (`urn:cen.eu:en16931:2017`), facture type `380`, devise EUR,
   référence de paiement = n° de facture, échéance = date limite de la facture, projet = uid + objet. Notes
   françaises obligatoires ajoutées : `PMT` (indemnité de recouvrement 40 €), `PMD` (pénalités de retard), `AAB`
   (pas d'escompte).
4. **PDF** : le HTML de la facture classique est rendu par WeasyPrint en **`pdf/a-3b`**, avec `factur-x.xml` en
   pièce jointe (`AFRelationship /Data`) et l'extension XMP Factur-X (`fx:DocumentType` INVOICE,
   `fx:Version` 1.0, `fx:ConformanceLevel` EN 16931).

Sortie : `exports/digital/{fullUid}_{client}_{projet}_facturx.pdf` et le `.xml` à côté. Les fichiers temporaires
(HTML, XMP) sont supprimés.

### Envoi et suivi (SUPER PDP)

API `https://api.superpdp.tech`, routes `/v1.beta`, jeton OAuth2 (client credentials, `/oauth2/token`).

| Action | Route |
|---|---|
| Tester la connexion | `GET /v1.beta/companies/me` |
| Vérifier | `POST /v1.beta/validation_reports` |
| Envoyer | `POST /v1.beta/invoices` (corps = le PDF Factur-X, `external_id` = n° de facture) |
| Statuts | `GET /v1.beta/invoices/{id}` (codes `api:*`, cycle de vie `fr:200` … `fr:213`) |

Chaque envoi est enregistré dans `database/digital/superpdp.digital`, une ligne par facture, séparée par des
tabulations : `fullUid  idSUPERPDP  envoyéeLe  statut  libellé`. Pour pouvoir renvoyer une facture, supprimer sa
ligne à la main.

### Limites connues

- **Frais + TVA** : une facture qui a des `frais:` et une TVA > 0 est refusée (non géré).
- **Adresse de livraison** distincte de l'adresse de facturation : non gérée.
- **Avoirs** (type 381) : non gérés.
- **E-reporting** (B2C, international, paiements) : non géré.
- **Conformité non vérifiée en local** : ni veraPDF (PDF/A-3 strict), ni XSD/Schematron. C'est le rapport de
  validation SUPER PDP (bouton « Vérifier ») qui fait foi.

---

## Contexte réglementaire

### Calendrier — auto-entrepreneur (BNC)

| Date | Obligation |
|---|---|
| 1er septembre 2026 | **Réception** de factures électroniques via une plateforme agréée (PA) |
| 1er septembre 2027 | **Émission** de factures électroniques structurées pour les clients professionnels + **e-reporting** |

Concerne tous les auto-entrepreneurs assujettis à la TVA, y compris ceux en franchise en base
(exonérés de collecter la TVA mais toujours assujettis au sens de la réforme).

### Obligations principales

- **Plateforme agréée (PA)** obligatoire, pour la réception puis l'émission des factures.
- **Format structuré** : Factur-X, UBL ou CII (le format doit permettre le traitement automatisé + le suivi par
  l'administration fiscale).
- **E-reporting** : transmission des données de facturation au fisc (numéros de facture, montants TVA, dates de
  paiement) — notamment pour le B2C et les opérations internationales, en plus du B2B structuré.
- **Nouveaux champs obligatoires** : SIREN du client, adresse de livraison si différente de l'adresse de
  facturation, nature de l'opération (vente de bien, prestation de service, ou mixte).

### Clients dans un autre pays de l'UE (ex. Belgique)

La réforme ne couvre que le **B2B France ↔ France**. Pour un client établi dans un autre État membre, pas
d'obligation de Factur-X : le PDF actuel envoyé par mail reste valable.

**Côté France — e-reporting (à partir du 1er septembre 2027)**
- Pas la facture elle-même, seulement ses données : date, HT, TVA (0, autoliquidation), n° TVA du client, pays.
- Transmises via la PA (SUPER PDP), qui les remonte à l'administration.
- Pas encore géré par l'app (voir « Limites connues »).

**Côté Belgique — Peppol**
- Depuis le 1er janvier 2026, la facturation électronique B2B via **Peppol** est obligatoire entre entreprises
  établies en Belgique.
- Un fournisseur français non établi en Belgique n'y est pas soumis, mais un client belge peut demander une
  facture Peppol (sa compta ne traite plus que ça).
- Dans ce cas : `eaddress:0208:{numéro BCE}` dans `clients/{uid}.cli` (0208 = schéma Peppol des numéros
  d'entreprise belges). La page « Digital » envoie alors la facture en catégorie TVA **AE** (autoliquidation).
  À vérifier : que SUPER PDP route bien vers Peppol.
- Sans `eaddress:`, « Vérifier » / « Envoyer » refusent un client étranger — voulu.

**Inchangé d'ici là**
- Mentions sur la facture : n° TVA du client + mention d'autoliquidation (`infos/{ISO}.info` → `mention`).
- **DES** (déclaration européenne de services) mensuelle pour les prestations B2B intra-UE.

**Horizon — ViDA (1er juillet 2030)** : la directive européenne *VAT in the Digital Age* rend la facture
électronique obligatoire pour le B2B intra-UE, avec une déclaration quasi temps réel qui remplacera la DES.

### Le format Factur-X

Un fichier Factur-X est un **PDF hybride** :
- un **PDF/A-3** lisible normalement par un humain (identique en apparence à un PDF classique),
- + un **fichier XML embarqué en pièce jointe** (`factur-x.xml`), structuré selon la norme **CII**
  (Cross Industry Invoice, UN/CEFACT), elle-même conforme au modèle sémantique européen **EN 16931**.

Alternative pure XML : **UBL** (l'autre syntaxe reconnue par EN 16931, non hybride).

`EN 16931` est le standard sémantique européen (champs obligatoires/optionnels d'une facture), indépendant du
format de transport (CII ou UBL). Révisé le 13 février 2026 pour intégrer les échanges B2B.

### Profils Factur-X (niveaux de détail du XML)

| Profil | ~Champs | Usage |
|---|---|---|
| MINIMUM | 25 | quasi obsolète |
| BASIC WL | 45 | en-tête/pied seulement, pas de lignes |
| BASIC | 60 | + détail des lignes |
| **EN 16931** | 160 | standard complet, recommandé pour l'interopérabilité — **celui utilisé par l'app** |
| EXTENDED | 200+ | données sectorielles (douane, logistique) |

### Exigences du profil EN 16931

- **Détail des lignes** : désignation, quantités, prix unitaire, taxe par ligne
- **Cohérence arithmétique** : le total HT doit égaler la somme des lignes
- **Ventilation TVA** par catégorie et taux
- **Identifiants obligatoires** : numéro de facture, date, codes de type de document

### Contraintes techniques — XML embarqué dans le PDF

- Le XML doit être nommé `factur-x.xml`
- Validé contre un schéma XSD propre au profil
- Conforme aux règles métier Schematron (codes `BR-*`) : cohérence arithmétique, présence conditionnelle de
  champs, listes de codes valides (devises ISO 4217, codes UNTDID)
- Déclaré dans les métadonnées XMP du PDF avec un `ConformanceLevel` correspondant
- Le PDF lui-même doit être strictement **PDF/A-3** : polices intégrées, pas de JavaScript, pas de chiffrement

---

## Sources

- [La facturation électronique : obligatoire au 1er septembre 2026 — Urssaf.fr](https://www.urssaf.fr/accueil/actualites/facturation-electronique.html)
- [Facture électronique auto-entrepreneur : obligations, calendrier 2026 et solutions — Pennylane](https://www.pennylane.com/fr/fiches-pratiques/facture-electronique/obligation-pour-les-auto-entrepreneurs)
- [Facturation électronique obligatoire pour les auto-entrepreneurs : guide 2026-2027 — portail-autoentrepreneur.fr](https://www.portail-autoentrepreneur.fr/academie/gestion-auto-entreprise/facturation/facture-electronique-obligatoire)
- [Factur-X EN — fnfe-mpe.org](https://fnfe-mpe.org/factur-x/factur-x_en/)
- [Factur-X : le guide technique complet — FactureValide](https://facturevalide.fr/blog/factur-x-guide-technique-complet.html)
- [Tout savoir sur la facturation électronique pour les entreprises — economie.gouv.fr](https://www.economie.gouv.fr/tout-savoir-sur-la-facturation-electronique-pour-les-entreprises)
- [API SUPER PDP (OpenAPI)](https://www.superpdp.tech/openapi/)
