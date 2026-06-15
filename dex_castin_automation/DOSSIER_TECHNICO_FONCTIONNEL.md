# Dossier technico-fonctionnel — Automatisation « Reprise DEX → CAST'IN »

## 1. Objet et périmètre

Ce dossier décrit l'automatisation de la **reprise du contenu d'un Dossier
d'Exploitation (DEX)**, fourni au format Word `.docx`, vers les champs de
l'outil **CAST'IN**, en application du document de référence
`Prompt_Reprise_DEX_vers_CASTIN.md`.

Le périmètre couvre **uniquement** la partie « traitement des DEX » de ce
document : extraction, nettoyage et mise en forme du contenu (règles 1 à 8),
identification (numéro de solution, auteur, responsable), et production des
trois blocs de sortie (Identification / Champs CAST'IN / Points à vérifier).

Sont **hors périmètre** : la saisie automatique dans CAST'IN lui-même (pas
d'API CAST'IN utilisée — l'outil produit un contenu prêt à coller), et la
génération du contenu d'un DEX (le DEX est une donnée d'entrée).

## 2. Architecture générale

```
                 ┌───────────────────────────────┐
                 │      dex_castin_common.py       │
                 │ (lecture .docx, règles métier,  │
                 │  nettoyage, mise en forme)       │
                 └───────────────┬─────────────────┘
                                  │ importé par
            ┌─────────────────────┴─────────────────────┐
            │                                             │
┌───────────────────────┐                 ┌──────────────────────────────────┐
│   dex_castin_cli.py     │                 │  dex_castin_word_addin_server.py  │
│ (ligne de commande /    │                 │  (serveur HTTP local, appelé      │
│  invite de commandes)   │                 │   par le complément Office.js)    │
└───────────┬─────────────┘                 └────────────────┬───────────────┘
            │ écrit                                            │ HTTP (localhost)
            ▼                                                  ▼
   *_CASTIN.md / .json                          ┌──────────────────────────────┐
                                                   │ addin/ (Office.js : manifest, │
                                                   │ taskpane.html, taskpane.js)   │
                                                   │ -> volet dans Word            │
                                                   └──────────────────────────────┘
```

**Principe directeur** : aucune règle métier n'est dupliquée. Les deux points
d'entrée (CLI et serveur Office.js) appellent la même fonction
`dex_castin_common.process_dex()` et produisent un résultat identique, quel
que soit le mode d'utilisation.

## 3. Lecture du fichier .docx (sans dépendance externe)

Un fichier `.docx` est une archive ZIP contenant du XML (format OOXML). Le
module commun lit directement :

- `word/document.xml` — corps du document (paragraphes `<w:p>`, tableaux `<w:tbl>`) ;
- `word/styles.xml` — définitions de styles, pour résoudre le **niveau de
  titre** (`Titre 1` / `Heading 1`, etc., y compris styles personnalisés
  basés sur ceux-ci, via `outlineLvl` ou la chaîne `basedOn`) ;
- `word/_rels/document.xml.rels` — relations, pour résoudre la **cible des
  hyperliens** (`w:hyperlink r:id=...` → URL).

Chaque paragraphe est représenté par une liste de *runs* (morceaux de texte
avec mise en forme : italique, couleur, cible d'hyperlien éventuelle), et
porte un niveau de titre (`heading_level`) si applicable. Chaque tableau est
représenté ligne par ligne / cellule par cellule.

## 4. Règles métier implémentées

### 4.1 Repérage des sections par leur nom (règle 1)

`_normalize_heading()` normalise le texte d'un titre : suppression de la
numérotation en tête (`2.1`, `12.3.4)`, `Annexe 1 -`...), suppression des
accents, mise en minuscules, suppression de la ponctuation.

`find_section()` parcourt les paragraphes à partir d'un index donné et
retourne la première section dont le titre normalisé contient un des
mots-clés définis pour le champ CAST'IN (table `CASTIN_FIELDS`). La fin de
section est le prochain titre de niveau **inférieur ou égal**, ce qui permet
de capturer :

- une **sous-section précise** (ex. `~2.1 Description de la solution`) ;
- un **chapitre entier avec ses sous-sections** (ex. `~6 Supervision`), car
  les sous-titres rencontrés ont un niveau strictement supérieur et ne
  déclenchent donc pas la fin de la section.

### 4.2 Contenu utile uniquement (règle 2)

`section_text()` concatène le texte des paragraphes et tableaux d'une
section, en excluant :

- les titres eux-mêmes (non inclus dans la plage `[start, end[`) ;
- les paragraphes "explicatifs" détectés par `Paragraph.is_explanatory()` :
  **tous** les *runs* non vides du paragraphe sont en italique **et** au
  moins un *run* porte une couleur explicite non standard (≠ noir/auto) —
  caractéristique des encarts d'aide « bleu/italique » des gabarits DEX.

Pour les champs « LIEN UNIQUEMENT » (Dossier Archi / Schéma Applicatif),
`section_links()` extrait **uniquement** les cibles d'hyperliens et les
références textuelles correspondant au motif attendu (`DAP...`, `ADU...`),
sans reprendre le texte environnant.

### 4.3 Nettoyage des caractères parasites (règle 3)

`clean_text()` :

- convertit les espaces insécables / fines en espace normal ;
- supprime les caractères de contrôle, marqueurs invisibles (BOM, marques de
  direction de texte, espaces de largeur nulle) et la zone Unicode "Private
  Use Area" utilisée par les puces des polices Wingdings/Symbol ;
- remplace les puces (`•`, `▪`, `●`, `◦`, `‣`, `·`, glyphes Wingdings) par
  `- ` en début de ligne ;
- compresse les espaces multiples et les lignes vides successives.

### 4.4 Information absente → « Non concerné » (règle 4)

Pour chaque champ, si la section source n'est pas trouvée (ou son contenu
est vide), la valeur est fixée à `Non concerné` (`none_value` dans
`CASTIN_FIELDS`), **sauf** :

- `Principes et décisions` → toujours vide (règle 5) ;
- `Informations supplémentaires` → vide si absent, car **optionnel** (règle 6).

Chaque absence (hors champs optionnels/vides) génère une entrée dans
« Points à vérifier auprès de l'Équipier Ops ».

### 4.5 Champs composés

- **Changement et MEP** : concatène `Contrôle des opérations` (~10) et
  `Changements et MEP` (~5), si toutes deux présentes.
- **Matière (repo)** : contenu de la section « Référentiel / Dépôt » (~5.1)
  **+** recherche, dans tout le document, des paragraphes mentionnant
  « Merge Request ».
- **Informations supplémentaires** : tout le contenu situé **après** la
  section « Resynchronisation » (~13.3) **+** la section « Assets
  mainframe » (~4.2.2) si elle existe ailleurs dans le document.

### 4.6 Identification

- **Numéro de solution** (`Sxxxx`) : recherché en priorité dans le **nom de
  fichier**, puis dans les ~60 premiers paragraphes du document.
- **Auteur** : paragraphe `Auteur : ...` recherché avant le premier titre
  (page de garde).
- **Responsable** : paragraphe `Responsable : ...` recherché dans les ~60
  premiers paragraphes ; à défaut, paragraphe `Service : ...` (avec
  signalement dans les points à vérifier).

### 4.7 Sortie (règle 8 + format imposé)

`format_markdown()` produit exactement les trois blocs définis par le
prompt :

1. **IDENTIFICATION** (Solution / Auteur / Responsable) ;
2. **CONTENU PAR CHAMP CAST'IN** — un bloc `**[Nom du champ]**` suivi du
   contenu nettoyé (ou `Non concerné` / `(laisser vide)`) ;
3. **POINTS À VÉRIFIER AUPRÈS DE L'ÉQUIPIER OPS** — liste à puces, ou `RAS`.

`to_json()` fournit la même information au format structuré, consommée par
le serveur Office.js.

## 5. Mode 1 — Utilisation autonome (`dex_castin_cli.py`)

- Entrée : un ou plusieurs chemins `.docx` (motifs `*.docx` développés par le
  script lui-même, y compris sous l'invite de commandes Windows qui ne
  développe pas les motifs).
- Traitement : appel direct à `dex_castin_common.process_dex()`.
- Sortie :
  - affichage console des 3 blocs ;
  - fichier `<nom>_CASTIN.md` (toujours) ;
  - fichier `<nom>_CASTIN.json` (sur option `--json`) ;
  - code de retour `0` si tout s'est bien passé (même avec des points à
    vérifier — ce sont des avertissements métier, pas des erreurs
    techniques), `1` si au moins un fichier n'a pu être traité (`.docx`
    corrompu, illisible...), `2` si aucun fichier trouvé.

## 6. Mode 2 — Intégration Word via Office.js (`dex_castin_word_addin_server.py` + `addin/`)

### 6.1 Pourquoi un service local ?

Un complément Office.js s'exécute dans une **vue web sandboxée** (le volet
Office) : il n'a pas accès au système de fichiers ni à un interpréteur
Python. `dex_castin_word_addin_server.py` est un serveur HTTP **local**
(`http.server` de la bibliothèque standard) qui expose le module commun via
une API JSON.

### 6.2 Flux d'exécution

1. L'utilisateur ouvre le DEX dans Word et clique sur **« Reprendre ce
   DEX »** (bouton ajouté au ruban par `manifest.xml`), qui ouvre le volet
   (`taskpane.html`).
2. Dans le volet, **« Analyser ce DEX »** déclenche `taskpane.js` :
   - `Office.context.document.getFileAsync(Office.FileType.Compressed, ...)`
     récupère le `.docx` du document **actuellement ouvert**, par tranches ;
   - les tranches sont concaténées puis encodées en base64 ;
   - `POST http://127.0.0.1:8943/api/process-dex` avec
     `{ "filename": ..., "docx_base64": ... }`.
3. Le serveur Python :
   - décode le base64 vers un fichier temporaire ;
   - appelle `dex_castin_common.process_dex()` ;
   - supprime le fichier temporaire ;
   - renvoie `dex_castin_common.to_json(result)`.
4. `taskpane.js` affiche les 3 blocs, avec un bouton **« Copier »** par
   champ pour le collage dans CAST'IN.

### 6.3 Sécurité et portée

- Le serveur n'écoute que sur `127.0.0.1` par défaut (`DEX_HOST`).
- CORS : en-tête `Access-Control-Allow-Origin` configurable
  (`DEX_ALLOWED_ORIGIN`), `*` par défaut pour le développement local.
- Taille de fichier limitée à 50 Mo (`MAX_UPLOAD_SIZE`).
- Aucune donnée n'est conservée : le fichier temporaire est supprimé après
  traitement, aucune écriture sur disque côté serveur autre que ce fichier
  temporaire éphémère.

### 6.4 Déploiement du complément

`addin/manifest.xml` est un manifeste minimal (`TaskPaneApp`), à adapter
(GUID, URLs HTTPS d'hébergement de `taskpane.html`/`taskpane.js`) puis
chargé dans Word via le **sideloading** (« Mes compléments → Téléverser mon
complément »). Le détail des étapes figure dans `README.md`.

## 7. Synthèse des règles ↔ implémentation

| Règle du prompt | Implémentation |
|---|---|
| 1. Repérage par nom, pas par numéro | `_normalize_heading()` + `find_section()` (mots-clés, pas de numéro) |
| 2. Contenu utile uniquement, pas de titres/texte explicatif | `section_text()` + `Paragraph.is_explanatory()` |
| 3. Suppression des caractères parasites | `clean_text()` |
| 4. Absence → "Non concerné" | `none_value` dans `CASTIN_FIELDS` + `process_dex()` |
| 5. "Principes et décisions" vide | `kind = "empty"` |
| 6. "Informations supplémentaires" optionnel | `kind = "appendix"`, `optional = True` |
| 7. Pas de reformulation | Aucune génération/reformulation de texte : extraction + nettoyage uniquement |
| 8. Doute → "Points à vérifier" | `points_a_verifier` alimenté à chaque section/identification non trouvée |

## 8. Tests effectués

Un document `.docx` de test (généré par script à partir de XML OOXML brut,
couvrant : page de garde avec Auteur/Responsable, sections avec et sans
numérotation, paragraphe explicatif italique/coloré à exclure, hyperlien
DAP, référence ADU en texte, tableau, section "Supervision" avec
sous-section, sections "Restauration"/"Resynchronisation" et contenu
d'annexe) a permis de vérifier :

- la bonne segmentation des sections par nom (numérotation variable) ;
- l'exclusion du paragraphe explicatif italique/coloré ;
- l'extraction des liens DAP/ADU (hyperlien + référence textuelle) sur
  plusieurs sections candidates ;
- le remplissage "Non concerné" + signalement pour les sections absentes ;
- le contenu de "Informations supplémentaires" (texte d'annexe après la
  Resynchronisation) ;
- le fonctionnement bout-en-bout du serveur HTTP (`/api/health`,
  `/api/process-dex` avec un `.docx` encodé en base64).

## 9. Évolutions possibles (hors périmètre actuel)

- Génération directe d'un export structuré pour import CAST'IN (si une API
  ou un format d'import existe), à partir du JSON déjà produit.
- Détection plus fine des paragraphes "explicatifs" (ex. configuration de la
  couleur attendue par organisation).
- Prise en charge de gabarits DEX alternatifs (mots-clés additionnels
  configurables sans modifier le code, ex. fichier de configuration JSON).
