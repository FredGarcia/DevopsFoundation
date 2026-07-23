# DOF-PREP — Spécifications techniques

## 0. Objet

Ce document décrit **comment** DOF-PREP est construit : architecture, schémas
de données, algorithmes (avec formules), API de l'agent IA, environnement
d'exécution, stratégie de test et limites connues. Pour **ce que fait**
l'application, voir `SPECIFICATIONS_FONCTIONNELLES.md`. Pour l'installer, voir
`INSTALLATION.md`.

---

## 1. Architecture générale

Trois livrables **fonctionnellement équivalents**, partageant une source
unique de données (`questions.json`), plus un composant optionnel indépendant :

```
                        questions.json  (source unique, 315 questions)
                               |
        +----------------------+----------------------+
        |                                             |
  Python (stdlib)                              JavaScript (navigateur)
  devops_foundation_prep.py                    engine.js (moteur, port fidele)
  - http.server (SPA embarquee)                store.js (persistance locale)
  - sqlite3 (persistance)                      app.js   (interface, 5 vues)
        |                                             |
        |                                   +----------+----------+
        |                                   |                     |
   (application de bureau)          index.html + sw.js     dof-prep-standalone.html
                                     + manifest (PWA)       (fichier unique, banque inlinee)

  dof-prep-agent.py (optionnel, independant) --- API Anthropic (reseau, opt-in)
```

Le moteur JavaScript (`engine.js`) est un **portage fidèle** du moteur Python :
mêmes constantes officielles, mêmes algorithmes de quotas et de génération
d'examens, mêmes règles de correction et de calibration. Un point diffère
volontairement : le générateur pseudo-aléatoire (voir section 8, limitations).

---

## 2. Arborescence des fichiers

```
devops_foundation_prep.py     application Python complete (serveur + SPA + logique)
questions.json                 banque de questions — SOURCE UNIQUE (315 questions)
install.sh / install.ps1 / install-docker.sh    installeurs heredoc autoportes
.env.example                    variables d'environnement de l'app Python

dof-prep-web/                  build web (JS pur, aucune dependance)
  index.html                    page PWA
  app.css                       styles
  engine.js                     moteur (logique, portage du Python)
  store.js                      persistance localStorage
  app.js                        interface (vues + carte Assistant IA)
  sw.js                         service worker (cache hors-ligne, versionne)
  manifest.webmanifest          manifeste PWA
  questions.json                copie de la banque (identique, meme sha256)
  icon-192.png / icon-512.png / icon-180.png
  dof-prep-standalone.html      fichier unique autonome (banque inlinee)
  dof-prep-agent.py             agent IA compagnon (optionnel, independant)
  README_web.md / README_agent.md / .env.agent.example

(non livres : engine.test.js, ui.smoke.js, agent_unit_test.py, package.json,
 node_modules — suite de tests interne, cf. section 7)
```

---

## 3. Schéma de données — `questions.json`

```json
{
  "questions": [
    {
      "domain": "DOFD-1",
      "k_level": 1,
      "difficulty": 1,
      "type": "single",
      "statement": "Comment definit-on le mieux DevOps ?",
      "options": [
        { "text": "...", "correct": false },
        { "text": "...", "correct": true }
      ],
      "explanation": "..."
    }
  ]
}
```

| Champ | Type | Contrainte |
|---|---|---|
| `domain` | string | Un des 8 codes `DOFD-1`..`DOFD-8` |
| `k_level` | int | 1 à 7 |
| `difficulty` | int | 1 à 5 |
| `type` | string | `single` \| `multiple` \| `truefalse` |
| `statement` | string | Non vide, français sans accents |
| `options` | array | ≥ 2 éléments ; `truefalse` : exactement 2 |
| `explanation` | string | Texte pédagogique |

L'identifiant de question n'est **pas stocké** : côté JS, il correspond à
l'**index dans le tableau** (`id = i`) ; côté Python, la logique interne suit
le même principe. Les options reçoivent un identifiant dérivé `"${qi}:${oi}"`
côté JS.

Intégrité : sha256 = `303f39895ee9b8ad1fc0c018437d3a060f949ed92378f227f6d92b52495f51ca`
(doit être identique entre `questions.json` racine, `dof-prep-web/questions.json`,
et le contenu inliné dans `dof-prep-standalone.html`).

---

## 4. Schéma de persistance — `localStorage` (clé `dofprep:v1`)

```json
{
  "v": 1,
  "prefs": { "target_score": 0.90, "second_order": false, "agent_url": "http://127.0.0.1:8799" },
  "mastery": { "DOFD-1": { "score": 0.82, "attempts": 14 } },
  "cards": { "37": { "ease_factor": 2.5, "interval_days": 6, "repetitions": 2, "due_date": "2026-07-28" } },
  "confidence": [ { "predicted": 0.75, "is_correct": 1, "domain": "DOFD-3", "context": "exam", "ts": 1753180800000 } ],
  "theta_ability": 0.0,
  "theta_item": { "37": -0.4 },
  "attempts_total": 128,
  "history": [ { "ts": 1753180800000, "kind": "exam", "score": 0.85, "correct": 34, "total": 40, "label": "Examen blanc 3" } ]
}
```

Une migration douce complète les champs de préférence ajoutés après la
première version (ex. `agent_url`) sans jamais écraser une valeur déjà
personnalisée par l'utilisateur.

---

## 5. Algorithmes clés

### 5.1 Quotas par domaine (méthode du plus grand reste)

Pour chaque domaine `d` de poids officiel `w_d`, sur un examen de `N=40`
questions : part exacte `w_d × N`, partie entière allouée en premier, puis
les `N − Σ⌊w_d × N⌋` unités restantes attribuées aux domaines ayant la plus
grande partie fractionnaire (égalité départagée par index). Résultat fixe :
`{DOFD-1:5, DOFD-2:4, DOFD-3:7, DOFD-4:7, DOFD-5:6, DOFD-6:5, DOFD-7:2, DOFD-8:4}`
(somme 40).

### 5.2 Génération « par donne » (recouvrement nul)

Pour un niveau et un domaine donnés : les questions de la bande de difficulté
du niveau sont mélangées (PRNG à graine fixe dérivée du niveau et du domaine),
puis réparties **round-robin** entre les 4 examens du niveau — chaque question
n'atterrit donc que dans un seul des 4 examens. Un repli réutilise le reste de
la banque du domaine si la bande ne fournit pas assez de questions.

### 5.3 Générateur pseudo-aléatoire (mulberry32)

```
a = (seed >>> 0) || 1
next():
  a = (a + 0x6d2b79f5) | 0
  t = Math.imul(a ^ (a >>> 15), 1 | a)
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296
```

Déterministe et reproductible (même graine ⇒ même séquence), mais **distinct**
de l'algorithme Mersenne Twister utilisé par CPython (voir section 8).

### 5.4 Maîtrise par domaine (moyenne mobile exponentielle)

`score' = score × (1 − α) + y × α`, avec `α = 0.2` et `y ∈ {0, 1}` (juste/faux).
Première réponse : `score = y`.

### 5.5 Révision espacée (SM-2)

Sur une réponse de qualité `q` (2 = faux, 5 = juste dans cette implémentation) :
- si `q < 3` : répétitions → 0, intervalle → 1 jour ;
- sinon : répétitions += 1 ; intervalle = 1 j (1ʳᵉ répétition), 6 j (2ᵉ), puis
  `round(intervalle_précédent × facteur_de_facilité)` ;
- `facteur_de_facilité' = max(1.3, facteur + 0.1 − (5−q) × (0.08 + (5−q) × 0.02))`.

### 5.6 Second ordre — aptitude/difficulté (Elo léger)

`p = 1 / (1 + e^(-(aptitude - difficulté)))` (logistique) ; sur une réponse
juste/fausse `y` : `Δ = K × (y - p)` avec `K = 0.08` ; aptitude += Δ,
difficulté -= Δ ; les deux bornées à `[-4, 4]`.

### 5.7 Calibration (Brier, ECE, tendance)

- **Brier** : moyenne de `(confiance_déclarée - résultat)²` sur l'historique.
- **ECE** : somme pondérée, par tranche de confiance (< 40 %, ~50 %, ~75 %,
  ~95 %), de l'écart absolu entre confiance moyenne et réussite moyenne de la
  tranche.
- **Facteur de calibration** : `max(0.60, 1 − ECE)`, appliqué seulement si
  ≥ 20 enregistrements disponibles (`CALIB_MIN_RECORDS = 20`,
  `CALIB_FLOOR = 0.60`).
- **Tendance** : l'historique est découpé en 2 à 8 tranches chronologiques
  (5 enregistrements minimum par tranche) ; comparaison du Brier de la 1ʳᵉ
  moitié vs la 2ᵉ moitié (`amélioration` si delta < −0.02, `dégradation` si
  > +0.02, sinon `stable`).

### 5.8 Préparation globale (readiness)

`brute = Σ (maîtrise_d × poids_d)` ; `confiance_données = min(1, tentatives/80)` ;
`préparation = brute × confiance_données × facteur_calibration` (facteur = 1.0
si la calibration est désactivée).

---

## 6. API de l'agent IA compagnon (`dof-prep-agent.py`)

Serveur HTTP local (`http.server.ThreadingHTTPServer`), CORS réfléchissant
l'origine de la requête (`Access-Control-Allow-Origin: <Origin>`), bind par
défaut sur `127.0.0.1:8799`.

| Méthode | Route | Corps | Réponse |
|---|---|---|---|
| GET | `/health` | — | `{"ok": true, "has_key": bool, "model": "..."}` |
| GET | `/` | — | Description sommaire + liste des endpoints |
| POST | `/analyze` | `{"mastery": {...}, "weak_domains": [...], "readiness": 0.x, "target": 0.x}` | `{"analysis": "texte 120-200 mots"}` |
| POST | `/generate-questions` | `{"domain": "DOFD-x", "count": 1-10, "level": "moyen\|difficile\|tres_difficile", "avoid_statements": [...]}` | `{"questions": [...], "count": n}` |

Erreurs : toute erreur contrôlée (clé absente, domaine invalide, réponse
modèle non conforme) renvoie un JSON `{"error": "message clair"}` avec un
code HTTP explicite (400, 404, 502) — jamais de page d'erreur opaque, jamais
de crash serveur (filet `except Exception` en dernier recours → 500 avec
message).

Validation stricte des questions générées (`validate_question`) avant tout
retour au client : domaine reconnu, `k_level` 1–7, `difficulty` 1–5, type
valide, règle de comptage des bonnes réponses par type (section 5 des specs
fonctionnelles), translittération automatique des accents vers ASCII pur
(cohérence avec la convention « banque sans accents » du projet, quel que
soit ce que le modèle a produit).

---

## 7. Environnement d'exécution et stratégie de test

| Composant | Requiert |
|---|---|
| Application Python | Python 3.10+ (validé sur 3.12), bibliothèque standard uniquement |
| Build web (PWA/standalone) | Aucune dépendance runtime ; navigateur moderne (ES2017+, `fetch`, `localStorage`) |
| Agent IA | Python 3.10+, bibliothèque standard uniquement, clé API Anthropic |
| Suite de tests (dev uniquement) | Node.js 18+ (validé sur v22), paquet `jsdom` |

Suites de vérification (internes, non livrées avec l'application) :

| Suite | Portée | Résultat |
|---|---|---|
| `engine.test.js` | Parité moteur JS ↔ Python : distribution, quotas, recouvrement nul, reproductibilité, correction, EMA, SM-2, Elo, calibration, readiness | 41/41 |
| `ui.smoke.js` | Parcours fonctionnel headless (jsdom) : rendu, examen complet, score, persistance ; dégradation propre sans agent ; détection réelle de l'agent (process réel lancé sans clé) et remontée d'erreur jusqu'à l'UI | 20/20 |
| `agent_unit_test.py` | Fonctions pures de l'agent (sans réseau) : translittération, extraction JSON tolérante, validation de question | 18/18 |
| *(historique)* `test_client.py` (application Python) | Logique métier côté serveur Python | 74/74 *(établi lors de la construction initiale ; non ré-exécuté dans cette session)* |

Non couvert par une vérification automatisée : le contenu réel renvoyé par
l'API Anthropic (nécessiterait une vraie clé et une dépense réelle) — seul le
**format** de la réponse est strictement validé côté agent avant transmission
à l'interface.

---

## 8. Sécurité, vie privée et limitations connues

- **Vie privée par défaut** : aucune donnée ne quitte l'appareil tant que
  l'agent IA n'est pas explicitement sollicité. Les seules données envoyées à
  l'agent (et par lui à l'API Anthropic) sont des pourcentages de maîtrise
  agrégés par domaine et, pour la génération, des énoncés déjà présents dans
  la banque (contenu pédagogique, non personnel).
- **Clé API** : jamais transmise au navigateur ; lue uniquement côté serveur
  agent depuis une variable d'environnement.
- **CORS de l'agent** : réfléchit l'origine de la requête pour fonctionner
  aussi bien depuis un fichier ouvert en `file://` que depuis une PWA servie
  en `http://`. L'agent n'écoutant que sur `127.0.0.1` par défaut, ce choix
  est sans risque tant que `DOF_AGENT_HOST` n'est pas changé pour exposer le
  service sur le réseau local.
- **PRNG du moteur web** (`mulberry32`) : déterministe et reproductible, mais
  **algorithmiquement distinct** du Mersenne Twister de CPython. Les deux
  moteurs garantissent les **mêmes invariants** (pondération exacte,
  recouvrement nul, reproductibilité) mais ne tirent pas les mêmes questions
  pour une graine « équivalente » — il n'y a pas d'équivalence bit-à-bit
  attendue ni recherchée entre les deux implémentations.
- **`localStorage` en `file://`** : certains navigateurs restreignent ou
  isolent le stockage local pour les pages ouvertes directement depuis le
  disque (fichier standalone), en particulier sur mobile. La PWA, servie
  depuis une origine HTTP(S) stable, n'a pas cette limite.
- **Service worker en `file://`** : ne s'exécute pas dans ce contexte, d'où
  la nécessité de servir la PWA au moins une fois en HTTP(S) (voir
  `INSTALLATION.md`).
