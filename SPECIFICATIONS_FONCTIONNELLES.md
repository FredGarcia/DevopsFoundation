# DOF-PREP — Spécifications fonctionnelles

## 0. Objet et méthode de lecture

Ce document décrit **ce que fait** DOF-PREP (comportement observable,
règles de gestion) indépendamment de son implémentation. Pour **comment**
c'est construit (architecture, formules, schémas de données, API), voir
`SPECIFICATIONS_TECHNIQUES.md`. Pour l'usage courant, voir `GUIDE_FORMATION.md`.

Chaque règle de gestion est numérotée (**RG-xx**) pour être référencée sans
ambiguïté ailleurs (tests, audit, évolutions futures).

---

## 1. Périmètre

### 1.1 Objectif du système

Fournir un outil de préparation **autonome, local et hors-ligne** à la
certification DevOps Foundation (DOFD v3.4, DevOps Institute), reproduisant
fidèlement le format et la pondération de l'examen officiel, avec un
accompagnement pédagogique (entraînement ciblé, révision espacée) et un
diagnostic de préparation.

### 1.2 Formes de livraison couvertes par ce document

Trois formes fonctionnellement équivalentes (même banque, mêmes règles de
gestion) : application Python (serveur local), fichier web autonome, et
application web installable (PWA). Une fonctionnalité additionnelle et
indépendante (assistant IA) est couverte en section 8.

### 1.3 Acteur

Un seul type d'acteur : **l'apprenant**, utilisateur unique de son instance de
l'application. Il n'y a pas de compte, pas de rôle, pas de notion
multi-utilisateur au sein d'une même instance (chaque installation a ses
propres données locales, non partagées).

### 1.4 Hors périmètre

- Délivrance officielle de la certification (DOF-PREP est un outil de
  préparation, pas un organisme certificateur).
- Synchronisation multi-appareils ou sauvegarde distante de la progression.
- Gestion de plusieurs profils d'apprenants sur une même installation.
- Correction ou modération humaine des questions générées par l'assistant IA
  avant affichage (la relecture reste à la charge de l'apprenant).

---

## 2. Référentiel de certification couvert

### 2.1 Format d'examen reproduit

| Caractéristique | Valeur |
|---|---|
| Nombre de questions par examen | 40 |
| Durée officielle de référence | 60 minutes |
| Seuil de réussite | 65 % |
| Pénalité de mauvaise réponse | Aucune |
| Documentation autorisée | Oui (open book) |

### 2.2 Domaines et pondération

| Domaine | Intitulé | Questions par examen (sur 40) | Questions dans la banque |
|---|---|---|---|
| DOFD-1 | Explorer le DevOps | 5 | 38 |
| DOFD-2 | Principes fondamentaux du DevOps (les Trois Voies) | 4 | 37 |
| DOFD-3 | Pratiques clés du DevOps | 7 | 45 |
| DOFD-4 | Cadres métier et techniques | 7 | 42 |
| DOFD-5 | Valeurs DevOps : culture, comportements et modèles opérationnels | 6 | 42 |
| DOFD-6 | Valeurs DevOps : automatisation et architecture des chaînes d'outils | 5 | 42 |
| DOFD-7 | Valeurs DevOps : mesure, métriques et reporting | 2 | 33 |
| DOFD-8 | Valeurs DevOps : partage, accompagnement et évolution | 4 | 36 |
| **Total** | | **40** | **315** |

**RG-01** — La somme des quotas par domaine, pour tout examen généré, est
toujours strictement égale à 40.

**RG-02** — La répartition des 40 questions entre les 8 domaines respecte la
pondération officielle ci-dessus pour tout examen généré (blanc prédéfini ou
libre), à l'unité de question près.

### 2.3 Métadonnées de chaque question

| Attribut | Valeurs possibles | Rôle fonctionnel |
|---|---|---|
| Domaine | DOFD-1 à DOFD-8 | Rattachement au référentiel officiel |
| Niveau de connaissance (k_level) | 1 à 7 | Classification pédagogique (rappel → analyse) |
| Difficulté | 1 (facile) à 5 (très difficile) | Sert à la génération d'examens par bande de niveau |
| Type | Choix unique / choix multiple / vrai-faux | Détermine la règle de correction applicable |
| Explication | Texte libre | Affichée après correction, à but pédagogique |

**RG-03** — Toute question de type « choix unique » ou « vrai/faux » possède
exactement une bonne réponse. Toute question de type « choix multiple »
possède au moins deux bonnes réponses. Toute question de type « vrai/faux »
possède exactement deux options.

---

## 3. Génération des examens

### 3.1 Examens blancs prédéfinis (« par donne »)

Le système propose **12 examens prédéfinis**, répartis en 3 niveaux de 4
examens chacun : **Moyen**, **Difficile**, **Très difficile**.

**RG-04** — Pour un niveau donné, les 4 examens prédéfinis ne partagent
**aucune question en commun** (recouvrement nul par construction). Un
apprenant peut donc passer les 4 examens d'un même niveau sans jamais revoir
une question déjà rencontrée à ce niveau.

**RG-05** — Chaque examen prédéfini respecte la pondération par domaine (RG-02)
et privilégie, dans la mesure du possible, des questions dont la difficulté
correspond à la bande du niveau demandé (Moyen : difficulté 2–3 ; Difficile :
3–4 ; Très difficile : 4–5), avec repli sur le reste de la banque si la bande
ne fournit pas assez de questions pour un domaine donné.

**RG-06** — Un même examen prédéfini (identifié par son numéro) génère
toujours exactement la même liste de questions, dans un ordre lui-même
reproductible (aucun aléa d'une exécution à l'autre pour un même identifiant
d'examen).

### 3.2 Examen libre

**RG-07** — L'examen libre génère, pour un niveau choisi, un examen de 40
questions respectant la pondération par domaine (RG-02) et privilégiant la
bande de difficulté du niveau choisi, avec un tirage différent à chaque
génération.

### 3.3 Correction

**RG-08** — Pour une question à choix unique ou vrai/faux, la réponse est
comptée juste si et seulement si l'unique bonne option est sélectionnée.

**RG-09** — Pour une question à choix multiple, la réponse est comptée juste
si et seulement si l'ensemble des options sélectionnées est **exactement**
égal à l'ensemble des bonnes options (un sous-ensemble incomplet, ou une
sélection incluant une mauvaise option, est compté faux dans son ensemble).

**RG-10** — Le score d'un examen est le rapport (nombre de réponses justes) /
(nombre total de questions), exprimé en pourcentage. Il n'y a pas de pénalité
pour une réponse fausse (RG issue du référentiel officiel, section 2.1).

**RG-11** — Un examen est déclaré « Réussite » si son score est supérieur ou
égal à 65 %, « Échec » sinon.

---

## 4. Suivi de la maîtrise et de la progression

### 4.1 Maîtrise par domaine

**RG-12** — Chaque réponse (en examen, entraînement, ou révision) met à jour
un indicateur de maîtrise par domaine, sous forme de moyenne mobile donnant
plus de poids aux réponses récentes qu'aux plus anciennes.

**RG-13** — Un domaine dont la maîtrise est strictement inférieure à 65 % est
considéré comme un **domaine faible**, signalé visuellement et repris dans les
recommandations.

### 4.2 Entraînement par domaine

**RG-14** — Le mode Entraînement présente les questions d'un seul domaine à la
fois, avec correction affichée **immédiatement** après chaque réponse
(contrairement à l'examen blanc, corrigé en fin de parcours).

### 4.3 Révision espacée

**RG-15** — Chaque question reçoit une échéance de révision individuelle,
recalculée après chaque réponse selon un algorithme de répétition espacée : une
réponse fausse ramène l'échéance au lendemain ; une réponse juste l'éloigne
progressivement (l'intervalle croît avec le nombre de répétitions réussies
consécutives).

**RG-16** — Le mode Révision ne présente que les questions dont l'échéance est
arrivée à échéance (aujourd'hui ou avant) au moment de la consultation.

### 4.4 Préparation globale (readiness)

**RG-17** — La préparation globale affichée est calculée comme la maîtrise
moyenne pondérée par les poids officiels des domaines (section 2.2),
elle-même pondérée par un facteur de confiance croissant avec le nombre total
de réponses enregistrées (peu de données ⇒ estimation prudente).

**RG-18** — Des recommandations textuelles sont générées automatiquement à
partir de l'état courant : domaines faibles à renforcer en priorité,
confirmation d'objectif atteint le cas échéant, ou invitation à accumuler
davantage de données si le volume de réponses est encore trop faible pour une
estimation fiable.

---

## 5. Calibration métacognitive (fonctionnalité optionnelle)

**RG-19** — Cette fonctionnalité est **désactivée par défaut** et ne modifie
aucun comportement tant qu'elle n'a pas été explicitement activée par
l'apprenant.

**RG-20** — Une fois activée, chaque réponse est accompagnée d'une estimation
de confiance déclarée par l'apprenant (parmi un jeu de valeurs prédéfinies),
recueillie *avant* que le résultat (juste/faux) ne soit connu.

**RG-21** — Le système calcule, à partir de l'historique de confiance
déclarée et de réussite effective : un score global de calibration, une
courbe de fiabilité par tranche de confiance, une tendance temporelle
(amélioration, dégradation, ou stabilité), et un détail par domaine.

**RG-22** — Un facteur de calibration, dérivé de l'écart entre confiance
déclarée et réussite effective, est appliqué à la préparation globale (RG-17)
lorsque cette fonctionnalité est active et qu'un volume minimal de données est
disponible. Ce facteur ne peut jamais faire descendre la préparation affichée
sous un plancher défini (voir `SPECIFICATIONS_TECHNIQUES.md` pour la valeur
exacte), afin de ne jamais produire une estimation démesurément décourageante
à partir de peu de signal.

---

## 6. Persistance et confidentialité

**RG-23** — Toutes les données de progression (maîtrise, échéances de
révision, historique d'examens, confiance déclarée) sont stockées
**localement sur l'appareil de l'apprenant**. Aucune donnée n'est transmise à
un tiers dans le fonctionnement normal de l'application.

**RG-24** — L'apprenant peut, à tout moment, réinitialiser intégralement sa
progression locale via une action explicite et confirmée (action
irréversible).

**RG-25** — Le fonctionnement de l'application ne requiert, à aucun moment, de
connexion réseau — à la seule exception de la fonctionnalité optionnelle
décrite en section 8, qui appelle un service tiers uniquement sur action
explicite de l'apprenant.

---

## 7. Exigences non fonctionnelles

**RG-26** — L'application doit rester utilisable sans connexion réseau après
son chargement initial (ou son installation, selon la forme de livraison).

**RG-27** — L'application ne requiert aucune dépendance d'exécution
extérieure à un interpréteur Python standard (forme A) ou à un navigateur web
standard (formes B et C) : aucune installation de paquet tiers n'est
nécessaire pour l'usage courant.

**RG-28** — La banque de questions (`questions.json`) constitue la source
unique de vérité, partagée à l'identique entre toutes les formes de livraison
(A, B, C) : toute modification de contenu doit s'appliquer de manière
cohérente à l'ensemble des formes déployées (voir procédure en
`INSTALLATION.md`, section 7).

---

## 8. Assistant IA (fonctionnalité optionnelle et indépendante)

### 8.1 Principe

**RG-29** — Cette fonctionnalité est **strictement optionnelle** : son
absence ne dégrade aucune autre fonctionnalité décrite dans ce document.
Elle nécessite un composant serveur local additionnel, exécuté volontairement
par l'apprenant, ainsi qu'une clé d'accès à un service tiers dont l'usage est
à la charge de l'apprenant.

### 8.2 Fonctions couvertes

**RG-30** — *Analyse des lacunes* : à la demande explicite de l'apprenant, une
synthèse textuelle de sa progression par domaine est générée, à partir des
seules données agrégées de maîtrise (aucune donnée personnelle identifiante
n'est transmise).

**RG-31** — *Proposition de questions* : à la demande explicite de
l'apprenant et pour un domaine choisi, de nouvelles questions candidates sont
générées, dans le même format que la banque officielle, puis **validées
automatiquement** (conformité du domaine, des bornes de difficulté, de la
règle de comptage des bonnes réponses par type) avant d'être présentées.

### 8.3 Garde-fous fonctionnels

**RG-32** — Les questions générées par l'assistant IA ne sont, en aucun cas et
à aucun moment, intégrées automatiquement à la banque officielle ni utilisées
dans la génération des examens blancs (prédéfinis ou libres) décrite en
section 3. Elles sont présentées comme candidates, explicitement signalées
comme non validées, et l'intégration éventuelle à la banque officielle est une
action manuelle et distincte de l'apprenant.

**RG-33** — Toute réponse générée par le service tiers qui ne respecte pas le
format attendu (section 2.3, RG-03) est rejetée avant affichage, avec un
message d'erreur explicite ; aucune question non conforme n'est jamais
présentée à l'apprenant.

---

## 9. Synthèse des règles de gestion

| Réf. | Résumé |
|---|---|
| RG-01 | Somme des quotas par domaine = 40 |
| RG-02 | Pondération par domaine respectée dans tout examen |
| RG-03 | Règles de comptage des bonnes réponses par type de question |
| RG-04 | Recouvrement nul entre les 4 examens d'un même niveau |
| RG-05 | Priorité à la bande de difficulté du niveau, avec repli |
| RG-06 | Reproductibilité d'un examen prédéfini donné |
| RG-07 | Examen libre : pondération respectée, tirage différent à chaque fois |
| RG-08/09 | Règle de correction single/truefalse (1 bonne réponse exacte) vs multiple (ensemble exact) |
| RG-10/11 | Calcul du score, seuil de réussite 65 % |
| RG-12/13 | Maîtrise par domaine (moyenne mobile), seuil de domaine faible 65 % |
| RG-14 | Correction immédiate en entraînement |
| RG-15/16 | Révision espacée : échéances et présentation du dû du jour |
| RG-17/18 | Calcul et usage de la préparation globale |
| RG-19 à RG-22 | Calibration métacognitive : opt-in, confiance déclarée, facteur borné |
| RG-23 à RG-25 | Persistance locale, réinitialisation, absence de réseau requis |
| RG-26 à RG-28 | Hors-ligne, zéro dépendance, source unique de la banque |
| RG-29 à RG-33 | Assistant IA : opt-in, portée limitée, jamais dans la banque officielle, validation stricte |
