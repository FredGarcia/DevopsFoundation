# Rapport de tests — Reprise DEX -> CAST'IN

Ce rapport est généré par `tests/run_tests.py` à partir de DEX `.docx` synthétiques couvrant des cas nominaux, des absences attendues, et des FAUX POSITIFS / FAUX NÉGATIFS connus de l'outil.

## 01_cas_nominal_complet

Cas nominal : toutes les sections présentes, bien structurées (vrais positifs attendus).

- Fichier : `fixtures/DEX_S20001_Nominal.docx`
- **Score : 28/28 (100%)**

  - ✅ Numéro de solution extrait du nom de fichier
  - ✅ Auteur extrait de la page de garde
  - ✅ Responsable extrait
  - ✅ Description Fonctionnelle retrouvée (par nom)
  - ✅ Texte d'aide italique/coloré exclu de la Description Fonctionnelle
  - ✅ Lien Dossier Archi (DAP) retrouvé
  - ✅ Schéma Applicatif (ADU) retrouvé
  - ✅ Données de la solution retrouvées
  - ✅ Principes et décisions laissé vide
  - ✅ Description Technique retrouvée
  - ✅ Plage de fonctionnement retrouvée
  - ✅ Supervision retrouvée (chapitre + sous-section)
  - ✅ Observabilité (Métrologie) retrouvée
  - ✅ Log (Diagnostique) retrouvé
  - ✅ Sauvegardes retrouvées
  - ✅ Servitudes et ordonnancements retrouvées
  - ✅ Comptes et services (tableau) retrouvés
  - ✅ Certificats (tableau) retrouvés
  - ✅ Liste blanche (tableau) retrouvée
  - ✅ Flux (tableau) retrouvés
  - ✅ Support (matrice RACI, tableau) retrouvé
  - ✅ Changement et MEP agrège Contrôle des opérations + Changements et MEP
  - ✅ Matière (repo) agrège le référentiel + la mention 'Merge Request'
  - ✅ Procédure de restauration retrouvée
  - ✅ Procédure de reconstruction retrouvée
  - ✅ Procédure de resynchronisation retrouvée
  - ✅ Informations supplémentaires : Assets mainframe + annexe
  - ✅ Aucun point critique inattendu (RAS ou points mineurs uniquement)

## 02_sections_manquantes

Sections majoritairement absentes : doivent être marquées 'Non concerné' et signalées (vrais négatifs attendus).

- Fichier : `fixtures/DEX_S20002_Minimal.docx`
- **Score : 7/7 (100%)**

  - ✅ Description Fonctionnelle retrouvée
  - ✅ Description Technique retrouvée
  - ✅ Supervision absente -> 'Non concerné'
  - ✅ Sauvegardes absentes -> 'Non concerné'
  - ✅ Certificats absents -> 'Non concerné'
  - ✅ Liste blanche absente -> 'Non concerné'
  - ✅ Sections absentes toutes signalées dans les points à vérifier

## 03_faux_positif_italique_legitime

FAUX POSITIF connu : contenu fonctionnel légitime mis en forme en italique/couleur -> exclu à tort par l'heuristique de la règle 2 (score < 100% attendu : limite documentée).

- Fichier : `fixtures/DEX_S20003_FauxPositif.docx`
- **Score : 1/2 (50%)**

  - ✅ Première phrase de la Description Fonctionnelle retrouvée
  - ❌ [FAUX POSITIF ATTENDU] Le contenu métier en italique/couleur est CONSERVÉ

## 04_faux_negatif_titre_non_standard

FAUX NÉGATIF connu : section 'Sauvegarde' présente mais avec un titre dans un style non reconnu -> section non détectée, contenu non repris (score < 100% attendu : limite documentée).

- Fichier : `fixtures/DEX_S20004_FauxNegatif.docx`
- **Score : 2/3 (67%)**

  - ✅ Description Fonctionnelle retrouvée
  - ✅ Description Technique retrouvée
  - ❌ [FAUX NÉGATIF ATTENDU] Section Sauvegardes détectée malgré le titre non standard

## 05_numerotation_atypique

Sections numérotées très différemment des indications du prompt : doivent être retrouvées par leur NOM (règle 1).

- Fichier : `fixtures/DEX_S20005_Numerotation.docx`
- **Score : 3/3 (100%)**

  - ✅ Description Fonctionnelle retrouvée malgré la numérotation 9.4
  - ✅ Description Technique retrouvée malgré la numérotation 2.1
  - ✅ Supervision retrouvée malgré le placement en 'Annexe B'

## 06_liens_dap_adu_sections_separees

Lien DAP et référence ADU répartis sur deux sections différentes : agrégation multi-sections.

- Fichier : `fixtures/DEX_S20006_LiensSepares.docx`
- **Score : 3/3 (100%)**

  - ✅ Lien Dossier Archi (DAP) retrouvé dans 'Architecture fonctionnelle & applicative'
  - ✅ Schéma Applicatif (ADU) retrouvé dans 'Description de la solution'
  - ✅ Lien Dossier Archi ne contient PAS de texte hors-périmètre

## 07_servitudes_absentes_non_concerne

Absence légitime de servitudes : 'Non concerné' est la valeur correcte (règle 4).

- Fichier : `fixtures/DEX_S20007_Servitudes.docx`
- **Score : 2/2 (100%)**

  - ✅ Servitudes et ordonnancements -> 'Non concerné'
  - ✅ Description Fonctionnelle retrouvée

## 08_identification_absente

Aucune information d'identification présente : doit être signalé pour les 3 champs.

- Fichier : `fixtures/DEX_sans_identification.docx`
- **Score : 4/4 (100%)**

  - ✅ Numéro de solution absent -> signalé
  - ✅ Auteur absent -> signalé
  - ✅ Responsable absent -> signalé
  - ✅ Description Fonctionnelle retrouvée malgré l'absence d'identification

## Récapitulatif par traitement (règle métier)

| Traitement | Score | % |
|---|---|---|
| Champs composés (Changement et MEP / Matière (repo)) | 2/2 | 100% |
| Identification (Solution / Auteur / Responsable) | 6/6 | 100% |
| Informations supplémentaires (annexe + Assets mainframe) | 1/1 | 100% |
| Liens DAP / ADU (champs 'lien uniquement') | 4/4 | 100% |
| Règle 1 — Repérage des sections par leur nom | 22/23 | 96% |
| Règle 2 — Exclusion du contenu non utile / explicatif | 2/3 | 67% |
| Règle 4 — Information absente -> 'Non concerné' | 5/5 | 100% |
| Règle 5 — 'Principes et décisions' vide | 1/1 | 100% |
| Règle 8 — Signalement des doutes (points à vérifier) | 2/2 | 100% |
| Extraction de contenu en tableaux | 5/5 | 100% |

## Score global

**50/52 (96%)**


## Lecture des résultats

- Les tests `03_faux_positif_italique_legitime` et `04_faux_negatif_titre_non_standard` contiennent des vérifications marquées **[FAUX POSITIF ATTENDU]** / **[FAUX NÉGATIF ATTENDU]** : leur échec (❌) est **normal** et quantifie une limite connue de l'outil (cf. README.md, section "Limites connues"). Un score de 0% sur CES lignes précises ne signale pas une régression.
- Pour tous les autres tests, un score < 100% indique une régression à analyser.
