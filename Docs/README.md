# DOF-PREP — Préparation à la certification DevOps Foundation (DOFD v3.4)

Application autoportée d'entraînement à l'examen **DevOps Foundation** (DevOps Institute, référentiel DOFD v3.4) : examens blancs générés selon la pondération officielle des 8 domaines, entraînement ciblé par domaine, révision espacée, tableau de bord de préparation et **curseur de cible réglable de 65 % à 90 %**.

## Choix d'architecture : zéro dépendance

L'application repose **uniquement sur la bibliothèque standard de Python 3** (`http.server`, `sqlite3`, `json`, `hashlib`…). Aucun `pip install`, aucun `npm`, aucun framework. C'est l'« Option B » prévue par le cahier des charges, retenue ici parce que c'est la seule façon de tenir ensemble *livraison par installeur, fonctionnement hors-ligne et portabilité totale sur les trois plateformes* : un déploiement Django/Vue exigerait l'installation de paquets et donc un accès réseau, en contradiction avec ces exigences.

- Backend : serveur HTTP de la stdlib + persistance **SQLite**.
- Frontend : application monopage (HTML/CSS/JS « vanilla ») **embarquée** dans le fichier Python, servie telle quelle — pas d'étape de build, pas de police distante (compatible hors-ligne).
- Le même fichier `devops_foundation_prep.py` est embarqué **à l'identique** (vérifié par empreinte SHA-256) dans les trois installeurs.

## Pré-requis

**Python 3.8 ou plus** sur la machine (Linux/macOS/Windows). Pour la version Docker : seulement **Docker** (Python est fourni par l'image).

## Installation et lancement

Les trois installeurs sont au **format heredoc** : ils écrivent eux-mêmes les fichiers, puis se lancent simplement.

### 1) Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
cd devops-foundation-prep
.\start.bat
```

### 2) Linux / macOS (bash)

```bash
bash install.sh
cd devops-foundation-prep
./start.sh
```

### 3) Docker

```bash
bash install-docker.sh
cd devops-foundation-prep-docker
docker compose up --build -d
```

Sans `docker compose` :

```bash
docker build -t dof-prep .
docker run -d -p 8765:8765 -v dofprep-data:/app/data dof-prep
```

Dans tous les cas, ouvrir ensuite **http://localhost:8765/** (en local, le navigateur s'ouvre automatiquement).

## Configuration (variables d'environnement)

| Variable | Rôle | Défaut |
|---|---|---|
| `DOF_HOST` | hôte d'écoute | `127.0.0.1` (Docker : `0.0.0.0`) |
| `DOF_PORT` | port HTTP | `8765` |
| `DOF_DB_PATH` | chemin de la base SQLite | `./dofprep.sqlite3` (Docker : `/app/data/dofprep.sqlite3`) |
| `DOF_OPEN_BROWSER` | ouvrir le navigateur au démarrage | `1` (Docker : `0`) |
| `DOF_SECOND_ORDER` | activer par défaut la couche de second ordre (calibration métacognitive) | `0` |
| `DOF_ELO_K` | gain de la boucle réflexive (mise à jour mutuelle aptitude ↔ difficulté latente), borné `[0,1]` | `0.08` |
| `DOF_CALIB_MIN_RECORDS` | nombre minimal de prédictions de confiance avant que la calibration n'influe sur la préparation (anti‑oscillation), entier ≥ 1 | `20` |
| `DOF_CALIB_FLOOR` | plancher du facteur de calibration (la préparation peut être amortie, jamais effondrée ; le seuil officiel 65 % n'est jamais abaissé), borné `[0,1]` | `0.60` |

Toutes ces variables sont **optionnelles** et documentées dans **`.env.example`** (fourni). Sous Linux/macOS, `start.sh` **charge automatiquement** un fichier `.env` présent à côté : `cp .env.example .env`, puis décommentez/ajustez. Les bornes de sûreté sont appliquées au démarrage (valeurs hors plage ramenées dans l'intervalle).

En Docker, la base est conservée dans le volume `dofprep-data` (la progression survit aux redémarrages) ; les paramètres du second ordre se règlent via le bloc `environment` (commenté) du `docker-compose.yml`.

## Fonctionnalités

- **Examen blanc** : 40 questions, 60 minutes (minuteur avec soumission automatique), seuil 65 %, **sans pénalité**. Génération dynamique respectant la pondération des 8 domaines. Correction détaillée par domaine, avec explication pour chaque question.
- **Génération par niveau de difficulté** : chaque examen peut être tiré en niveau **Moyen**, **Difficile** ou **Très difficile**. Le niveau biaise la difficulté des questions ; **la pondération par domaine reste toujours exacte** (repli automatique sur les autres difficultés du domaine si nécessaire).
- **12 examens blancs prêts à l'emploi**, classés par niveau (4 Moyen, 4 Difficile, 4 Très difficile). Chacun est **reproductible** (tirage déterministe : même composition à chaque lancement). Au sein d'un même niveau, les 4 examens se **partagent les questions sans répétition** (distribution « par donne ») : **recouvrement nul** entre eux, pour un entraînement réellement varié.
- **Curseur de cible (65 % → 90 %)** sur le tableau de bord : règle l'objectif de préparation, persisté par utilisateur. L'indicateur « prêt pour l'examen » se déclenche quand la préparation globale atteint la cible **et** qu'aucun domaine n'est sous 65 %.
- **Entraînement ciblé** par domaine, avec correction immédiate et explication.
- **Révision espacée** (algorithme SM-2) : file « à revoir » alimentée par les réponses.
- **Tableau de bord** : jauge de préparation, maîtrise par domaine, recommandations automatiques (domaines faibles, prochaines actions).
- **Couche de second ordre (optionnelle, activable)** — *cybernétique des systèmes observants* : le système observe sa propre observation. Une **invite de confiance** accompagne chaque question (examen blanc et entraînement) ; un **tableau de bord de calibration** confronte confiance prédite et réussite réelle (**score de Brier**, biais sur/sous‑confiance, ECE, **courbe de fiabilité**, détail par domaine) et trace la **tendance temporelle du Brier** (la calibration s'améliore‑t‑elle au fil des sessions ?). L'**auto‑calibration** ajuste la difficulté *latente* des items (la difficulté éditoriale 1–5 reste intacte) et module le **facteur de confiance** de la préparation — avec garde‑fous (seuil minimal de prédictions, plancher, seuil officiel 65 % jamais abaissé) et **préparation brute toujours affichée** à côté. Paramètres pilotables par variables d'environnement (voir `.env.example`).
- **Banque de 315 questions originales en français**, classées par section d'apprentissage (DOFD-1 à DOFD-8) et par niveau cognitif **K1 à K7** (de la restitution à la synthèse), avec des difficultés de 1 à 5 et des types variés (choix unique, choix multiple, vrai/faux). Couverture : CALMS, les Trois Voies, théorie des contraintes, loi de Little, Lean/Kaizen/DOWNTIME, Scrum/Kanban/SAFe, ITIL/ITSM, CI/CD et déploiement continu, Blue-Green/canari, TDD, SLI/SLO/SLA/error budget, observabilité, DevSecOps, chaos engineering, conteneurs/Kubernetes/microservices, IaC/idempotence/immuabilité, chaînes d'outils, DORA/MTBF/MTTR, Westrum, loi de Conway (et manœuvre inverse), team topologies, Kübler-Ross, modèle Spotify, guildes, ChatOps, inner source, dojo…

## API (extraits)

| Méthode | Endpoint | Rôle |
|---|---|---|
| GET | `/api/v1/bootstrap` | utilisateur, certification, domaines |
| GET | `/api/v1/dashboard` | préparation, maîtrise, recommandations |
| POST | `/api/v1/exams/generate` | génère un examen pondéré ; accepte `level` (`moyen`/`difficile`/`tres_difficile`) ou `preset_id` (1–12) |
| GET | `/api/v1/exams/presets` | liste les 12 examens blancs (id, niveau, libellé) |
| POST | `/api/v1/exams/sessions/{id}/submit` | corrige et renvoie le détail |
| POST | `/api/v1/training/start` · `/training/answer` | entraînement ciblé |
| GET | `/api/v1/review/due` | cartes de révision dues |
| PATCH | `/api/v1/me/preferences` | règle la cible (65–90 %, sinon 422) |

## Périmètre (MVP) et extensions prévues

Cette version couvre le cœur fonctionnel et est entièrement opérationnelle. Sont volontairement **simplifiés / à étendre** (cohérent avec le découpage en lots du cahier des charges) :

- **Mono-utilisateur local** : un profil « apprenant » par défaut, sans authentification ni RBAC (l'outil est conçu pour un usage local). Le multi-utilisateur et les rôles admin/reviewer sont des extensions naturelles (les tables le permettent déjà).
- **Niveaux cognitifs supérieurs (K5–K7)** : présents dans la banque sous forme de questions d'analyse, d'évaluation et de synthèse (utiles au sur-apprentissage), mais **pas** sous forme de modules interactifs dédiés (simulations guidées, projet libre avec grille) — extension naturelle pour une version ultérieure.
- **Mode connecté** (liens externes, mises à jour de contenu) : non activé (l'application est hors-ligne par conception).
- **Pondérations des domaines** : valeurs **officielles** du blueprint DevOps Institute (document *DevOps Foundation Examination Requirements*), exprimées en nombre maximal de questions par domaine sur 40 (somme = 40) :

| Domaine | Intitulé | Questions /40 |
|---|---|---|
| DOFD-1 | Explorer le DevOps | 5 |
| DOFD-2 | Principes fondamentaux (les Trois Voies) | 4 |
| DOFD-3 | Pratiques clés | 7 |
| DOFD-4 | Cadres métier et techniques | 7 |
| DOFD-5 | Culture, comportements et modèles opérationnels | 6 |
| DOFD-6 | Automatisation et architecture des chaînes d'outils | 5 |
| DOFD-7 | Mesure, métriques et reporting | 2 |
| DOFD-8 | Partage, accompagnement et évolution | 4 |

Ces valeurs sont issues du document v3.3 (les nombres définissent la composition exacte de l'examen). Si une révision v3.4 publie des nombres différents, un seul tableau `DOMAINS` en tête du fichier est à ajuster.

## Note pédagogique

Le seuil officiel de réussite est **65 %**. La cible par défaut (**90 %**) est un objectif d'entraînement créant une marge de sécurité ; elle se règle librement entre 65 % et 90 % via le curseur.

**À propos des niveaux K1–K7 et des examens « Difficile / Très difficile »** : l'examen DevOps Foundation réel ne porte que sur les niveaux cognitifs **K1–K2** (mémorisation et compréhension). Les questions de niveaux **K3 à K7** (application, analyse, évaluation, synthèse) et les examens blancs **Difficile** et **Très difficile** vont donc **au-delà** du niveau attendu : ils servent au sur-apprentissage et à consolider une marge confortable. Pour des conditions au plus proche de l'examen réel, privilégier les examens **Moyen**. Le contenu est original et destiné à l'entraînement ; il ne reproduit pas les ouvrages de référence.
