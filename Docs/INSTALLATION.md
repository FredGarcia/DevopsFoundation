# DOF-PREP — Guide d'installation (toutes options)

Préparation à la certification **DevOps Foundation** (DOFD v3.4, DevOps Institute).
Ce document recense **toutes les façons d'installer et d'exécuter DOF-PREP**, du
poste de bureau au smartphone Android, avec ou sans l'assistant IA optionnel.

> **Une seule question à se poser pour choisir : sur quel appareil, et pour
> combien de temps ?** Voir le tableau de synthèse ci-dessous, puis la section
> correspondante.

---

## Sommaire

1. [Panorama des options](#1-panorama-des-options)
2. [Option A — Application Python (serveur + interface intégrée)](#2-option-a--application-python)
3. [Option B — Fichier autonome (`dof-prep-standalone.html`)](#3-option-b--fichier-autonome)
4. [Option C — Application web installable (PWA)](#4-option-c--pwa)
5. [Option D — Android via Termux](#5-option-d--android-via-termux)
6. [Option E — Assistant IA compagnon (optionnel, toutes options)](#6-option-e--assistant-ia-compagnon)
7. [Mettre à jour la banque de questions](#7-mettre-à-jour-la-banque-de-questions)
8. [Dépannage général](#8-dépannage-général)

---

## 1) Panorama des options

| Option | Ce que c'est | Prérequis | Persistance de la progression | Hors-ligne | Idéal pour |
|---|---|---|---|---|---|
| **A. Python** | Serveur local + interface intégrée | Python 3.10+ | SQLite (fiable) | Oui (réseau coupé possible) | Poste fixe, usage prolongé, export CSV |
| **B. Standalone** | Un seul fichier `.html` | Un navigateur | localStorage — **fragile en `file://`**, surtout mobile | Oui, total, sans rien installer | Dépannage, partage instantané, clé USB |
| **C. PWA** | Dossier web installable | Un navigateur + un service HTTP pour la 1ʳᵉ visite | localStorage — fiable (origine stable) | Oui, après 1ʳᵉ visite (service worker) | Mobile/bureau au quotidien, icône dédiée |
| **D. Android/Termux** | B ou C lancés depuis un raccourci | Termux + Termux:API | Selon la variante lancée (B ou C) | Oui | Utilisateurs avancés d'Android |
| **E. Assistant IA** | Serveur compagnon optionnel | Python 3 + clé API Anthropic + Internet (ponctuel) | N/A (rien n'est stocké côté agent) | **Non**, par nature (appelle une API) | Analyse de lacunes, génération de questions |

Les options A, B et C partagent **la même banque de questions** (`questions.json`,
schéma identique, contenu identique) et, pour B et C, **le même moteur**
(`engine.js`), avec les mêmes garanties (pondération par domaine, examens à
recouvrement nul, calibration). L'option D est un simple lanceur pour B ou C.
L'option E est indépendante et strictement optionnelle : sans elle, tout le
reste fonctionne à l'identique.

---

## 2) Option A — Application Python

Le programme original : un serveur HTTP local (bibliothèque standard
uniquement, aucune dépendance) qui sert une interface complète et persiste la
progression en SQLite.

### Installation

**Linux / macOS**

```bash
chmod +x install.sh
./install.sh
```

**Windows (PowerShell)**

```powershell
./install.ps1
```

**Docker**

```bash
chmod +x install-docker.sh
./install-docker.sh
```

Chaque installeur est un script heredoc autoporté : il contient déjà tout le
code de l'application (`devops_foundation_prep.py`, `questions.json`), il n'y a
rien d'autre à télécharger.

### Lancement

```bash
python3 devops_foundation_prep.py
```

Le navigateur par défaut s'ouvre automatiquement sur l'interface. Pour arrêter :
`Ctrl+C` dans le terminal.

### Variables d'environnement utiles (voir `.env.example`)

| Variable | Rôle | Défaut |
|---|---|---|
| `DOF_HOST` | Adresse d'écoute | `127.0.0.1` |
| `DOF_PORT` | Port d'écoute | `8765` |
| `DOF_DB_PATH` | Emplacement de la base SQLite | `./dof_prep.db` |
| `DOF_OPEN_BROWSER` | Ouvrir automatiquement le navigateur | `1` |
| `DOF_QUESTIONS_PATH` | Chemin vers la banque | `./questions.json` |
| `DOF_STRICT` | Démarrage strict (refuse en cas d'avertissement) | `0` |
| `DOF_SECOND_ORDER` | Active la calibration métacognitive par défaut | `0` |

### Commandes utiles

```bash
python3 devops_foundation_prep.py --validate --strict   # valide la banque, échoue sur tout avertissement
python3 devops_foundation_prep.py --stats                # statistiques de la banque (distribution, etc.)
python3 devops_foundation_prep.py --export-csv out.csv   # export de la banque en CSV
python3 devops_foundation_prep.py --import-csv out.csv   # ré-import (aller-retour sans perte)
```

---

## 3) Option B — Fichier autonome

`dof-prep-standalone.html` contient **tout** : interface, moteur, et banque de
questions inlinée (identique à `questions.json`).

### Installation

Il n'y en a pas. Copiez le fichier où vous voulez (bureau, clé USB, téléphone,
pièce jointe d'e-mail) et **double-cliquez dessus**. Il s'ouvre dans votre
navigateur par défaut et fonctionne immédiatement, réseau coupé y compris.

### Limite à connaître

Ouvert en `file://` (sans serveur), la sauvegarde de la progression
(`localStorage`) peut être restreinte par certains navigateurs, en particulier
sur mobile. Pour une progression garantie sur la durée, préférez l'option C
(PWA). Le fichier standalone reste néanmoins la meilleure option pour un essai
rapide, un dépannage, ou un partage instantané.

---

## 4) Option C — PWA

Le dossier `dof-prep-web/` (hors `dof-prep-standalone.html` et `dof-prep-agent.py`,
qui sont indépendants) constitue une **application web installable**.

### Pourquoi un serveur, ne serait-ce qu'une fois

Le mécanisme qui permet le hors-ligne robuste (le *service worker*) **ne
s'exécute pas** en `file://`. Il faut donc servir le dossier **une seule fois**
en HTTP(S) ; ensuite, tout est mis en cache et le réseau peut être coupé.

### Installation locale (test rapide)

```bash
cd dof-prep-web
python3 -m http.server 8000
# puis ouvrir http://localhost:8000/ dans le navigateur
```

### Installation via un hébergeur statique (recommandé pour un usage durable)

Déposez le contenu du dossier sur n'importe quel hébergeur de fichiers
statiques : GitHub Pages, Netlify, Vercel, Cloudflare Pages, ou un simple
partage interne. Aucune base de données, aucun back-end requis.

### Installer l'icône sur l'appareil

- **Android / Chrome** : menu ⋮ → « Installer l'application » ou « Ajouter à
  l'écran d'accueil ».
- **iOS / Safari** : bouton Partager → « Sur l'écran d'accueil ».
- **Bureau (Chrome/Edge)** : icône d'installation dans la barre d'adresse.

Une fois installée, l'application s'ouvre en plein écran, avec sa propre icône,
et **fonctionne sans réseau**.

---

## 5) Option D — Android via Termux

Pour les utilisateurs avancés qui veulent lancer B ou C d'un tap depuis
l'écran d'accueil, sans passer par un navigateur classique. Ceci est un
**lanceur**, pas une troisième variante de l'application : il exécute soit le
standalone (B), soit la PWA (C), selon ce qui est présent dans le dossier.

### Prérequis

- **Termux** (F-Droid recommandé — la version Play Store est obsolète et non
  maintenue).
- **Termux:API** (F-Droid ou Play Store), et le paquet correspondant :
  ```bash
  pkg install termux-api
  ```
- Les fichiers de DOF-PREP copiés sur le téléphone, par exemple dans
  `~/storage/shared/DOFPrep` (nécessite d'avoir lancé `termux-setup-storage`
  au préalable pour accéder au stockage partagé).

### Script de lancement

Créez `~/launch-dofprep.sh` :

```bash
#!/data/data/com.termux/files/usr/bin/bash
# Chemin vers le dossier de l'appli (a ajuster si besoin)
APP_DIR="$HOME/storage/shared/DOFPrep"

cd "$APP_DIR" || { echo "Dossier introuvable : $APP_DIR"; exit 1; }

if [ -f "dof-prep-standalone.html" ]; then
    # Version standalone : ouverture directe dans le navigateur
    termux-open dof-prep-standalone.html
elif [ -f "index.html" ]; then
    # Version PWA : necessite un petit serveur local (pour le service worker)
    (python3 -m http.server 8080 &> /dev/null &)
    sleep 1
    termux-open-url "http://localhost:8080"
else
    echo "Aucune version de l'appli trouvee dans $APP_DIR"
fi
```

Puis :

```bash
chmod +x ~/launch-dofprep.sh
```

Ajustez `APP_DIR` si nécessaire (`ls ~/storage/shared` pour vérifier le bon
chemin).

### Créer le raccourci sur l'écran d'accueil

Selon la variante présente dans `APP_DIR` :

- **Standalone** : installez **Termux:Widget** (F-Droid), puis :
  ```bash
  mkdir -p ~/.shortcuts
  cp ~/launch-dofprep.sh ~/.shortcuts/
  ```
  Ajoutez ensuite le widget Termux:Widget sur l'écran d'accueil : il propose
  le script comme raccourci lançable en un tap.

- **PWA** : après avoir lancé le script une première fois (serveur local +
  Chrome ouvert sur `localhost:8080`), utilisez le menu Chrome →
  **« Ajouter à l'écran d'accueil »**. Cela crée une vraie icône PWA installée,
  plus fiable dans la durée que le raccourci Termux (voir option C).

### Quelle variante choisir sur Android ?

Si vous voulez la **fiabilité de la progression sur la durée** : privilégiez
la PWA (C), avec un vrai « Ajouter à l'écran d'accueil » Chrome plutôt que le
widget Termux. Le lanceur Termux reste utile si vous préférez rester dans cet
écosystème ou pour la variante standalone en dépannage ponctuel.

---

## 6) Option E — Assistant IA compagnon

Un serveur local **strictement optionnel** (`dof-prep-agent.py`, bibliothèque
standard uniquement) qui ajoute deux fonctions au tableau de bord : analyse
des lacunes et proposition de nouvelles questions d'entraînement. Il s'appuie
sur **votre propre clé API Anthropic**, à vos frais.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 dof-prep-agent.py
```

**Sans lui, l'application (A, B, C ou D) fonctionne exactement comme décrit
ci-dessus, 100 % hors-ligne.** Détails complets — sécurité, coûts, ce qui est
envoyé, dépannage — dans `README_agent.md`.

---

## 7) Mettre à jour la banque de questions

`questions.json` est la **source unique**, partagée par les options A, B et C
(pour B, son contenu est recopié à l'identique dans le fichier standalone).
Après toute modification :

1. Éditez `questions.json`, ou utilisez `--export-csv` / `--import-csv` côté
   Python, puis validez avec `--validate --strict`.
2. **Option B (standalone)** : régénérez le fichier pour réinliner la banque à
   jour (le contenu inliné doit rester byte-identique à `questions.json`).
3. **Option C (PWA)** : incrémentez la version de cache dans `sw.js`
   (`CACHE = "dofprep-vN"`) pour forcer la mise à jour du cache hors-ligne chez
   les utilisateurs déjà installés.

---

## 8) Dépannage général

| Symptôme | Option concernée | Piste |
|---|---|---|
| Le navigateur ne s'ouvre pas automatiquement | A | Vérifiez `DOF_OPEN_BROWSER`, ou ouvrez manuellement `http://127.0.0.1:8765`. |
| Progression perdue après fermeture | B | Limite connue en `file://` sur certains navigateurs/mobiles — utilisez C. |
| L'app ne s'installe pas (pas d'icône proposée) | C | Le dossier doit être servi en HTTP(S), pas ouvert en `file://` ; vérifiez aussi que `manifest.webmanifest` est bien accessible. |
| Rien ne se passe au tap sur le raccourci | D | Vérifiez que `termux-api` est installé (paquet **et** application), et les permissions de stockage (`termux-setup-storage`). |
| « Agent non détecté » | E | Vérifiez que `python3 dof-prep-agent.py` tourne bien, et l'URL/port dans la carte Assistant IA (défaut `http://127.0.0.1:8799`). |
| Après une mise à jour, les anciens utilisateurs voient encore l'ancienne version (PWA) | C | Avez-vous bien incrémenté `CACHE` dans `sw.js` ? Sans cela, le service worker ressert le cache précédent. |

Pour toute question ne figurant pas ici, consultez `README.md` (option A) ou
`README_web.md` / `README_agent.md` (options B/C/E).
