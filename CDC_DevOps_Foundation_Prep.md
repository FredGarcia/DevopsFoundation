# Cahier des charges

## Plateforme de préparation à la certification *DevOps Foundation*

**Nom de code projet :** `DOF-PREP`
**Type de document :** Cahier des charges fonctionnel et technique (CDCF/T)
**Public visé par le document :** équipe de développement, direction technique, commanditaire

---

### Métadonnées du document

| Champ | Valeur |
|---|---|
| Référence | CDC-DOFPREP-001 |
| Version | 1.0 |
| Statut | Pour validation |
| Date | À compléter |
| Auteur | Architecture logicielle DevOps |
| Destinataires | Équipe projet, commanditaire |
| Confidentialité | Interne |

### Historique des révisions

| Version | Date | Auteur | Description |
|---|---|---|---|
| 0.1 | — | — | Trame initiale |
| 1.0 | — | — | Première version complète pour validation |

### Conventions de rédaction

- **DOIT / NE DOIT PAS** : exigence impérative (bloquante pour la recette).
- **DEVRAIT** : exigence forte, dérogation possible sur justification.
- **PEUT** : exigence optionnelle / souhaitable.
- Toute exigence est identifiée par un code (`EF-xx` fonctionnelle, `ENF-xx` non fonctionnelle) pour traçabilité.

---

## 1. Présentation et contexte

### 1.1 Contexte

Une équipe doit obtenir la certification **DevOps Foundation** (DevOps Institute, référentiel **DOFD v3.4**). Cette certification est exigée par un client final comme condition de validation d'une prestation. L'objectif n'est donc pas seulement individuel : il s'agit d'un **enjeu contractuel collectif**.

La présente application vise à industrialiser et fiabiliser la préparation de l'équipe : couverture complète du programme, entraînement mesurable, détection des lacunes et pilotage de la progression jusqu'à un niveau de préparation élevé.

### 1.2 Enjeu et objectif de réussite

| Élément | Valeur de référence (examen réel) | Objectif interne de la plateforme |
|---|---|---|
| Nombre de questions | 40 | — |
| Durée | 60 minutes | — |
| Seuil de réussite officiel | **65 %** (26/40) | — |
| Pénalité de mauvaise réponse | Aucune | — |
| Format | Livre ouvert (open book) | Reproduit en mode examen |
| Domaines pondérés | 8 (DOFD-1 → DOFD-8) | Respectés à l'identique |
| **Cible de réussite** | — | **Curseur réglable de 65 % à 90 %** (défaut 90 %) |

> **Note d'honnêteté pédagogique.** Le seuil officiel de réussite est de **65 %**. La cible demandée par le commanditaire (**90 %**) est un **objectif d'entraînement** : viser plus haut que le seuil crée une **marge de sécurité** pour franchir l'examen réel sous stress. La plateforme expose donc un **curseur de cible de réussite réglable de 65 % à 90 %** — le bas du curseur correspond au seuil officiel, le haut à l'objectif de confiance. Le moteur de préparation, le signal « prêt pour l'examen » et les tableaux de bord se calent sur la valeur choisie.

### 1.3 Vision produit

Une **plateforme web autoportée**, exécutable hors-ligne, multi-plateforme (Windows / Linux / Docker), combinant :

- un référentiel de contenu pédagogique aligné sur le programme officiel ;
- un moteur d'entraînement adaptatif et auto-correctif ;
- un pilotage de la progression par compétences (niveaux K0 à K6) ;
- un mode de préparation intensive ciblant la cible de confiance.

### 1.4 Parties prenantes

| Rôle | Responsabilité |
|---|---|
| Commanditaire | Définit l'enjeu, valide la recette |
| Référent pédagogique | Garant de l'alignement au syllabus officiel |
| Apprenants (équipe) | Utilisateurs finaux |
| Administrateur | Gère le contenu, les utilisateurs, l'import/export |
| Équipe de développement | Conçoit, réalise, déploie, maintient |

---

## 2. Objectifs

### 2.1 Objectifs pédagogiques

- **OP-1** — Couvrir l'intégralité des 8 domaines du référentiel DOFD v3.4.
- **OP-2** — Faire progresser chaque apprenant à travers les niveaux cognitifs K0 → K6.
- **OP-3** — Détecter et corriger les lacunes individuelles de façon ciblée.
- **OP-4** — Reproduire fidèlement les conditions de l'examen (format, durée, pondération, absence de pénalité).
- **OP-5** — Amener chaque apprenant à un niveau de préparation ≥ 90 % en examen blanc avant le passage réel.

### 2.2 Objectifs fonctionnels

- **OF-1** — Offrir plusieurs modalités d'apprentissage (théorie, flashcards, quiz, examens blancs, études de cas, simulations, révision espacée).
- **OF-2** — Générer dynamiquement des examens respectant la pondération officielle des domaines.
- **OF-3** — Évaluer, noter et expliquer chaque réponse.
- **OF-4** — Piloter la progression individuelle et collective via des tableaux de bord.
- **OF-5** — Permettre l'enrichissement du contenu (import/export de questions).
- **OF-6** — Fonctionner hors-ligne, avec un mode connecté optionnel.

### 2.3 Critères de succès mesurables (KPI)

| KPI | Cible |
|---|---|
| Couverture des 8 domaines | 100 % |
| Génération d'examen respectant la pondération | écart ≤ 1 question par domaine |
| Taux de réussite moyen de l'équipe en blancs finaux | ≥ 90 % |
| Disponibilité hors-ligne | 100 % des fonctions cœur sans réseau |
| Démarrage sur Windows / Linux / Docker | 3/3 plateformes |
| Round-trip import → export de questions | sans perte ni divergence |

### 2.4 Périmètre

**Inclus :**
- Application web complète (frontend + backend + base).
- Contenu pédagogique initial et banque de questions.
- Moteur adaptatif, modes d'entraînement, mode expert intensif.
- Outils d'administration et d'import/export.
- Trois cibles de déploiement (Windows, Linux, Docker) avec scripts.

**Exclu (sauf évolution ultérieure) :**
- Hébergement SaaS multi-tenant à grande échelle.
- Authentification fédérée d'entreprise (SSO/LDAP) — *prévu en extensibilité*.
- Application mobile native.
- Reproduction de tout contenu sous droit d'auteur (voir §14.3).

---

## 3. Cadre pédagogique

### 3.1 Référentiel de certification (DOFD v3.4)

Les 8 domaines structurent l'ensemble du contenu et le moteur d'examen. Les pondérations ci-dessous sont les **valeurs officielles** du blueprint DevOps Institute (document *DevOps Foundation Examination Requirements*, rubrique « Exam Topic Areas and Question Weighting »), exprimées en **nombre maximal de questions par domaine sur 40** (somme = 40, soit 100 %) :

| Code | Domaine (intitulé officiel) | Questions /40 | Pondération |
|---|---|---|---|
| DOFD-1 | Explorer le DevOps | 5 | 12,5 % |
| DOFD-2 | Principes fondamentaux (les Trois Voies) | 4 | 10,0 % |
| DOFD-3 | Pratiques clés (CALMS, CI/CD, pipeline, SRE, observabilité) | 7 | 17,5 % |
| DOFD-4 | Cadres métier et techniques (Agile, Lean, ITSM, SAFe) | 7 | 17,5 % |
| DOFD-5 | Valeurs DevOps : culture, comportements et modèles opérationnels | 6 | 15,0 % |
| DOFD-6 | Valeurs DevOps : automatisation et architecture des chaînes d'outils | 5 | 12,5 % |
| DOFD-7 | Valeurs DevOps : mesure, métriques et reporting (DORA) | 2 | 5,0 % |
| DOFD-8 | Valeurs DevOps : partage, accompagnement et évolution | 4 | 10,0 % |
| **Total** | | **40** | **100 %** |

> Source : les valeurs proviennent du document officiel **v3.3** (le seul blueprint chiffré publiquement disponible) ; ces nombres définissent la composition exacte de l'examen et sont selon toute vraisemblance inchangés en v3.4. Le référent pédagogique **CONFIRMERA** sur le syllabus v3.4 détenu par le commanditaire ; toute différence se corrige par simple paramétrage (voir ci-dessous).

> La pondération **DOIT** être stockée en base (table `domain`) et non codée en dur, afin de coller à la version officielle et de supporter d'autres certifications (voir §9).

### 3.2 Taxonomie des compétences K0–K6

La progression s'appuie sur une taxonomie cognitive (inspirée de la taxonomie de Bloom révisée). Chaque question, activité et objectif est rattaché à un niveau.

| Niveau | Intitulé | Verbe d'action | Type d'évaluation privilégié |
|---|---|---|---|
| **K0** | Exposition / prise de conscience | Découvrir, reconnaître | Flashcards, lecture, repérage |
| **K1** | Comprendre | Expliquer, reformuler | QCM de définition, vrai/faux |
| **K2** | Appliquer | Utiliser, mettre en œuvre | QCM situationnels, mini-exercices |
| **K3** | Analyser | Décomposer, comparer | Études de cas, scénarios |
| **K4** | Évaluer | Juger, prioriser, critiquer | Scénarios d'arbitrage, justification |
| **K5** | Synthétiser | Concevoir une combinaison, intégrer | Simulations, construction de pipeline |
| **K6** | Créer | Produire une solution nouvelle | Projet de simulation DevOps complet |

> **Note de cadrage.** L'examen *DevOps Foundation* évalue majoritairement les niveaux **K1–K2** (compréhension/application), avec quelques items K3. Les niveaux **K4–K6 sont des leviers de sur-apprentissage** : ils consolident la maîtrise au-delà de l'examen et soutiennent l'atteinte d'une cible élevée (jusqu'à 90 %, selon le réglage du curseur), sans être directement représentatifs du format réel. La plateforme **DOIT** distinguer clairement les activités « représentatives examen » des activités « approfondissement ».

> **Note d'implémentation (échelle K1–K7).** La banque livrée encode le niveau cognitif sur une **échelle 1-indexée K1 à K7**, plus fine que la table conceptuelle ci-dessus, afin de graduer le sur-apprentissage : **K1** Se souvenir, **K2** Comprendre, **K3** Appliquer, **K4** Analyser, **K5** Évaluer, **K6** Créer/concevoir, **K7** Synthèse experte (intégration de plusieurs concepts dans un scénario, nettement au-delà du format réel). La correspondance avec la taxonomie conceptuelle est directe (le K0 « exposition » est couvert par les fiches et flashcards). **L'examen réel restant borné à K1–K2**, les niveaux **K3–K7 et les examens « Difficile »/« Très difficile » sont explicitement du sur-apprentissage** ; pour des conditions proches du réel, on privilégie le niveau **Moyen**.

### 3.3 Sources pédagogiques de référence

Le contenu s'inspire des ouvrages suivants (références conceptuelles) :

- *DevOps Foundation Course Learner Manual* — DevOps Institute (référentiel principal).
- *The Phoenix Project* — Gene Kim, Kevin Behr, George Spafford (les 3 voies, types de travail, théorie des contraintes).
- *The DevOps Handbook* — Gene Kim, Jez Humble, Patrick Debois, John Willis (mise en pratique des 3 voies, CI/CD, télémétrie).
- *Scrum et XP depuis les tranchées* — Henrik Kniberg (Scrum, XP, intégration continue, rétrospectives).

> **Exigence légale (voir aussi §14.3).** Ces ouvrages servent de **sources d'inspiration conceptuelle**. L'application **NE DOIT PAS** reproduire de texte verbatim (extraits, paragraphes, questions originales des éditeurs). Tout contenu (questions, fiches, explications) **DOIT être rédigé de façon originale** et, lorsque pertinent, **citer la source** (« concept abordé dans *The DevOps Handbook* »).

### 3.4 Socle conceptuel à couvrir obligatoirement

Le contenu **DOIT** couvrir au minimum :

- **CALMS** : Culture, Automation, Lean, Measurement, Sharing.
- **The Three Ways** : Flux (Flow), Rétroaction (Feedback), Apprentissage et expérimentation continus.
- **Métriques DORA** : fréquence de déploiement, délai des changements (lead time), taux d'échec des changements, temps de rétablissement (MTTR), et fiabilité.
- **Théorie des contraintes** et **Value Stream Mapping**.
- **Quatre types de travail** (Phoenix Project) : projets métier, projets internes, changements, travail non planifié.
- **Lean / Kaizen / Kata**, **Agile / Scrum / XP**, **ITSM**, **SRE**, **observabilité** (logs, métriques, traces).
- **Chaînes d'outils** : IaC, gestion de configuration, conteneurs, orchestration, cloud, CI/CD.

### 3.5 Dispositif de cadrage propriétaire « axiome 7E » *(optionnel, non évalué)*

Le commanditaire souhaite intégrer un axiome de cadrage propriétaire dit **« axiome 7E »** :

> « *Les **É**léments dans l'**E**space **E**ngendrent un **É**tat d'**E**xpression **É**volutif de l'**E**nvironnement.* »

**Statut et recommandation d'usage :**
- Cet axiome est un **dispositif mnémotechnique et de marque** propre au projet. Il **ne fait pas partie** du référentiel officiel du DevOps Institute et **n'apparaîtra pas** à l'examen réel.
- Il **PEUT** être employé comme **fil narratif / identité de la plateforme** : écran d'accueil, nom des jalons de progression, éléments de gamification, transitions entre modules.
- Il **NE DOIT PAS** se substituer aux concepts officiellement évalués (CALMS, The Three Ways, métriques DORA, etc.), ni apparaître dans l'énoncé ou la correction des QCM représentatifs de l'examen.
- Suggestion d'ancrage cohérent : associer chaque « E » à un pilier réel pour donner du sens (p. ex. **E**nvironnement ↔ Culture, **E**xpression ↔ Sharing, **É**volutif ↔ Continual Learning…), tout en gardant la primauté des cadres officiels.

> En clair : l'axiome 7E sert l'**engagement et la cohérence de marque**, jamais la **validité d'examen**. Le moteur de questions reste strictement aligné sur le syllabus.

---

## 4. Exigences fonctionnelles

### 4.1 Modules pédagogiques

| Code | Module | Description | Niveaux K visés |
|---|---|---|---|
| EF-01 | Théorie | Fiches de cours par domaine, navigables hors-ligne | K0–K1 |
| EF-02 | Flashcards | Recto/verso, intégrées à la révision espacée | K0–K1 |
| EF-03 | Quiz | Séries courtes par domaine/niveau, correction immédiate | K1–K2 |
| EF-04 | Examens blancs | Génération dynamique au format officiel (40 Q / 60 min), **par niveau de difficulté** (Moyen / Difficile / Très difficile) et **12 examens blancs prédéfinis et reproductibles** classés par niveau, à **recouvrement nul** au sein d'un même niveau (voir EF-04b) | K1–K7 |
| EF-05 | Études de cas | Mises en situation longues avec questions liées | K3–K4 |
| EF-06 | Scénarios d'analyse | Arbitrages, priorisation, justification | K4 |
| EF-07 | Exercices pratiques | Manipulations guidées (pipeline, métriques…) | K2–K5 |
| EF-08 | Simulations DevOps | Construction d'une chaîne, choix d'outils, conséquences | K5–K6 |
| EF-09 | Révision espacée | File de cartes « à revoir » (algorithme SM-2) | tous |
| EF-10 | Suivi des faiblesses | Identification des domaines/topics fragiles | tous |

Chaque module **DOIT** : enregistrer l'activité de l'utilisateur, alimenter le suivi de progression et fournir des explications après réponse.

**EF-04b — Examens blancs : niveaux de difficulté, examens prédéfinis et anti-recouvrement.**
- La génération d'examen **DOIT** accepter un **niveau de difficulté** optionnel — **Moyen** (difficultés 2–3), **Difficile** (3–4), **Très difficile** (4–5) — qui biaise la difficulté des questions tirées. Quel que soit le niveau, la **pondération officielle par domaine reste exacte** (repli automatique sur les autres difficultés du domaine si le vivier d'une bande est insuffisant). Un mode **Expert intensif** (priorité aux questions les plus difficiles, tous niveaux) reste disponible.
- La plateforme **DOIT** proposer **12 examens blancs prédéfinis**, classés par niveau (4 Moyen, 4 Difficile, 4 Très difficile). Chaque examen est **reproductible** : tirage **déterministe** (graine fixe) produisant la même composition à chaque lancement, afin de permettre de refaire un examen et de mesurer sa progression.
- Au sein d'un même niveau, les examens prédéfinis **DOIVENT** se **partager les questions sans répétition** (distribution « par donne ») : le **recouvrement entre deux examens d'un même niveau doit être nul** tant que le vivier le permet (condition vérifiée : viviers par domaine ≥ 4 × quota). La difficulté **DOIT** rester équilibrée entre les examens d'un même niveau (répartition en alternance des questions de la bande).

### 4.2 Implémentation des niveaux K0 à K6

Pour **chaque** niveau, la plateforme **DOIT** définir : types d'activités, logique d'évaluation, critères de validation, scoring et règle de progression.

| Niveau | Activités | Évaluation | Critère de validation | Scoring | Progression vers K+1 |
|---|---|---|---|---|---|
| K0 | Lecture, flashcards de reconnaissance | Auto-déclaratif + reconnaissance | ≥ 80 % des cartes vues | Binaire (vu/non vu) | Toutes cartes du domaine vues |
| K1 | QCM de définition, vrai/faux | Correction automatique | ≥ 75 % de bonnes réponses sur 20 items | % de réussite | Seuil atteint 2 sessions de suite |
| K2 | QCM situationnels, mini-exercices | Correction automatique pondérée par difficulté | ≥ 75 % pondéré | Score pondéré difficulté | Seuil + stabilité |
| K3 | Études de cas (questions liées) | Auto + grille de critères | ≥ 70 % des questions de cas | Score par critère | 3 cas réussis |
| K4 | Scénarios d'arbitrage | Choix + justification (grille) | Justification conforme à la grille | Rubrique multicritère | 3 scénarios validés |
| K5 | Simulation guidée | Vérification des étapes/règles | Pipeline cohérent produit | Checklist de conformité | 1 simulation complète validée |
| K6 | Projet de simulation libre | Revue par grille (auto + admin optionnel) | Solution cohérente et justifiée | Rubrique projet | Validation finale |

**Règles transverses :**
- Un niveau **NE DOIT PAS** être marqué « maîtrisé » sur une seule réussite : exiger une **stabilité** (≥ 2 sessions au-dessus du seuil) pour limiter l'effet de chance.
- Le scoring **DOIT** pondérer la difficulté de chaque item.
- La progression d'un domaine est l'agrégat de ses niveaux atteints.

### 4.3 Moteur intelligent de préparation

- **EF-11 — Détection des lacunes.** À partir de l'historique, identifier les domaines/topics où le taux d'erreur dépasse un seuil paramétrable.
- **EF-12 — Révisions ciblées.** Générer automatiquement des sessions concentrées sur les lacunes détectées.
- **EF-13 — Difficulté adaptative.** Ajuster la difficulté des items en fonction des performances récentes (voir pseudo-code §7.4).
- **EF-14 — Probabilité de réussite.** Calculer un indicateur de préparation (0–100 %) par domaine et global, pondéré comme l'examen réel.
- **EF-15 — Cible de réussite réglable (curseur).** Exposer côté front un **curseur** réglant la cible de réussite de **65 % (seuil officiel) à 90 % (objectif de confiance)**, pas de 1 %, avec repères visuels aux deux bornes. La valeur est **persistée par utilisateur** (défaut 90 %) ; l'administrateur **PEUT** définir une cible par défaut d'équipe. Tous les indicateurs de préparation (probabilité, signal « prêt », tableaux de bord) se calent sur cette valeur. Le curseur **NE DOIT PAS** descendre sous 65 % (le seuil officiel reste le plancher) ni dépasser 90 %.
- **EF-16 — Tableaux de bord.** Visualiser progression, lacunes, tendance et estimation de préparation.
- **EF-17 — Auto-amélioration (rétro-observateur).** Le moteur **DOIT** réviser ses estimations à chaque nouvelle donnée (recalcul des scores, ré-ordonnancement de la file de révision) et **DEVRAIT** ajuster la difficulté d'un item en fonction de son taux de réussite réel observé (item trop facile/difficile signalé à l'admin). **Extension de second ordre (optionnelle, voir EF-17b) :** le moteur entretient une **difficulté latente** par item, mise à jour conjointement avec une **aptitude latente** de l'apprenant (mise à jour mutuelle de type Elo/Rasch léger). La difficulté **éditoriale** (1–5), qui pilote les bandes et le recouvrement nul des examens blancs, **reste inchangée** : seule la difficulté **observée** évolue (reporting et facteur de confiance). Le gain est **amorti** et la difficulté latente **bornée** pour éviter les à-coups.

- **EF-17b — Boucle réflexive et métacognition (cybernétique de second ordre, OPTIONNELLE).** La plateforme **DOIT** pouvoir être **activée/désactivée** (préférence par utilisateur, défaut configurable par variable d'environnement ; désactivée par défaut). Lorsqu'elle est active :
  - **Invite de confiance.** Avant validation, l'apprenant **PEUT** déclarer sa **confiance** (probabilité de réussite) sur chaque item d'examen blanc et d'entraînement ; le couple (confiance prédite, résultat réel) est journalisé.
  - **Tableau de bord de calibration.** La plateforme **DOIT** présenter la qualité de calibration : **score de Brier**, **biais signé** (sur/sous-confiance), **erreur de calibration** (ECE), **courbe de fiabilité** par tranches (prédit vs réel), détail **par domaine**, et la **tendance temporelle du score de Brier** (découpage chronologique des prédictions en tranches successives + verdict amélioration / dégradation / stable) — pour montrer si la calibration progresse au fil des sessions.
  - **Auto-calibration de la préparation.** Le **facteur de confiance** de l'indicateur de préparation **DOIT** intégrer la qualité de calibration : une mauvaise calibration **amortit** la préparation affichée. Cet ajustement **NE DOIT** s'appliquer **qu'au-delà d'un nombre minimal de prédictions** (anti-oscillation), **rester borné par un plancher**, et **NE JAMAIS** abaisser le **seuil officiel de 65 %**. La **préparation brute** (sans calibration) **DOIT** rester affichée à côté de la préparation calibrée.
  - **Garde-fous.** La boucle réflexive (un régulateur qui règle un régulateur) **DOIT** être amortie et plafonnée pour éviter divergence ou oscillation ; ses paramètres — **gain** (`DOF_ELO_K`), **seuil minimal de prédictions** (`DOF_CALIB_MIN_RECORDS`), **plancher** (`DOF_CALIB_FLOOR`) — sont **centralisés, pilotables par variables d'environnement** (bornes de sûreté appliquées au démarrage) et **documentés dans `.env.example`**.

### 4.4 Gestion des utilisateurs et des rôles

- **EF-18** — Trois rôles minimum : `apprenant`, `administrateur`, `référent` (lecture étendue des statistiques).
- **EF-19** — Authentification locale (identifiant + mot de passe haché).
- **EF-20** — Profil utilisateur : préférences, langue (français par défaut), historique.
- **EF-21** — Vue d'équipe pour l'administrateur/référent : progression agrégée et par personne.

### 4.5 Suivi de progression et historique

- **EF-22** — Historiser chaque tentative (item, réponse, exactitude, temps passé, date).
- **EF-23** — Conserver l'historique des examens blancs (score, détail par domaine, réussite/échec).
- **EF-24** — Calculer des statistiques (réussite par domaine, par niveau K, tendance temporelle).
- **EF-25** — Générer des **recommandations** pédagogiques personnalisées (« réviser DOFD-6 », « refaire un blanc »).

### 4.6 Import / export des questions

- **EF-26** — Exporter la banque de questions au format **JSON** (et **CSV** pour relecture).
- **EF-27** — Importer des questions depuis JSON/CSV avec **validation de schéma** et rapport d'erreurs.
- **EF-28** — Import idempotent : détection des doublons (clé naturelle ou hachage du contenu).
- **EF-29** — Versionner les questions (champ `version`, statut `brouillon`/`publiée`/`archivée`).

### 4.7 Mode hors-ligne et mode connecté

- **EF-30** — **Hors-ligne (par défaut)** : toutes les fonctions cœur (théorie, quiz, examens, suivi) fonctionnent **sans aucun accès réseau**.
- **EF-31** — **Connecté (optionnel)** : enrichissement (liens de ressources externes, vérification de mises à jour de contenu). L'absence de réseau **NE DOIT JAMAIS** bloquer l'usage.

### 4.8 Mode « Expert intensif » (sur-apprentissage, cible réglable jusqu'à 90 %)

- **EF-32** — Sessions chronométrées en conditions d'examen strictes (pas de correction avant la fin).
- **EF-33** — Sélection priorisée des items les plus difficiles et des domaines faibles.
- **EF-34** — **Gating** : le mode signale « prêt pour l'examen » uniquement lorsque la probabilité de réussite globale **≥ cible réglée par le curseur (65–90 %)** **et** qu'aucun domaine n'est sous le seuil officiel de 65 %.
- **EF-35** — Enchaînement d'examens blancs complets avec analyse comparative inter-sessions.
- **EF-36** — Routine quotidienne recommandée (objectifs du jour, série/streak).

### 4.9 Administration

- **EF-37** — CRUD complet sur questions, réponses, fiches, flashcards, domaines.
- **EF-38** — Gestion des utilisateurs et des rôles.
- **EF-39** — Tableau de bord d'équipe et export des statistiques.
- **EF-40** — Pilotage des paramètres (pondérations, seuils, durée d'examen).

---

## 5. Exigences non fonctionnelles

| Code | Catégorie | Exigence |
|---|---|---|
| ENF-01 | Portabilité | DOIT s'exécuter sur Windows 10+, Linux (distributions courantes) et via Docker, sans modification du code. |
| ENF-02 | Portabilité | DOIT fonctionner intégralement hors-ligne. |
| ENF-03 | Performance | Réponse API < 200 ms (P95) en usage local ; génération d'un examen < 1 s. |
| ENF-04 | Performance | DOIT supporter au moins l'équipe complète en local/poste (charge faible à modérée). |
| ENF-05 | Sécurité | Mots de passe hachés (algorithme à coût configurable) ; jamais de secret en clair. |
| ENF-06 | Sécurité | Protection contre injection SQL (ORM/requêtes paramétrées) et XSS (échappement côté Vue). |
| ENF-07 | Sécurité | Authentification par session/token ; contrôle d'accès par rôle (RBAC). |
| ENF-08 | Maintenabilité | Architecture en couches, code typé/documenté, couverture de tests ≥ 80 % sur la logique métier. |
| ENF-09 | Fiabilité | Sauvegarde de la base SQLite automatisable ; restauration documentée. |
| ENF-10 | UX / Accessibilité | Interface responsive ; contrastes et navigation clavier conformes aux bonnes pratiques (WCAG AA visé). |
| ENF-11 | i18n | Interface et contenu en **français** par défaut ; structure prête pour d'autres langues. |
| ENF-12 | Observabilité | Logs structurés ; point de santé (`/health`) ; métriques applicatives exposables. |
| ENF-13 | Conformité | Aucune donnée personnelle superflue ; export/suppression des données utilisateur possible. |

---

## 6. Architecture technique

### 6.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                     Navigateur (poste local)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │   Frontend Vue.js (SPA)  —  store (Pinia) — Vue Router │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │  HTTP / JSON (API REST /api/v1)
┌───────────────────────────▼─────────────────────────────────┐
│              Backend Python (Django + DRF)                   │
│  ┌──────────────┬───────────────┬──────────────────────┐    │
│  │  API REST    │  Services      │  Moteurs             │    │
│  │  (DRF views) │  (logique      │  - adaptatif         │    │
│  │              │   métier)      │  - probabilité       │    │
│  │              │                │  - révision espacée  │    │
│  │              │                │  - génération examen │    │
│  └──────────────┴───────────────┴──────────────────────┘    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            ORM Django  +  Migrations                   │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │   SQLite (fichier) │
                  └────────────────────┘
```

Le frontend est **compilé** (build statique) et **servi par le backend Django**, ce qui simplifie le déploiement hors-ligne (un seul service à lancer). Le mode Docker encapsule l'ensemble.

### 6.2 Stack technologique retenue

| Couche | Technologie | Justification |
|---|---|---|
| Backend | **Python 3.11+ / Django 4.x** | ORM mature, migrations, admin intégré, robustesse |
| API | **Django REST Framework (DRF)** | Sérialisation, vues, auth, pagination |
| Base de données | **SQLite** | Zéro serveur, portable, fichier unique |
| Frontend | **Vue.js 3 (Composition API)** | Demandé ; réactif et léger |
| État | **Pinia** | Store moderne recommandé pour Vue 3 |
| Routage | **Vue Router** | Navigation SPA |
| Build front | **Vite** | Build rapide, sortie statique |
| Conteneur | **Docker / docker-compose** | Cible de livraison « full Docker » |
| Tests back | **pytest / pytest-django** | Standard de l'écosystème |
| Tests front | **Vitest / Vue Test Utils** | Tests unitaires composants |
| Qualité | **ruff + black** (Python), **ESLint + Prettier** (JS) | Lint/format |

> **Note d'architecture — alternative « zéro dépendance ».** La demande retient **Django** pour sa maintenabilité (ORM, migrations, admin). Si la **portabilité « sans aucune installation »** devenait la priorité absolue, une variante reposant **uniquement sur la bibliothèque standard Python** (`http.server`, `sqlite3`) est techniquement possible, au prix d'un effort accru (ORM, migrations et admin à réimplémenter). **Le présent CDC retient Django conformément à la demande** ; la variante « zéro dépendance » est documentée comme **option B** activable si le contexte d'exécution se révèle contraint.

### 6.3 Architecture backend (en couches)

```
api/            → vues DRF (contrôleurs), sérialiseurs, routage
services/       → logique métier (cas d'usage), orchestration
engines/        → moteurs (adaptatif, probabilité, SR, génération examen)
models/         → entités ORM Django
repositories/   → accès données spécifiques (requêtes complexes)
core/           → config, sécurité, utilitaires, i18n
```

Principe : **les vues ne contiennent pas de logique métier** ; elles délèguent aux `services`, qui appellent les `engines` et `repositories`. Cela facilite tests et évolutions.

### 6.4 Architecture frontend

```
src/
 ├── views/          → écrans (Dashboard, Examen, Révision, Admin…)
 ├── components/      → composants réutilisables (QuestionCard, Timer, ProgressRing…)
 ├── stores/         → Pinia (auth, progression, examen, contenu)
 ├── router/         → routes + gardes (auth, rôles)
 ├── services/       → client API (axios/fetch), gestion erreurs
 ├── composables/    → logique réutilisable (useTimer, useExam…)
 └── assets/         → styles, i18n (fr)
```

### 6.5 API REST — principes

- Préfixe versionné : `/api/v1/`.
- Verbes HTTP standard ; codes de statut explicites (200/201/400/401/403/404/422).
- Pagination, filtrage et tri sur les collections.
- Réponses JSON normalisées ; erreurs structurées (`{ "error": { "code", "message", "details" } }`).
- Auth par token de session.

Exemples d'endpoints (liste non exhaustive — détails et exemples en §7) :

| Méthode | Endpoint | Rôle |
|---|---|---|
| POST | `/api/v1/auth/login` | Connexion |
| GET | `/api/v1/me/progress` | Progression de l'utilisateur |
| PATCH | `/api/v1/me/preferences` | Met à jour la cible de réussite (curseur 65–90 %) |
| GET | `/api/v1/domains` | Domaines + pondérations |
| GET | `/api/v1/questions` | Recherche filtrée de questions |
| POST | `/api/v1/exams/generate` | Génère un examen (pondéré) |
| GET | `/api/v1/exams/sessions/{id}` | Détail d'une session |
| POST | `/api/v1/exams/sessions/{id}/submit` | Soumet et corrige |
| GET | `/api/v1/flashcards/due` | Cartes à réviser (SR) |
| POST | `/api/v1/flashcards/{id}/review` | Enregistre une révision |
| GET | `/api/v1/recommendations` | Recommandations personnalisées |
| GET | `/api/v1/dashboard` | Données du tableau de bord |
| POST | `/api/v1/admin/questions/import` | Import (admin) |
| GET | `/api/v1/admin/questions/export` | Export (admin) |
| GET | `/health` | Santé du service |

### 6.6 Modèle de données SQLite

#### 6.6.1 Vue relationnelle (entités principales)

```
certification 1───∞ domain 1───∞ question 1───∞ answer_option
                                   │
user 1───∞ exam_session ∞───1 exam_template
  │              │
  │              └─∞ exam_session_question ∞───1 question
  │
  ├─∞ attempt_log ∞───1 question
  ├─∞ sr_card ∞───1 (question | flashcard)
  ├─∞ mastery (par domain × k_level)
  ├─∞ weakness
  └─∞ recommendation
domain 1───∞ flashcard
domain 1───∞ theory_section
```

#### 6.6.2 DDL des tables cœur (extrait)

```sql
-- Certifications (extensibilité multi-certification)
CREATE TABLE certification (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,         -- ex: 'DOFD_V3_4'
    label           TEXT NOT NULL,
    pass_threshold  REAL NOT NULL DEFAULT 0.65,   -- 65 %
    question_count  INTEGER NOT NULL DEFAULT 40,
    duration_min    INTEGER NOT NULL DEFAULT 60,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Domaines pondérés
CREATE TABLE domain (
    id              INTEGER PRIMARY KEY,
    certification_id INTEGER NOT NULL REFERENCES certification(id),
    code            TEXT NOT NULL,                -- ex: 'DOFD-3'
    label           TEXT NOT NULL,
    weight          REAL NOT NULL,                -- pondération (0–1)
    sort_order      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(certification_id, code)
);

-- Questions
CREATE TABLE question (
    id              INTEGER PRIMARY KEY,
    domain_id       INTEGER NOT NULL REFERENCES domain(id),
    k_level         INTEGER NOT NULL CHECK (k_level BETWEEN 0 AND 6),
    difficulty      INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    qtype           TEXT NOT NULL CHECK (qtype IN ('single','multiple','truefalse','scenario')),
    statement       TEXT NOT NULL,
    explanation     TEXT,                         -- correction pédagogique
    source_ref      TEXT,                         -- ex: 'DevOps Handbook, concept X'
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    version         INTEGER NOT NULL DEFAULT 1,
    content_hash    TEXT NOT NULL,                -- déduplication à l'import
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(content_hash)
);

-- Options de réponse
CREATE TABLE answer_option (
    id              INTEGER PRIMARY KEY,
    question_id     INTEGER NOT NULL REFERENCES question(id) ON DELETE CASCADE,
    label           TEXT NOT NULL,
    is_correct      INTEGER NOT NULL DEFAULT 0,   -- 0/1
    feedback        TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

-- Utilisateurs
CREATE TABLE app_user (
    id              INTEGER PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'learner' CHECK (role IN ('learner','admin','reviewer')),
    locale          TEXT NOT NULL DEFAULT 'fr',
    target_score    REAL NOT NULL DEFAULT 0.90       -- cible du curseur (65 %–90 %)
                    CHECK (target_score BETWEEN 0.65 AND 0.90),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Modèle d'examen (configurable)
CREATE TABLE exam_template (
    id              INTEGER PRIMARY KEY,
    certification_id INTEGER NOT NULL REFERENCES certification(id),
    label           TEXT NOT NULL,
    question_count  INTEGER NOT NULL,
    duration_min    INTEGER NOT NULL,
    mode            TEXT NOT NULL DEFAULT 'mock' CHECK (mode IN ('mock','intensive','domain'))
);

-- Sessions d'examen
CREATE TABLE exam_session (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    template_id     INTEGER NOT NULL REFERENCES exam_template(id),
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT,
    score           REAL,                         -- 0–1
    passed          INTEGER,                      -- 0/1
    status          TEXT NOT NULL DEFAULT 'in_progress'
                    CHECK (status IN ('in_progress','submitted','expired'))
);

CREATE TABLE exam_session_question (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES exam_session(id) ON DELETE CASCADE,
    question_id     INTEGER NOT NULL REFERENCES question(id),
    given_answer    TEXT,                         -- JSON des options choisies
    is_correct      INTEGER,
    time_spent_sec  INTEGER,
    position        INTEGER NOT NULL
);

-- Journal granulaire des tentatives (hors examen)
CREATE TABLE attempt_log (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    question_id     INTEGER NOT NULL REFERENCES question(id),
    is_correct      INTEGER NOT NULL,
    difficulty      INTEGER NOT NULL,
    context         TEXT,                         -- 'quiz' | 'training' | 'flashcard'...
    answered_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Maîtrise par domaine × niveau K
CREATE TABLE mastery (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    domain_id       INTEGER NOT NULL REFERENCES domain(id),
    k_level         INTEGER NOT NULL CHECK (k_level BETWEEN 0 AND 6),
    score           REAL NOT NULL DEFAULT 0,      -- 0–1
    stable_sessions INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, domain_id, k_level)
);

-- Révision espacée (SM-2)
CREATE TABLE sr_card (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    item_type       TEXT NOT NULL CHECK (item_type IN ('question','flashcard')),
    item_id         INTEGER NOT NULL,
    ease_factor     REAL NOT NULL DEFAULT 2.5,
    interval_days   INTEGER NOT NULL DEFAULT 0,
    repetitions     INTEGER NOT NULL DEFAULT 0,
    due_date        TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE(user_id, item_type, item_id)
);

-- Faiblesses détectées et recommandations
CREATE TABLE weakness (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    domain_id       INTEGER NOT NULL REFERENCES domain(id),
    error_rate      REAL NOT NULL,
    detected_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE recommendation (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    rec_type        TEXT NOT NULL,                -- 'review_domain' | 'take_mock'...
    payload         TEXT,                         -- JSON
    status          TEXT NOT NULL DEFAULT 'open',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Tables complémentaires (DDL similaire) : `flashcard`, `theory_section`, `import_log`, `audit_log`, `setting`.

#### 6.6.3 Index recommandés

```sql
CREATE INDEX idx_question_filter ON question(domain_id, k_level, difficulty, status);
CREATE INDEX idx_attempt_user    ON attempt_log(user_id, question_id);
CREATE INDEX idx_sr_due          ON sr_card(user_id, due_date);
CREATE INDEX idx_mastery_user    ON mastery(user_id, domain_id);
CREATE INDEX idx_session_user    ON exam_session(user_id, started_at);
CREATE INDEX idx_esq_session     ON exam_session_question(session_id);
```

### 6.7 Arborescence du projet

```
dof-prep/
├── backend/
│   ├── manage.py
│   ├── pyproject.toml
│   ├── config/                 # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── content/            # domaines, questions, fiches, flashcards
│   │   ├── training/           # quiz, examens, sessions
│   │   ├── progress/           # maîtrise, faiblesses, recommandations
│   │   ├── users/              # auth, rôles
│   │   └── engines/            # moteurs (adaptatif, SR, probabilité, génération)
│   ├── api/                    # vues/sérialiseurs DRF, routage v1
│   ├── tests/
│   └── fixtures/               # contenu initial (JSON)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/                    # (cf. §6.4)
├── deploy/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── windows/
│   │   ├── install.ps1
│   │   └── start.ps1
│   └── linux/
│       ├── install.sh
│       └── start.sh
├── scripts/
│   ├── backup_sqlite.sh / .ps1
│   └── seed_content.py
├── docs/
│   ├── CDC.md                  # le présent document
│   └── ARCHITECTURE.md
├── .github/ (ou .gitlab-ci.yml)
├── .env.example
└── README.md
```

### 6.8 Sécurité et portabilité (synthèse)

- **Portabilité** : un seul artefact (backend servant le front compilé) ; base = fichier SQLite ; scripts par plateforme ; image Docker pour l'isolation totale.
- **Sécurité** : hachage des mots de passe, requêtes paramétrées (ORM), RBAC, échappement XSS côté Vue, en-têtes de sécurité, secrets via variables d'environnement, jamais en dur.

---

## 7. Spécifications détaillées (exemples concrets)

### 7.1 Exemple d'endpoint — génération d'examen

**Requête**
```http
POST /api/v1/exams/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "certification_code": "DOFD_V3_4",
  "mode": "mock"          // 'mock' | 'intensive' | 'domain'
}
```

**Réponse `201`**
```json
{
  "session_id": 412,
  "duration_min": 60,
  "question_count": 40,
  "questions": [
    {
      "id": 1187,
      "domain": "DOFD-3",
      "qtype": "single",
      "statement": "Dans le modèle CALMS, que recouvre le « M » ?",
      "options": [
        { "id": 4451, "label": "Measurement (mesure)" },
        { "id": 4452, "label": "Monitoring uniquement" },
        { "id": 4453, "label": "Microservices" },
        { "id": 4454, "label": "Management" }
      ]
    }
  ]
}
```

### 7.2 Exemple d'endpoint — soumission et correction

**Requête**
```http
POST /api/v1/exams/sessions/412/submit
Content-Type: application/json

{
  "answers": [
    { "question_id": 1187, "selected_option_ids": [4451], "time_spent_sec": 22 }
  ]
}
```

**Réponse `200`**
```json
{
  "session_id": 412,
  "score": 0.825,
  "passed": true,
  "threshold": 0.65,
  "by_domain": [
    { "domain": "DOFD-3", "correct": 6, "total": 7, "rate": 0.857 }
  ],
  "review": [
    {
      "question_id": 1187,
      "is_correct": true,
      "correct_option_ids": [4451],
      "explanation": "Dans CALMS, le M désigne Measurement : mesurer pour piloter l'amélioration continue."
    }
  ]
}
```

### 7.3 Exemple de jeu de données (contenu initial JSON)

```json
{
  "question": {
    "domain_code": "DOFD-2",
    "k_level": 2,
    "difficulty": 3,
    "qtype": "single",
    "statement": "Quelle « voie » (The Three Ways) met l'accent sur la rétroaction rapide et constante ?",
    "options": [
      { "label": "La Première Voie (Flux)", "is_correct": false },
      { "label": "La Deuxième Voie (Rétroaction)", "is_correct": true },
      { "label": "La Troisième Voie (Apprentissage)", "is_correct": false }
    ],
    "explanation": "La Deuxième Voie porte sur l'amplification des boucles de rétroaction.",
    "source_ref": "The DevOps Handbook — The Three Ways"
  }
}
```

### 7.4 Pseudo-code — moteurs clés

**a) Génération d'examen respectant la pondération**
```text
fonction generer_examen(certification, nb_questions):
    quotas ← {}
    pour chaque domaine de certification:
        quotas[domaine] ← arrondi(nb_questions * domaine.weight)
    ajuster(quotas) pour que somme(quotas) == nb_questions   # corrige les arrondis

    questions ← []
    pour chaque domaine, quota dans quotas:
        candidats ← questions_publiees(domaine)
        # privilégier la diversité K-level et la non-répétition récente
        selection ← echantillonner(candidats, quota,
                                    eviter_recents=historique(user),
                                    repartir_par_k_level=vrai)
        questions += selection
    retourner melanger(questions)
```

**b) Difficulté adaptative**
```text
fonction prochaine_difficulte(perf_recente):
    # perf_recente = taux de réussite sur les N derniers items
    si perf_recente >= 0.85: retourner min(difficulte_actuelle + 1, 5)
    si perf_recente <= 0.50: retourner max(difficulte_actuelle - 1, 1)
    retourner difficulte_actuelle
```

**c) Probabilité de réussite (préparation)**
```text
fonction probabilite_reussite(user, certification):
    total ← 0
    pour chaque domaine de certification:
        m ← maitrise_pondérée(user, domaine)     # 0–1, lissée et pénalisée si données rares
        total += m * domaine.weight
    # confiance réduite si peu de données
    confiance ← min(1, nb_items_repondus(user) / SEUIL_DONNEES)
    retourner total * confiance                   # 0–1
```

**d) Révision espacée (SM-2 simplifié)**
```text
fonction reviser(carte, qualite):   # qualite 0..5 (auto-évaluation ou exactitude)
    si qualite < 3:
        carte.repetitions ← 0
        carte.interval_days ← 1
    sinon:
        carte.repetitions += 1
        si carte.repetitions == 1: carte.interval_days ← 1
        sinon si carte.repetitions == 2: carte.interval_days ← 6
        sinon: carte.interval_days ← arrondi(carte.interval_days * carte.ease_factor)
        carte.ease_factor ← max(1.3,
            carte.ease_factor + (0.1 - (5 - qualite) * (0.08 + (5 - qualite) * 0.02)))
    carte.due_date ← aujourd_hui + carte.interval_days
```

**e) Détection de faiblesses → recommandation**
```text
fonction detecter_faiblesses(user, certification):
    pour chaque domaine:
        taux ← taux_erreur(user, domaine, fenetre=30j)
        si taux > SEUIL_FAIBLESSE:
            enregistrer_faiblesse(user, domaine, taux)
            creer_recommandation(user, "review_domain", {domaine})
```

**f) Signal « prêt pour l'examen » (gating, cible réglée par le curseur)**
```text
fonction est_pret(user, certification):
    cible ← user.target_score                 # 0.65–0.90, valeur du curseur
    p ← probabilite_reussite(user, certification)
    aucun_domaine_faible ← tous(maitrise_pondérée(user, d) >= 0.65
                                pour d dans certification.domaines)
    retourner (p >= cible) et aucun_domaine_faible
```

### 7.5 Workflow utilisateur type

```
1. Connexion → Dashboard (préparation globale comparée à la cible du curseur)
2. Réglage éventuel du curseur de cible (65 %–90 %)
3. Le moteur affiche des recommandations (« réviser DOFD-6 »)
4. Session ciblée (quiz adaptatif) → correction + explications
5. Mise à jour automatique : maîtrise, faiblesses, file de révision espacée
6. Périodiquement : examen blanc complet (40 Q / 60 min) → score par domaine
7. Mode Expert intensif jusqu'au signal « prêt » (probabilité ≥ cible du curseur, aucun domaine sous 65 %)
```

### 7.6 Exemple d'endpoint — réglage de la cible (curseur)

**Requête**
```http
PATCH /api/v1/me/preferences
Content-Type: application/json

{ "target_score": 0.80 }     // 0.65 ≤ valeur ≤ 0.90
```

**Réponse `200`**
```json
{ "target_score": 0.80, "ready_for_exam": false, "current_readiness": 0.72 }
```

Toute valeur hors de l'intervalle [0.65 ; 0.90] renvoie `422` (validation). Le champ `ready_for_exam` est recalculé selon la fonction `est_pret` (§7.4-f).

---

## 8. Écrans et interfaces (UI/UX)

| Écran | Objectif | Éléments clés |
|---|---|---|
| **Dashboard** | Vue d'ensemble | **Curseur de cible (65 %–90 %)**, anneau de préparation global comparé à la cible, domaines forts/faibles, recommandations, raccourci « examen blanc » |
| **Parcours d'apprentissage** | Progression par domaine et niveau K | Carte des 8 domaines, badges K0–K6, accès aux modules |
| **Quiz / Entraînement** | Pratique ciblée | Question, options, minuteur optionnel, correction + explication |
| **Examen blanc** | Conditions réelles | 40 questions, minuteur 60 min, navigation, soumission, écran de résultats détaillés |
| **Mode révision** | Révision espacée | File « à revoir » du jour, flashcards, suivi de série |
| **Mode challenge / Expert intensif** | Sur-apprentissage | Items difficiles, blancs enchaînés, comparaison inter-sessions, gating « prêt » |
| **Statistiques** | Analyse | Courbes de progression, réussite par domaine/niveau, historique des examens |
| **Gestion des sessions** | Historique | Liste des sessions, reprise, détail par session |
| **Administration** | Pilotage contenu/équipe | CRUD questions/fiches, utilisateurs, paramètres, tableau d'équipe |
| **Import / Export** | Enrichissement | Téléversement JSON/CSV, validation, rapport, export |

Principes UX : interface **en français**, responsive, lisible, navigation clavier, retours immédiats, parcours sans cul-de-sac.

**Composant « curseur de cible de réussite ».** Visible sur le Dashboard (et dans les préférences) : plage **65 %–90 %**, pas de 1 %, repères et étiquettes aux deux bornes (« Seuil officiel » à 65 %, « Confiance » à 90 %), valeur courante affichée en clair, accessible au clavier. Sa modification met immédiatement à jour l'anneau de préparation, le signal « prêt » et les seuils des tableaux de bord (appel `PATCH /api/v1/me/preferences`).

---

## 9. Extensibilité

L'architecture **DOIT** permettre, sans refonte :

- **Nouvelles certifications** : grâce à la table `certification` et aux `domain` rattachés (l'examen lit la config, rien n'est codé en dur).
- **Nouveaux modules pédagogiques** : par ajout d'une « app » Django et de composants Vue, via un contrat d'interface commun (un module expose : contenu, activité, scoring, alimentation de la progression).
- **Nouveaux questionnaires** : par import JSON/CSV validé.
- **Nouvelles taxonomies** : la taxonomie K0–K6 est paramétrable ; une table `competency_level` **DEVRAIT** porter les libellés et seuils pour autoriser d'autres modèles.
- **Évolutions futures** (hors périmètre initial) : SSO/LDAP, multi-tenant, application mobile.

---

## 10. Déploiement et exploitation (DevOps)

### 10.1 Stratégie multi-plateforme

Trois cibles, **un même code** :

| Cible | Principe | Livrables |
|---|---|---|
| **Linux** | venv + lancement local | `install.sh`, `start.sh` |
| **Windows** | venv + lancement PowerShell | `install.ps1`, `start.ps1` |
| **Docker** | image autonome | `Dockerfile`, `docker-compose.yml` |

> **Format des installateurs.** Les scripts d'installation **DEVRAIENT** être livrables au format *heredoc* / *here-string* auto-extractible (cohérent avec les habitudes de livraison du commanditaire), avec la syntaxe propre à chaque plateforme : `<<'EOF'` (shell, sans interpolation) et `@'...'@` (PowerShell). Les scripts **DOIVENT** être **générés à partir des sources testées**, jamais retranscrits à la main, pour garantir l'absence de divergence entre code testé et code livré.

### 10.2 Dockerfile (squelette)

```dockerfile
# Étape 1 : build du frontend
FROM node:20-alpine AS front
WORKDIR /front
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build          # sortie statique → dist/

# Étape 2 : backend + front compilé
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .
COPY backend/ .
COPY --from=front /front/dist ./static/   # Django sert le front
RUN python manage.py migrate
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# En production réelle : remplacer par gunicorn/uvicorn
```

### 10.3 docker-compose (squelette)

```yaml
services:
  dof-prep:
    build:
      context: .
      dockerfile: deploy/docker/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - dof_data:/app/data          # persistance de la base SQLite
    environment:
      - DOF_SECRET_KEY=${DOF_SECRET_KEY}
      - DOF_DB_PATH=/app/data/dofprep.sqlite3
      - DOF_DEBUG=0
    restart: unless-stopped
volumes:
  dof_data:
```

### 10.4 Scripts d'installation et de démarrage

- **Linux** (`install.sh`) : vérifie Python 3.11+, crée le venv, installe le backend, applique les migrations, charge le contenu initial, construit le front. (`start.sh`) lance le serveur et ouvre l'URL locale.
- **Windows** (`install.ps1` / `start.ps1`) : équivalents PowerShell.
- **Docker** : `docker compose up -d`.

### 10.5 Variables d'environnement

| Variable | Rôle | Exemple |
|---|---|---|
| `DOF_SECRET_KEY` | Clé secrète applicative | (généré) |
| `DOF_DB_PATH` | Chemin du fichier SQLite | `./data/dofprep.sqlite3` |
| `DOF_DEBUG` | Mode debug (0/1) | `0` |
| `DOF_HOST` / `DOF_PORT` | Hôte / port | `127.0.0.1` / `8000` |
| `DOF_LOCALE` | Langue par défaut | `fr` |
| `DOF_SECOND_ORDER` | Active par défaut la couche de second ordre (calibration métacognitive, EF-17b) — 0/1 | `0` |
| `DOF_ELO_K` | Gain de la boucle réflexive (mise à jour mutuelle aptitude ↔ difficulté latente), borné `[0,1]` | `0.08` |
| `DOF_CALIB_MIN_RECORDS` | Nombre minimal de prédictions avant que la calibration n'influe sur la préparation (anti-oscillation), entier ≥ 1 | `20` |
| `DOF_CALIB_FLOOR` | Plancher du facteur de calibration (jamais sous le seuil officiel 65 %), borné `[0,1]` | `0.60` |

Un fichier `.env.example` **DOIT** documenter toutes les variables (il est fourni avec le livrable et déposé par les installeurs ; sous Linux/macOS, `start.sh` charge automatiquement un `.env` présent à côté).

### 10.6 Stratégie de sauvegarde SQLite

- **Sauvegarde à chaud cohérente** : utiliser la commande de sauvegarde en ligne de SQLite (`.backup`) plutôt qu'une simple copie de fichier, pour éviter la corruption.
- **Planification** : script `backup_sqlite.(sh|ps1)` exécutable manuellement ou via tâche planifiée/cron ; rotation des sauvegardes (N derniers jours).
- **Restauration** : procédure documentée (arrêt du service, remplacement du fichier, redémarrage, vérification d'intégrité `PRAGMA integrity_check`).

```bash
# Exemple de sauvegarde cohérente
sqlite3 "$DOF_DB_PATH" ".backup '/backups/dofprep_$(date +%F_%H%M).sqlite3'"
```

### 10.7 CI/CD

Pipeline (GitHub Actions ou GitLab CI) en étapes :

```
lint  →  test (back: pytest, front: vitest)  →  build front  →  build image Docker  →  publication artefacts
```

- **DOIT** échouer si la couverture descend sous le seuil ou si le lint échoue.
- **DEVRAIT** publier l'image Docker et les installateurs en tant qu'artefacts versionnés.

### 10.8 Tests et qualité logicielle

| Type | Outil | Cible |
|---|---|---|
| Unitaires backend | pytest | logique métier, moteurs |
| Tests API | pytest + client DRF | endpoints, codes statut |
| Unitaires frontend | Vitest | composants critiques |
| Lint/format | ruff, black, ESLint, Prettier | conformité |
| Couverture | coverage.py | ≥ 80 % sur la logique métier |

Tests prioritaires : **génération d'examen pondérée**, **calcul de probabilité**, **révision espacée**, **import idempotent**, **RBAC**.

### 10.9 Monitoring, observabilité, versioning

- **Observabilité** : logs structurés (JSON), point `/health`, métriques applicatives exposables (compteurs d'examens, latence).
- **Versioning** : **versioning sémantique** (MAJOR.MINOR.PATCH).
- **Stratégie Git** : branches courtes (trunk-based ou GitFlow allégé), **commits conventionnels** (`feat:`, `fix:`, `docs:`…), revue obligatoire avant fusion, tags de release.

---

## 11. Livrables

| # | Livrable | Forme |
|---|---|---|
| L1 | Code source backend (Django/DRF) | Dépôt Git |
| L2 | Code source frontend (Vue 3) | Dépôt Git |
| L3 | Schéma + migrations SQLite | Dans le dépôt |
| L4 | Contenu pédagogique initial + **banque de 315 questions** (8 sections, K1–K7, difficultés 1–5, types variés) | Fixtures JSON |
| L5 | Installateurs Windows / Linux | `install.ps1`, `install.sh` |
| L6 | Déploiement Docker | `Dockerfile`, `docker-compose.yml` |
| L7 | Scripts de sauvegarde | `backup_sqlite.(sh\|ps1)` |
| L8 | Documentation | `README.md`, `ARCHITECTURE.md`, présent CDC |
| L9 | Suite de tests + pipeline CI/CD | Dans le dépôt |

---

## 12. Planning et jalons (proposition)

| Lot | Contenu | Sortie attendue |
|---|---|---|
| **Lot 0 — Socle** | Squelette projet, modèle de données, migrations, auth/RBAC, CI de base | Application démarrable, base initialisée |
| **Lot 1 — Contenu & QCM** | Domaines + contenu initial, modules théorie/flashcards/quiz, import/export | Entraînement de base fonctionnel |
| **Lot 2 — Moteur** | Génération d'examen pondérée, examens blancs, scoring, probabilité, faiblesses, recommandations | Examens blancs + tableau de bord |
| **Lot 3 — Modes avancés** | Révision espacée, niveaux K3–K7 (cas, scénarios, synthèse), **génération par niveau de difficulté + 12 examens blancs prédéfinis à recouvrement nul**, mode Expert intensif, **curseur de cible (65–90 %)** | Sur-apprentissage et gating sur cible réglable |
| **Lot 4 — Industrialisation** | Docker, installateurs, sauvegarde, observabilité, CI/CD complète, durcissement | Livraison multi-plateforme |
| **Recette** | Vérification des critères §13 | PV de recette |

*(Durées à fixer avec l'équipe ; les lots sont séquençables et partiellement parallélisables.)*

---

## 13. Critères d'acceptation (recette)

La solution est recevable si **toutes** les conditions suivantes sont satisfaites :

| # | Critère | Vérification |
|---|---|---|
| R1 | Couverture des 8 domaines | Contenu présent et publié pour chaque domaine |
| R2 | Génération d'examen pondérée | Sur 10 générations, écart ≤ 1 question par domaine vs pondération |
| R2b | Examens par niveau & anti-recouvrement | Génération par niveau (Moyen/Difficile/Très difficile) respectant la pondération exacte ; 12 examens prédéfinis reproductibles ; **recouvrement nul** entre deux examens d'un même niveau (banque ≥ 315 questions, viviers par domaine ≥ 4 × quota) |
| R3 | Format d'examen conforme | 40 questions, 60 minutes, seuil 65 %, aucune pénalité |
| R4 | Correction et explications | Chaque question corrigée fournit une explication |
| R5 | Cible réglable & préparation | Le curseur règle la cible de 65 % à 90 % (plancher/plafond respectés, persistance par utilisateur) ; la probabilité globale et le signal « prêt » se calent sur la valeur choisie |
| R6 | Détection de faiblesses | Recommandations générées à partir de l'historique |
| R7 | Révision espacée | File « à revoir » alimentée selon l'algorithme |
| R8 | Fonctionnement hors-ligne | Fonctions cœur opérationnelles sans réseau |
| R9 | Multi-plateforme | Démarrage validé sur Windows, Linux et Docker |
| R10 | Import/Export | Round-trip JSON sans perte ; doublons rejetés |
| R11 | Sécurité | Mots de passe hachés, RBAC effectif, requêtes paramétrées |
| R12 | Sauvegarde/restauration SQLite | Procédure exécutée et vérifiée (`integrity_check`) |
| R13 | Qualité | Lint OK, couverture ≥ 80 % sur la logique métier |
| R14 | Langue | Interface et contenu en français |

---

## 14. Risques, hypothèses et points d'attention

### 14.1 Hypothèses

- **H1** — Les paramètres d'examen de référence (40 Q, 60 min, 65 %, livre ouvert, sans pénalité, 8 domaines) correspondent au DOFD v3.4 ciblé. **À confirmer** sur le syllabus officiel détenu par le commanditaire.
- **H2** — Les pondérations des domaines du §3.1 sont les **valeurs officielles** du blueprint DevOps Institute (document *Examination Requirements*, v3.3) ; le référent **confirme** leur reconduction en v3.4, toute différence étant corrigeable par paramétrage en base.
- **H3** — L'usage est local/poste ou petit serveur d'équipe (charge faible à modérée).

### 14.2 Risques projet

| Risque | Impact | Mitigation |
|---|---|---|
| Écart entre pondérations v3.3 et v3.4 | Légère sous/sur-représentation d'un domaine | Valeurs officielles renseignées (§3.1), stockées en base et corrigeables sans redéploiement ; confirmation v3.4 par le référent |
| Banque de questions trop petite | Répétition, sur-apprentissage par cœur | **Banque de 315 questions originales** (K1–K7, types variés), viviers par domaine ≥ 4 × quota ; suivi de couverture |
| Sur-confiance par familiarité avec les items | Faux signal de préparation | **Recouvrement nul par construction** entre examens d'un même niveau (distribution « par donne ») ; rotation, niveaux de difficulté et items inédits |
| Décalage Django ↔ « portabilité totale » | Friction d'installation | Docker comme cible sûre ; option B « zéro dépendance » documentée |

### 14.3 Point d'attention — droits d'auteur (important)

L'application s'**inspire** d'ouvrages protégés. Pour rester en conformité, elle **NE DOIT PAS** :
- reproduire de texte verbatim (extraits, paragraphes) des manuels ou livres ;
- réutiliser des questions d'examen officielles ou des banques tierces sous licence.

Elle **DOIT** :
- produire un contenu **original** (questions, fiches, explications rédigées par le projet) ;
- citer les sources au niveau du **concept** (« notion abordée dans *The Phoenix Project* ») ;
- traiter le manuel officiel comme **référence de cadrage**, non comme source à copier.

### 14.4 Point d'attention — axiome « 7E »

Rappel (§3.5) : dispositif de **marque/engagement** uniquement, **hors référentiel officiel**, **exclu** des QCM représentatifs de l'examen. À utiliser pour l'identité de la plateforme, jamais pour la validité d'examen.

---

## 15. Annexes

### 15.1 Glossaire

| Terme | Définition |
|---|---|
| **DOFD** | DevOps Foundation (certification du DevOps Institute), version 3.4 |
| **CALMS** | Culture, Automation, Lean, Measurement, Sharing |
| **The Three Ways** | Flux, Rétroaction, Apprentissage continu (cadre DevOps) |
| **DORA** | Métriques de performance de livraison (DevOps Research and Assessment) |
| **K0–K6** | Niveaux cognitifs (de l'exposition à la création) |
| **Cybernétique de second ordre** | Cybernétique des *systèmes observants* : le système observe sa propre observation. Ici, l'apprenant devient observateur explicite (déclaration de confiance) et l'instrument de mesure se calibre lui-même (difficulté latente des items, facteur de confiance de la préparation — EF-17b) |
| **Calibration métacognitive / score de Brier** | Adéquation entre la confiance *prédite* par l'apprenant et sa réussite *réelle*. Le score de Brier (0 = parfait) mesure l'erreur quadratique moyenne des prédictions ; le biais signé distingue sur-confiance et sous-confiance, l'ECE résume l'erreur de calibration |
| **SR / SM-2** | Révision espacée / algorithme de planification des révisions |
| **RBAC** | Contrôle d'accès basé sur les rôles |
| **IaC** | Infrastructure as Code |
| **QCM** | Question à choix multiple(s) |

### 15.2 Références conceptuelles

- DevOps Institute — *DevOps Foundation* (syllabus officiel DOFD v3.4).
- Kim, Behr, Spafford — *The Phoenix Project*.
- Kim, Humble, Debois, Willis — *The DevOps Handbook*.
- Kniberg — *Scrum et XP depuis les tranchées*.
- Pask — *Conversation Theory* (cybernétique de second ordre appliquée à l'apprentissage : deux systèmes qui se modélisent mutuellement) — appui conceptuel de la boucle réflexive EF-17b.
- von Foerster — *Cybernetics of Cybernetics* (cybernétique des systèmes observants), fondement du « second ordre ».

---

*Fin du cahier des charges — version 1.0, pour validation.*
