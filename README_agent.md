# DOF-PREP — Agent IA compagnon (optionnel)

`dof-prep-agent.py` est un petit serveur local, 100 % bibliothèque standard
Python (rien à installer), qui ajoute **deux fonctions optionnelles** au
tableau de bord de DOF-PREP :

- **Analyser mes lacunes** : une synthèse en français, courte et concrète, de
  votre progression par domaine.
- **Proposer des questions** : de nouvelles questions d'entraînement générées
  pour un domaine choisi, **à relire avant toute utilisation**.

**Sans cet agent, DOF-PREP fonctionne exactement comme avant : 100 % hors-ligne.**
L'agent n'est jamais requis ; il n'est appelé que si vous cliquez sur un des
deux boutons dédiés, dans la carte « Assistant IA » du tableau de bord.

---

## Pourquoi un serveur local plutôt qu'un appel direct depuis le navigateur

- Votre **clé API Anthropic** ne doit jamais se trouver dans du code exécuté
  côté navigateur (elle serait visible via les outils de développement de
  n'importe qui consultant la page). L'agent la garde côté serveur, lue
  depuis une variable d'environnement, jamais transmise au navigateur.
- L'API Anthropic n'est pas conçue pour être appelée directement depuis un
  navigateur (CORS). L'agent relaie la requête et ajoute les en-têtes
  nécessaires pour que DOF-PREP — fichier autonome ouvert en `file://`, ou
  PWA servie en `http://` — puisse l'appeler depuis n'importe quelle origine
  locale.

## Ce que ça coûte, ce que ça implique

- Il vous faut **votre propre clé API Anthropic** (console.anthropic.com),
  aux frais de votre compte (usage facturé au tarif standard de l'API).
- Il vous faut une **connexion Internet** au moment où vous cliquez sur
  « Analyser » ou « Générer » (le reste de l'application n'en a jamais besoin).
- Les données envoyées sont **agrégées et non identifiantes** : scores de
  maîtrise par domaine (0 à 1), domaines faibles, préparation globale, et,
  pour la génération, les énoncés déjà existants du domaine ciblé (pour éviter
  les doublons) — jamais de donnée personnelle.

---

## Installation et lancement

Aucune dépendance à installer : le script n'utilise que la bibliothèque
standard de Python 3.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 dof-prep-agent.py
```

Vous devriez voir :

```
[dof-agent] DOF-PREP agent IA sur http://127.0.0.1:8799  (modele: claude-sonnet-5)
[dof-agent] 100% optionnel : sans lui, DOF-PREP fonctionne hors-ligne comme avant.
[dof-agent] Ctrl+C pour arreter.
```

Laissez ce terminal ouvert pendant que vous utilisez DOF-PREP dans votre
navigateur (fichier autonome ou PWA, peu importe). Rechargez ou cliquez sur
« Vérifier » dans la carte Assistant IA : le statut passe à « Agent détecté ».

Pour arrêter l'agent : `Ctrl+C` dans son terminal.

### Variables d'environnement (toutes optionnelles sauf la clé)

| Variable              | Défaut                  | Rôle                                    |
|------------------------|--------------------------|------------------------------------------|
| `ANTHROPIC_API_KEY`    | *(vide)*                | Clé API Anthropic. Sans elle, l'agent démarre mais `/analyze` et `/generate-questions` renvoient une erreur claire. |
| `DOF_AGENT_HOST`       | `127.0.0.1`              | Adresse d'écoute. **Ne changez pas sans lire la note de sécurité ci-dessous.** |
| `DOF_AGENT_PORT`       | `8799`                   | Port d'écoute.                          |
| `DOF_AGENT_MODEL`      | `claude-sonnet-5`        | Modèle Anthropic utilisé. Vérifiez la disponibilité/tarifs actuels sur `docs.claude.com` si besoin d'un autre modèle. |

Si vous changez le port ou l'hôte, mettez à jour l'URL correspondante dans la
carte Assistant IA de DOF-PREP (champ texte à côté du bouton « Vérifier ») ;
elle est mémorisée localement.

### Sécurité — ne pas exposer l'agent sur le réseau

Par défaut, l'agent n'écoute que sur `127.0.0.1` (votre machine uniquement).
Le CORS est volontairement permissif (nécessaire pour qu'une page ouverte en
`file://` puisse l'appeler). **Si vous changez `DOF_AGENT_HOST` pour l'exposer
sur votre réseau local (ex. `0.0.0.0`), n'importe quel appareil de ce réseau
pourrait alors consommer votre clé API à travers cet agent.** Ne le faites pas
sans comprendre et accepter ce risque.

---

## Ce que l'agent NE fait PAS

- Il ne modifie **jamais** `questions.json` ni la banque officielle.
- Les questions générées ne sont **jamais** utilisées dans les examens blancs
  pondérés (les 12 examens officiels et l'examen libre continuent de piocher
  exclusivement dans la banque validée).
- Elles sont affichées à l'écran, clairement marquées « IA — à valider », avec
  un bouton **Télécharger ces questions (JSON)** ; c'est à vous de les relire
  et, si elles vous conviennent, de les intégrer à la banque officielle via
  les outils déjà existants du projet Python (`--import-csv` /
  `--validate --strict` sur `devops_foundation_prep.py`).
- Rien n'est stocké côté agent : chaque requête est traitée puis oubliée
  (aucune base de données, aucun journal persistant au-delà de la console).

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| « Agent non détecté » alors qu'il tourne | Mauvaise URL/port dans le champ de la carte | Vérifiez l'URL (`http://127.0.0.1:8799` par défaut) et cliquez sur « Vérifier ». |
| « Agent détecté, mais aucune clé API définie » | `ANTHROPIC_API_KEY` non exportée avant le lancement | Arrêtez l'agent (Ctrl+C), exportez la clé, relancez. |
| Erreur au clic sur « Analyser »/« Générer » | Clé invalide, quota dépassé, ou panne réseau | Le message d'erreur renvoyé par l'agent reprend le détail de l'API Anthropic. |
| Le port 8799 est déjà utilisé | Une instance de l'agent tourne déjà | Réutilisez-la, ou changez `DOF_AGENT_PORT`. |

---

## Vérifications effectuées sur ce composant

- **Tests unitaires purs** (`agent_unit_test.py`, sans réseau ni clé) :
  translittération des accents, extraction JSON tolérante (JSON brut, balises
  ```` ```json ``` ````, texte parasite autour), validation des questions
  générées (domaines, bornes k_level/difficulty, règles single/multiple/
  truefalse) — **18/18 passent**.
- **Test d'intégration UI** (`ui.smoke.js`) : démarre réellement l'agent (sans
  clé), vérifie la détection réseau depuis l'application, l'affichage du
  statut, et la remontée propre du message d'erreur « clé API manquante »
  jusqu'à l'interface au clic sur « Analyser mes lacunes ».
- **Non testé ici** (nécessite une vraie clé API, donc hors de portée d'une
  vérification automatisée sans compte) : le contenu réel renvoyé par l'API
  Anthropic. Le format de sortie est cependant strictement validé côté agent
  avant d'atteindre l'interface (voir `validate_question` dans
  `dof-prep-agent.py`) : toute réponse non conforme est rejetée avec un
  message clair plutôt que transmise telle quelle.
