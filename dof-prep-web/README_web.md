# DOF-PREP — version web hors-ligne

Préparation à la certification **DevOps Foundation (DOFD v3.4)**, portée intégralement
côté navigateur. Toute la logique (génération d'examens, correction, maîtrise,
révision espacée SM-2, calibration métacognitive) s'exécute **sans serveur et sans
réseau** une fois la page chargée. La banque `questions.json` est la **source unique
partagée** avec la version Python (sha256 `303f3989…51f51ca`).

Deux manières d'utiliser l'application, selon le besoin.

---

## 1) Le plus simple : le fichier autonome (zéro installation)

**`dof-prep-standalone.html`** contient tout : interface, moteur et **banque inlinée**
(byte-identique à `questions.json`). 

- Double-cliquez le fichier : il s'ouvre dans le navigateur et fonctionne **hors-ligne
  total**, sans serveur, sans connexion. Vous pouvez le copier sur une clé USB, un
  téléphone, l'envoyer par mail, etc.
- Limite connue : ouvert en `file://`, l'enregistrement de la progression
  (localStorage) fonctionne sur la plupart des navigateurs de bureau mais peut être
  restreint par certains navigateurs (notamment sur mobile en `file://`). Si vous
  voulez une progression persistante garantie et une icône sur l'écran d'accueil,
  utilisez la version PWA ci-dessous.

---

## 2) Application installable (PWA) — recommandé sur mobile

Le dossier web (les fichiers listés plus bas) constitue une **PWA installable** : après
une première ouverture servie en HTTP(S), elle s'installe et devient **100 % hors-ligne**
grâce au *service worker* qui pré-cache l'application et la banque.

Pourquoi un service ? Un *service worker* ne s'exécute pas en `file://` : il faut donc
servir le dossier **une fois** (ensuite tout est en cache, réseau coupé compris).

Servir localement (au choix) :

```bash
cd dof-prep-web
python3 -m http.server 8000
# puis ouvrir http://localhost:8000/ dans le navigateur
```

ou déposer le dossier sur n'importe quel hébergeur de fichiers statiques (GitHub Pages,
Netlify, un partage interne…). Aucune base de données, aucun back-end.

Installer :
- **Android / Chrome** : menu ⋮ → « Installer l'application » / « Ajouter à l'écran
  d'accueil ».
- **iOS / Safari** : Partager → « Sur l'écran d'accueil ».
- **Bureau** : icône d'installation dans la barre d'adresse.

Après installation, l'application s'ouvre en plein écran et **fonctionne sans réseau**.

---

## Fonctionnalités

- **Tableau de bord** : jauge de préparation, score cible réglable (65–90 %), maîtrise
  par domaine, recommandations. Bascule de la **couche de second ordre**.
- **Examens blancs** : 12 examens prédéfinis (4 par niveau Moyen / Difficile / Très
  difficile) à **recouvrement nul** entre examens d'un même niveau, plus un **examen
  libre** par niveau. 40 questions, seuil 65 %, sans pénalité.
- **Entraînement** par domaine avec correction immédiate et explications.
- **Révision espacée (SM-2)** : les questions reviennent à échéance.
- **Calibration** (si second ordre actif) : score de Brier, ECE, courbe de fiabilité,
  **tendance temporelle** du Brier, détail par domaine ; la préparation est pondérée par
  un **facteur de calibration** (jamais sous le plancher de 0,60).

Quand la couche de second ordre est active, une **question de confiance** (25/50/75/95 %)
accompagne chaque réponse, l'onglet **Calibration** apparaît, et l'aptitude/difficulté
latentes sont mises à jour (Elo léger). La difficulté éditoriale (1–5, qui pilote les
bandes et le recouvrement nul) reste inchangée.

---

## Assistant IA (optionnel)

Le tableau de bord affiche une carte **« Assistant IA »**. Elle est
**entièrement optionnelle** : sans rien faire, elle indique juste « agent non
détecté » et le reste de l'application fonctionne exactement comme décrit
ci-dessus, 100 % hors-ligne.

Pour l'activer, lancez en local le petit serveur compagnon fourni
(`dof-prep-agent.py`, bibliothèque standard Python uniquement) avec votre
propre clé API Anthropic. Voir **`README_agent.md`** pour l'installation, la
sécurité, et le détail de ce qui est envoyé (uniquement des scores de maîtrise
agrégés — jamais de donnée personnelle). Les questions générées restent
séparées de la banque officielle et pondérée : elles sont à relire et à
télécharger manuellement si vous voulez les intégrer.

---

## Données & vie privée

Toute la progression est stockée **localement** dans le navigateur (clé `dofprep:v1`).
Rien n'est envoyé sur un réseau. Le bouton **« Réinitialiser ma progression »** (en bas
du tableau de bord) efface ces données.

---

## Modifier la banque de questions

`questions.json` est partagé avec le projet Python (même schéma, même contenu, même
sha256). Pour faire évoluer la banque :

1. Éditez `questions.json` (ou utilisez les outils CSV de la version Python :
   `--export-csv` / `--import-csv`, puis revalidez avec `--validate --strict`).
2. Pour le **fichier autonome**, régénérez-le afin de réinliner la banque à jour
   (le contenu inliné doit rester byte-identique à `questions.json`).
3. Pour la **PWA**, incrémentez la version de cache dans `sw.js` (actuellement
   `CACHE = "dofprep-v2"` ; passez à `"dofprep-v3"`, etc.) pour forcer la mise
   à jour du cache hors-ligne.

---

## Parité avec la version Python (vérifications)

Le moteur web reproduit **les mêmes garanties** que la version Python, vérifiées
automatiquement :

- **Moteur — 41/41** : 315 questions, distribution par domaine identique au Python
  `--stats`, quotas `5,4,7,7,6,5,2,4` (somme 40), **recouvrement nul** sur les trois
  niveaux, pondération exacte par examen, reproductibilité par graine, règle de score
  (choix multiple = ensemble exact requis), EMA de maîtrise, SM-2, Elo de second ordre,
  calibration (plancher 0,60) et tendance du Brier, préparation = brute × facteur.
- **Interface — 13/13** (headless) : rendu du tableau de bord et de la jauge, lancement
  d'un examen blanc (40 questions), correction à 100 % « Réussite », persistance de la
  progression, apparition de l'onglet Calibration à l'activation du second ordre.

Note d'honnêteté : la version web utilise un générateur pseudo-aléatoire propre
(déterministe et reproductible). Elle garantit **les mêmes invariants** que la version
Python — pondération exacte, recouvrement nul, reproductibilité — sans prétendre tirer
les **mêmes identifiants** de questions que le générateur de CPython (algorithmes
différents).

---

## Contenu du dossier (PWA)

- `index.html` — page de l'application
- `app.css` — styles
- `engine.js` — moteur (logique, identique en garanties à la version Python)
- `store.js` — persistance locale
- `app.js` — interface (5 vues)
- `sw.js` — service worker (hors-ligne)
- `manifest.webmanifest` — manifeste PWA
- `questions.json` — banque (source unique partagée)
- `icon-192.png`, `icon-512.png`, `icon-180.png` — icônes
- `dof-prep-standalone.html` — **version autonome** (tout-en-un, ouverture directe)
