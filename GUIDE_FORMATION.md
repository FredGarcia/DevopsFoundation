# DOF-PREP — Guide de formation à l'application

Ce guide explique **comment se servir de DOF-PREP** au quotidien pour préparer
la certification **DevOps Foundation** (DOFD v3.4, DevOps Institute), quelle
que soit la variante installée (Python, standalone, PWA — l'interface et les
fonctionnalités sont identiques).

---

## Sommaire

1. [Rappel du format d'examen officiel](#1-rappel-du-format-dexamen-officiel)
2. [Premier lancement](#2-premier-lancement)
3. [Tour des vues de l'application](#3-tour-des-vues-de-lapplication)
4. [Tableau de bord : lire sa préparation](#4-tableau-de-bord--lire-sa-préparation)
5. [Passer un examen blanc](#5-passer-un-examen-blanc)
6. [S'entraîner par domaine](#6-sentraîner-par-domaine)
7. [La révision espacée (SM-2)](#7-la-révision-espacée-sm-2)
8. [La calibration métacognitive (avancé)](#8-la-calibration-métacognitive-avancé)
9. [L'assistant IA (optionnel)](#9-lassistant-ia-optionnel)
10. [Méthode de préparation conseillée](#10-méthode-de-préparation-conseillée)
11. [Questions fréquentes](#11-questions-fréquentes)
12. [Glossaire des domaines DOFD](#12-glossaire-des-domaines-dofd)

---

## 1) Rappel du format d'examen officiel

| Caractéristique | Valeur |
|---|---|
| Nombre de questions | 40 |
| Durée | 60 minutes |
| Seuil de réussite | 65 % |
| Pénalité pour mauvaise réponse | Aucune (pas de points négatifs) |
| Documentation pendant l'examen | Autorisée (« open book ») |
| Domaines couverts | 8 (DOFD-1 à DOFD-8), pondérés différemment |

DOF-PREP reproduit fidèlement ce format dans ses examens blancs : mêmes
40 questions, même seuil, même absence de pénalité, et surtout **la même
pondération par domaine** que l'examen réel (voir le glossaire en fin de
document).

---

## 2) Premier lancement

Quelle que soit la variante (voir `INSTALLATION.md`), vous arrivez sur le
**Tableau de bord**, vide au premier lancement : aucune tentative, jauge de
préparation à 0 %. C'est normal — la préparation se construit au fil de vos
sessions d'entraînement, de révision et d'examens.

---

## 3) Tour des vues de l'application

L'application s'organise en onglets, accessibles en haut de l'écran :

| Onglet | Ce qu'on y fait |
|---|---|
| **Tableau de bord** | Voir sa préparation globale, sa maîtrise par domaine, ses réglages, et (si activé) l'assistant IA. |
| **Examen blanc** | Passer un des 12 examens prédéfinis, ou un examen libre généré à la volée. |
| **Entraînement** | S'exercer sur un domaine choisi, avec correction immédiate. |
| **Révision** | Retravailler les questions dues aujourd'hui (algorithme de répétition espacée). |
| **Calibration** | *(apparaît seulement si activée dans les réglages)* Analyse de la justesse de votre confiance en vos réponses. |

---

## 4) Tableau de bord : lire sa préparation

### La jauge de préparation

Un demi-cercle qui affiche un pourcentage : votre **préparation actuelle**,
c'est-à-dire une estimation de votre probabilité de réussite si vous passiez
l'examen maintenant. Le petit repère noir sur la jauge indique votre **score
cible** (réglable entre 65 % et 90 %).

- **Préparation brute** : la maîtrise moyenne pondérée par les poids
  officiels des domaines, ajustée par la quantité de données disponibles
  (peu de tentatives = estimation prudente).
- **Confiance des données** : à combien de réponses cumulées correspond votre
  estimation actuelle. Plus vous vous entraînez, plus elle se rapproche de
  100 %, et plus la préparation affichée devient fiable.

### Réglages

- **Score cible** (curseur 65–90 %) : au-delà du seuil officiel de 65 %, fixez
  votre propre objectif de confort.
- **Couche de second ordre** (case à cocher) : active la calibration
  métacognitive (voir section 8). Optionnel, désactivé par défaut.

### Maîtrise par domaine

Une barre par domaine (DOFD-1 à DOFD-8), avec le pourcentage de bonnes
réponses (moyenne mobile, donc plus sensible à vos réponses récentes qu'à vos
toutes premières tentatives) et le nombre de réponses cumulées sur ce domaine.
Une barre orange signale un domaine sous le seuil de maîtrise (65 %).

### Recommandations

Une liste de conseils générés automatiquement à partir de votre état actuel :
domaines à renforcer en priorité, ou confirmation que vous êtes prêt.

---

## 5) Passer un examen blanc

Deux façons de démarrer un examen, dans l'onglet **Examen blanc** :

### Les 12 examens prédéfinis

Répartis en 3 niveaux (**Moyen**, **Difficile**, **Très difficile**), 4
examens par niveau. **Propriété importante : les 4 examens d'un même niveau ne
partagent aucune question entre eux.** Vous pouvez donc les enchaîner sans
jamais retomber sur une question déjà vue à ce niveau — utile pour mesurer une
vraie progression d'un examen au suivant, plutôt que de la mémorisation de
questions répétées.

### L'examen libre

Génère un examen aléatoire au niveau choisi, à chaque fois différent, avec la
même pondération par domaine que les examens officiels.

### Pendant l'examen

Répondez aux 40 questions (à choix unique, multiple, ou vrai/faux selon la
question), puis cliquez **« Terminer et corriger »**. Vous pouvez aussi
**« Abandonner »** sans enregistrer de résultat.

### Après l'examen

- Un **score global** et la mention Réussite/Échec selon le seuil de 65 %.
- Un **détail par domaine** (bonnes réponses / total, taux).
- Une **correction question par question** : la ou les bonnes réponses sont
  surlignées en vert, votre réponse erronée éventuelle en rouge, avec
  l'explication pédagogique associée à chaque question.

Chaque réponse (juste ou fausse) alimente votre maîtrise par domaine et votre
planning de révision, exactement comme en mode Entraînement.

---

## 6) S'entraîner par domaine

Dans l'onglet **Entraînement**, choisissez un des 8 domaines. Les questions de
ce domaine défilent une par une, avec **correction immédiate** après chaque
réponse (contrairement à l'examen blanc, où la correction n'arrive qu'à la
fin). C'est le mode le plus adapté pour **apprendre**, plutôt que pour se
mettre en situation d'examen.

---

## 7) La révision espacée (SM-2)

Chaque question à laquelle vous répondez (en entraînement, en examen, ou en
révision) reçoit une **échéance de révision**, calculée par l'algorithme
**SM-2** (le même que celui utilisé par des outils de mémorisation espacée
reconnus) :

- Une réponse **fausse** remet l'échéance à demain.
- Une réponse **juste** repousse l'échéance de plus en plus loin à chaque
  répétition réussie (1 jour, puis 6 jours, puis un intervalle croissant).

L'onglet **Révision** ne vous montre que les questions **dues aujourd'hui**.
S'il n'y en a aucune, l'onglet vous l'indique simplement — revenez plus tard.
C'est la manière la plus efficace de faire remonter durablement votre
mémorisation, en concentrant l'effort sur ce qui est sur le point d'être
oublié plutôt que de tout revoir en bloc.

---

## 8) La calibration métacognitive (avancé)

Fonctionnalité optionnelle, à activer depuis le Tableau de bord (case
« Activer la couche de second ordre »).

### Ce qui change une fois activée

Après chaque réponse (examen, entraînement, révision), une question
supplémentaire apparaît : **« Confiance : 25 % / 50 % / 75 % / 95 % »**. Vous
indiquez à quel point vous étiez sûr de votre réponse *avant* de voir si elle
était juste.

### Pourquoi c'est utile

Réussir un examen ne dépend pas seulement de *ce que vous savez*, mais aussi
de **savoir évaluer ce que vous savez** — éviter la fausse confiance sur des
sujets mal maîtrisés, et la sous-confiance sur des sujets en réalité acquis.
Un nouvel onglet **Calibration** apparaît, avec :

- **Score de Brier** et **erreur de calibration (ECE)** : plus bas, plus
  votre confiance reflète fidèlement votre vraie réussite.
- **Courbe de fiabilité** : par tranche de confiance annoncée (moins de 40 %,
  ~50 %, ~75 %, ~95 %), votre taux de réussite réel dans cette tranche.
- **Tendance** : votre calibration s'améliore-t-elle, se dégrade-t-elle, ou
  reste-t-elle stable au fil du temps ?
- **Détail par domaine.**

Une fois suffisamment de données recueillies, votre **préparation affichée au
tableau de bord** est ajustée par un facteur de calibration : une confiance
mal calibrée (trop optimiste) réduit légèrement la préparation affichée, pour
éviter une fausse impression de sécurité avant l'examen réel. Ce facteur ne
descend jamais sous un plancher (0,60), pour ne jamais décourager
excessivement.

---

## 9) L'assistant IA (optionnel)

Si le serveur compagnon `dof-prep-agent.py` est lancé (voir `INSTALLATION.md`,
option E, et `README_agent.md`), une carte **« Assistant IA »** apparaît sur le
Tableau de bord avec deux fonctions :

- **Analyser mes lacunes** : une synthèse en français de votre progression,
  avec des pistes concrètes pour la suite.
- **Proposer des questions** : de nouvelles questions générées pour un domaine
  choisi. Elles sont clairement marquées **« IA — à valider »** et
  **ne comptent jamais dans vos examens blancs officiels** : à vous de les
  relire, et de les télécharger si vous voulez les conserver.

Sans cet agent lancé, la carte indique simplement « agent non détecté » et le
reste de l'application continue de fonctionner normalement.

---

## 10) Méthode de préparation conseillée

Une progression possible, à adapter à votre rythme :

1. **Diagnostic initial** : passez un examen blanc de niveau **Moyen** dès le
   début, sans réviser — cela révèle vos domaines faibles réels plutôt que
   supposés.
2. **Entraînement ciblé** : utilisez l'onglet Entraînement sur les 2–3
   domaines les plus faibles identifiés, en profitant de la correction
   immédiate et des explications.
3. **Révision quotidienne courte** : consultez l'onglet Révision chaque jour
   (quelques minutes suffisent) plutôt que de tout reporter à la veille de
   l'examen.
4. **Montée en difficulté** : une fois à l'aise en Moyen, enchaînez sur
   Difficile puis Très difficile — souvenez-vous que les 4 examens d'un même
   niveau ne se recoupent jamais, vous pouvez les utiliser comme 4 vraies
   mesures indépendantes de progression.
5. **Activez la calibration** si vous voulez travailler spécifiquement votre
   gestion du stress/de la confiance à l'approche de l'examen réel.
6. **Jour J moins quelques jours** : visez une préparation affichée
   confortablement au-dessus de votre score cible, sur **tous** les domaines
   (pas seulement en moyenne).

---

## 11) Questions fréquentes

**Ma progression a disparu après avoir fermé l'application.**
Selon la variante utilisée, voir la limite connue du fichier autonome en
`file://` (section 3 de `INSTALLATION.md`) — privilégiez la PWA installée pour
une persistance fiable.

**Puis-je repartir de zéro ?**
Oui : bouton **« Réinitialiser ma progression »** en bas du Tableau de bord.
Cette action efface toutes les données locales (maîtrise, cartes de révision,
historique) et ne peut pas être annulée.

**Le score cible à 90 % est-il obligatoire ?**
Non, c'est un objectif personnel réglable entre 65 % (le seuil officiel
minimal) et 90 %. Le viser vous laisse une marge de sécurité le jour de
l'examen réel.

**Une question à choix multiple compte-t-elle juste si je coche une bonne
réponse parmi plusieurs ?**
Non : pour les questions à choix multiple, **toutes** les bonnes réponses
doivent être cochées, et **aucune** mauvaise — un sous-ensemble incomplet est
compté comme faux, exactement comme dans l'examen réel.

**Mes données sont-elles envoyées quelque part ?**
Non, jamais, sauf si vous activez explicitement l'Assistant IA (section 9) et
cliquez sur un de ses deux boutons — et même alors, seules des statistiques
agrégées (pourcentages de maîtrise) sont transmises, jamais de donnée
personnelle.

---

## 12) Glossaire des domaines DOFD

| Code | Intitulé |
|---|---|
| DOFD-1 | Explorer le DevOps |
| DOFD-2 | Principes fondamentaux du DevOps (les Trois Voies) |
| DOFD-3 | Pratiques clés du DevOps |
| DOFD-4 | Cadres métier et techniques |
| DOFD-5 | Valeurs DevOps : culture, comportements et modèles opérationnels |
| DOFD-6 | Valeurs DevOps : automatisation et architecture des chaînes d'outils |
| DOFD-7 | Valeurs DevOps : mesure, métriques et reporting |
| DOFD-8 | Valeurs DevOps : partage, accompagnement et évolution |

Ces 8 domaines ne pèsent pas le même nombre de questions à l'examen réel (ni
dans les examens blancs de DOF-PREP, qui reproduisent fidèlement cette
pondération) : DOFD-3 et DOFD-4 sont les plus représentés, DOFD-7 le moins.
Voir `SPECIFICATIONS_FONCTIONNELLES.md` pour le détail chiffré exact.
