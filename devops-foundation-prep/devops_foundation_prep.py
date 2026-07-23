#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOF-PREP — Plateforme de préparation à la certification DevOps Foundation (DOFD v3.4)

Application autoportée, ZERO dependance externe : uniquement la bibliotheque
standard de Python 3 (http.server, sqlite3, json, ...). SPA (HTML/CSS/JS)
embarquee. Fonctionne hors-ligne. Persistance SQLite.

Variables d'environnement :
  DOF_HOST           hote d'ecoute        (defaut: 127.0.0.1 ; Docker: 0.0.0.0)
  DOF_PORT           port                 (defaut: 8765)
  DOF_DB_PATH        chemin base SQLite   (defaut: ./dofprep.sqlite3)
  DOF_OPEN_BROWSER   ouvrir le navigateur (defaut: 1 ; Docker: 0)

Lancement :
  python3 devops_foundation_prep.py
"""

import os
import json
import math
import sqlite3
import hashlib
import secrets
import random
import threading
import webbrowser
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

HOST = os.environ.get("DOF_HOST", "127.0.0.1")
PORT = int(os.environ.get("DOF_PORT", "8765"))
DB_PATH = os.environ.get("DOF_DB_PATH", "dofprep.sqlite3")
OPEN_BROWSER = os.environ.get("DOF_OPEN_BROWSER", "1") == "1"

# Parametres officiels de reference (DOFD v3.4) — configurables en base.
CERT_CODE = "DOFD_V3_4"
CERT_LABEL = "DevOps Foundation (DevOps Institute) — v3.4"
PASS_THRESHOLD = 0.65          # seuil officiel
QUESTION_COUNT = 40            # questions par examen
DURATION_MIN = 60             # minutes

# Bornes du curseur de cible de reussite.
TARGET_MIN = 0.65
TARGET_MAX = 0.90
TARGET_DEFAULT = 0.90

# Nombre d'items repondus a partir duquel l'indicateur de preparation atteint
# sa pleine confiance.
DATA_CONFIDENCE_THRESHOLD = 80

# Seuil de maitrise par domaine en deca duquel un domaine est juge faible.
DOMAIN_FLOOR = 0.65

# --------------------------------------------------------------------------- #
# Couche de second ordre (cybernetique des systemes observants) — OPTIONNELLE  #
# Le systeme observe sa propre observation : calibration metacognitive de      #
# l'apprenant et auto-calibration de l'instrument de mesure (difficulte des    #
# items, facteur de confiance de la preparation). Desactivee par defaut.       #
# Les parametres de la boucle sont pilotables par variables d'environnement    #
# (bornes de surete appliquees) et documentes dans .env.example.               #
# --------------------------------------------------------------------------- #
def _env_float(name, default, lo, hi):
    try:
        v = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


def _env_int(name, default, lo, hi):
    try:
        v = int(float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


SECOND_ORDER_DEFAULT = os.environ.get("DOF_SECOND_ORDER", "0") == "1"
# Nombre minimal de predictions de confiance avant que la calibration n'influe
# sur la preparation (anti-oscillation : on n'agit pas sur trop peu de donnees).
CALIB_MIN_RECORDS = _env_int("DOF_CALIB_MIN_RECORDS", 20, 1, 100000)
# Plancher du facteur de calibration : la boucle reflexive peut amortir la
# preparation, jamais l'effondrer (borne dure dans [0,1]).
CALIB_FLOOR = _env_float("DOF_CALIB_FLOOR", 0.60, 0.0, 1.0)
# Gain (amortissement) de la mise a jour mutuelle aptitude<->difficulte (Elo
# leger sur echelle logit) : volontairement faible pour eviter les a-coups.
ELO_K = _env_float("DOF_ELO_K", 0.08, 0.0, 1.0)
# Echelle reliant la difficulte editoriale (1..5) a la difficulte latente.
DIFF_LOGIT_SCALE = 0.85
# Niveaux de confiance proposes a l'apprenant (probabilite de reussite, en %).
CONFIDENCE_CHOICES = [25, 50, 75, 95]

# --------------------------------------------------------------------------- #
# Domaines — PONDERATIONS OFFICIELLES (DevOps Institute, blueprint DOFD).      #
# Exprimees en nombre maximal de questions par domaine sur 40 (somme = 40,     #
# soit 100 %). Source : DevOps Institute, DevOps Foundation Examination        #
# Requirements (« Exam Topic Areas and Question Weighting ») :                 #
#   DOFD-1=5  DOFD-2=4  DOFD-3=7  DOFD-4=7  DOFD-5=6  DOFD-6=5  DOFD-7=2  DOFD-8=4
# --------------------------------------------------------------------------- #

DOMAINS = [
    ("DOFD-1", "Explorer le DevOps", 5 / 40),
    ("DOFD-2", "Principes fondamentaux du DevOps (les Trois Voies)", 4 / 40),
    ("DOFD-3", "Pratiques cles du DevOps", 7 / 40),
    ("DOFD-4", "Cadres metier et techniques", 7 / 40),
    ("DOFD-5", "Valeurs DevOps : culture, comportements et modeles operationnels", 6 / 40),
    ("DOFD-6", "Valeurs DevOps : automatisation et architecture des chaines d'outils", 5 / 40),
    ("DOFD-7", "Valeurs DevOps : mesure, metriques et reporting", 2 / 40),
    ("DOFD-8", "Valeurs DevOps : partage, accompagnement et evolution", 4 / 40),
]

# --------------------------------------------------------------------------- #
# Banque de questions originales (francais)                                   #
# Chaque entree : (domaine, niveau_K, difficulte 1-5, type, enonce,           #
#                  [(texte_option, est_correcte), ...], explication)          #
# type : 'single' (1 bonne), 'multiple' (>=1 bonnes), 'truefalse'             #
# --------------------------------------------------------------------------- #

QUESTIONS = [
    # ----------------------------- DOFD-1 ---------------------------------- #
    ("DOFD-1", 1, 1, "single",
     "Comment definit-on le mieux DevOps ?",
     [("Un ensemble d'outils a installer pour automatiser les serveurs", False),
      ("Une culture, des pratiques et des outils alignant le developpement et les operations", True),
      ("Un nouveau poste remplacant les administrateurs systeme", False),
      ("Une methodologie de gestion de projet remplacant Scrum", False)],
     "DevOps n'est pas un outil ni un poste : c'est l'alliance d'une culture, de pratiques et d'outils visant a aligner Dev et Ops."),

    ("DOFD-1", 1, 2, "single",
     "Quel est l'objectif central de DevOps ?",
     [("Supprimer l'equipe des operations", False),
      ("Reduire le delai entre une idee/un commit et sa mise en production fiable", True),
      ("Ecrire davantage de documentation", False),
      ("Augmenter le nombre de reunions de coordination", False)],
     "DevOps cherche a livrer de la valeur plus vite ET de maniere fiable, en raccourcissant le delai de bout en bout."),

    ("DOFD-1", 1, 2, "truefalse",
     "Le « mur de la confusion » (wall of confusion) designe la friction et le rejet de responsabilite entre les equipes Dev et Ops.",
     [("Vrai", True), ("Faux", False)],
     "Le wall of confusion illustre le cloisonnement Dev/Ops que DevOps cherche a abattre."),

    ("DOFD-1", 1, 1, "truefalse",
     "DevOps est avant tout un changement culturel, pas uniquement l'achat d'un outillage.",
     [("Vrai", True), ("Faux", False)],
     "La culture (collaboration, responsabilite partagee) prime ; l'outillage la soutient mais ne la remplace pas."),

    ("DOFD-1", 1, 3, "single",
     "Quel evenement/mouvement est associe a l'emergence du terme DevOps (vers 2009) ?",
     [("La sortie de Kubernetes", False),
      ("Les premiers DevOpsDays inities notamment par Patrick Debois", True),
      ("La publication du Manifeste Agile", False),
      ("La creation de Git", False)],
     "Le terme s'est popularise avec les DevOpsDays (Patrick Debois, 2009)."),

    ("DOFD-1", 2, 2, "multiple",
     "Quels benefices sont typiquement attribues a une adoption reussie de DevOps ?",
     [("Deploiements plus frequents", True),
      ("Delai de mise en production plus court", True),
      ("Temps de retablissement (MTTR) plus court", True),
      ("Augmentation systematique du taux d'echec des changements", False)],
     "DevOps vise plus de frequence, moins de delai, un retablissement plus rapide ET un taux d'echec plus bas."),

    # ----------------------------- DOFD-2 ---------------------------------- #
    ("DOFD-2", 1, 2, "single",
     "Que privilegie la Premiere Voie (The First Way) ?",
     [("Le flux de gauche a droite, du developpement vers la production", True),
      ("Les boucles de retroaction de droite a gauche", False),
      ("L'experimentation et l'apprentissage continus", False),
      ("La suppression des tests automatises", False)],
     "La Premiere Voie concerne le flux rapide et fluide du travail, du Dev vers le client."),

    ("DOFD-2", 1, 2, "single",
     "Sur quoi insiste la Deuxieme Voie (The Second Way) ?",
     [("Le flux de gauche a droite", False),
      ("L'amplification des boucles de retroaction (feedback) de droite a gauche", True),
      ("La reduction du nombre de deploiements", False),
      ("L'externalisation des operations", False)],
     "La Deuxieme Voie amplifie et raccourcit les boucles de retroaction pour corriger au plus tot."),

    ("DOFD-2", 1, 2, "single",
     "Que recouvre la Troisieme Voie (The Third Way) ?",
     [("La culture de l'apprentissage continu et de l'experimentation", True),
      ("La centralisation des decisions", False),
      ("La suppression des post-mortems", False),
      ("Le gel des changements en production", False)],
     "La Troisieme Voie cultive l'apprentissage continu, l'experimentation et la prise de risque maitrisee."),

    ("DOFD-2", 2, 3, "single",
     "Selon la Theorie des Contraintes (Goldratt), pour ameliorer le debit d'un systeme il faut d'abord :",
     [("Optimiser chaque etape independamment", False),
      ("Identifier et exploiter la contrainte (le goulot d'etranglement)", True),
      ("Ajouter du travail en cours partout", False),
      ("Supprimer toute forme de mesure", False)],
     "Optimiser ailleurs que le goulot ne sert a rien : on concentre l'effort sur la contrainte du systeme."),

    ("DOFD-2", 2, 3, "multiple",
     "Quelles pratiques relevent de la Premiere Voie (flux) ?",
     [("Rendre le travail visible", True),
      ("Limiter le travail en cours (WIP)", True),
      ("Reduire la taille des lots de travail", True),
      ("Multiplier les transferts (hand-offs) entre equipes", False)],
     "Visibilite, limitation du WIP et petits lots fluidifient le flux ; multiplier les hand-offs le degrade."),

    ("DOFD-2", 2, 3, "single",
     "Dans une organisation apprenante, comment traite-t-on un incident ?",
     [("En cherchant un coupable a sanctionner", False),
      ("Par un post-mortem sans blame, axe sur l'apprentissage systemique", True),
      ("En ignorant l'incident s'il est resolu", False),
      ("En interdisant tout nouveau deploiement", False)],
     "La culture juste privilegie l'apprentissage et la correction des causes systemiques plutot que le blame."),

    ("DOFD-2", 2, 2, "multiple",
     "Quels sont des « types de travail » identifies dans The Phoenix Project ?",
     [("Projets metier", True),
      ("Projets internes (IT)", True),
      ("Changements", True),
      ("Travail non planifie", True)],
     "Les quatre types : projets metier, projets internes, changements, et travail non planifie."),

    ("DOFD-2", 1, 2, "truefalse",
     "Reduire la taille des lots (small batches) ameliore le flux et accelere la retroaction.",
     [("Vrai", True), ("Faux", False)],
     "De petits lots reduisent les risques, accelerent le retour d'information et fluidifient le flux."),

    # ----------------------------- DOFD-3 ---------------------------------- #
    ("DOFD-3", 1, 1, "single",
     "Que designe l'acronyme CALMS ?",
     [("Culture, Automation, Lean, Measurement, Sharing", True),
      ("Cloud, Agile, Lean, Monitoring, Security", False),
      ("Continuous, Automated, Logging, Metrics, Scaling", False),
      ("Culture, Agile, Learning, Metrics, Standards", False)],
     "CALMS = Culture, Automation, Lean, Measurement, Sharing."),

    ("DOFD-3", 1, 2, "single",
     "Dans CALMS, que recouvre le « M » ?",
     [("Monitoring uniquement", False),
      ("Measurement (la mesure pour piloter l'amelioration)", True),
      ("Microservices", False),
      ("Management", False)],
     "Le M est Measurement : mesurer pour decider et s'ameliorer en continu."),

    ("DOFD-3", 2, 2, "single",
     "Qu'est-ce que l'integration continue (CI) ?",
     [("Deployer automatiquement en production a chaque commit", False),
      ("Fusionner frequemment le code dans une branche commune, avec build et tests automatises", True),
      ("Geler les fusions pendant un sprint", False),
      ("Ecrire le code sans tests", False)],
     "La CI consiste a integrer souvent le code, valide automatiquement par build et tests."),

    ("DOFD-3", 3, 3, "single",
     "Quelle est la difference entre livraison continue et deploiement continu ?",
     [("Aucune, ce sont des synonymes", False),
      ("La livraison continue rend chaque version deployable (mise en prod sur decision) ; le deploiement continu met automatiquement en production", True),
      ("Le deploiement continu n'utilise pas de tests", False),
      ("La livraison continue interdit l'automatisation", False)],
     "Livraison continue = toujours pret a deployer (declenchement manuel) ; deploiement continu = mise en prod automatique."),

    ("DOFD-3", 2, 3, "multiple",
     "Quelles etapes trouve-t-on typiquement dans un pipeline de deploiement ?",
     [("Build (compilation/empaquetage)", True),
      ("Tests automatises", True),
      ("Deploiement vers des environnements", True),
      ("Suppression de la gestion de versions", False)],
     "Un pipeline enchaine build, tests et deploiements ; la gestion de versions en est le socle."),

    ("DOFD-3", 3, 4, "single",
     "En SRE, que represente un « error budget » (budget d'erreur) ?",
     [("Le budget financier de l'equipe", False),
      ("La marge d'indisponibilite toleree, derivee de l'objectif de service (SLO)", True),
      ("Le nombre de tickets ouverts", False),
      ("Le delai de paie des astreintes", False)],
     "Le budget d'erreur = 1 - SLO ; il arbitre entre vitesse de livraison et fiabilite."),

    ("DOFD-3", 2, 3, "multiple",
     "Quels sont les trois piliers de l'observabilite ?",
     [("Les logs (journaux)", True),
      ("Les metriques", True),
      ("Les traces", True),
      ("Les sauvegardes hebdomadaires", False)],
     "Observabilite : logs, metriques et traces (les sauvegardes n'en font pas partie)."),

    ("DOFD-3", 2, 2, "single",
     "Que recommande la « pyramide des tests » ?",
     [("Surtout des tests manuels en fin de cycle", False),
      ("Beaucoup de tests unitaires rapides a la base, moins de tests d'integration, peu de tests bout-en-bout", True),
      ("Uniquement des tests d'interface graphique", False),
      ("Aucun test automatise", False)],
     "On privilegie une large base de tests unitaires rapides, et on limite les tests E2E plus lents et fragiles."),

    ("DOFD-3", 2, 3, "single",
     "A quoi servent les « feature flags » (drapeaux de fonctionnalite) ?",
     [("A supprimer les tests", False),
      ("A activer/desactiver des fonctionnalites en production sans redeployer", True),
      ("A empecher les fusions de code", False),
      ("A chiffrer la base de donnees", False)],
     "Les feature flags decouplent le deploiement de la mise a disposition d'une fonctionnalite."),

    ("DOFD-3", 2, 2, "truefalse",
     "Le principe « shift left » consiste a integrer les tests et la qualite au plus tot dans le cycle.",
     [("Vrai", True), ("Faux", False)],
     "« Decaler a gauche » rapproche tests, securite et qualite des phases initiales."),

    # ----------------------------- DOFD-4 ---------------------------------- #
    ("DOFD-4", 1, 2, "single",
     "Que cherche a eliminer la pensee Lean ?",
     [("La documentation", False),
      ("Le gaspillage (muda), c'est-a-dire toute activite sans valeur ajoutee", True),
      ("Les tests automatises", False),
      ("La collaboration", False)],
     "Lean traque le gaspillage afin de maximiser la valeur livree au client."),

    ("DOFD-4", 1, 2, "single",
     "Que designe le Kaizen ?",
     [("Une suppression des processus", False),
      ("L'amelioration continue par petites etapes", True),
      ("Un type de serveur", False),
      ("Un langage de programmation", False)],
     "Kaizen = amelioration continue, incrementale et participative."),

    ("DOFD-4", 1, 2, "multiple",
     "Quelles valeurs figurent dans le Manifeste Agile ?",
     [("Les individus et leurs interactions plus que les processus et les outils", True),
      ("Un logiciel operationnel plus qu'une documentation exhaustive", True),
      ("La collaboration avec le client plus que la negociation contractuelle", True),
      ("Le respect strict du plan initial plus que l'adaptation au changement", False)],
     "Le Manifeste valorise notamment l'adaptation au changement plutot que le suivi rigide d'un plan."),

    ("DOFD-4", 2, 2, "truefalse",
     "DevOps et l'ITSM (gestion des services IT) sont complementaires et peuvent coexister.",
     [("Vrai", True), ("Faux", False)],
     "DevOps s'integre aux pratiques ITSM (incidents, changements, services) plutot que de les exclure."),

    ("DOFD-4", 3, 3, "single",
     "Quel est le but principal du Value Stream Mapping ?",
     [("Dessiner l'organigramme de l'entreprise", False),
      ("Visualiser le flux de valeur pour reperer goulots, attentes et gaspillages", True),
      ("Lister les serveurs de production", False),
      ("Planifier les conges", False)],
     "Le VSM cartographie le flux de bout en bout afin d'identifier ou la valeur est ralentie ou gaspillee."),

    ("DOFD-4", 2, 3, "single",
     "Pourquoi reduire la taille des lots est-il benefique (theorie des files d'attente) ?",
     [("Cela augmente les delais", False),
      ("Cela reduit le temps d'attente, accelere la retroaction et diminue le risque", True),
      ("Cela supprime le besoin de tests", False),
      ("Cela complexifie le deploiement", False)],
     "De petits lots reduisent l'en-cours, donc l'attente, et rendent les problemes plus faciles a localiser."),

    ("DOFD-4", 2, 3, "single",
     "Qu'apporte un financement oriente « produit » plutot que « projet » ?",
     [("Des equipes durables centrees sur un produit et un flux de valeur continu", True),
      ("Des equipes dissoutes a chaque livraison", False),
      ("La suppression de toute mesure de valeur", False),
      ("Un gel des budgets", False)],
     "Le financement produit soutient des equipes stables et un flux de valeur continu, contrairement au mode projet temporaire."),

    # ----------------------------- DOFD-5 ---------------------------------- #
    ("DOFD-5", 2, 3, "single",
     "Qu'est-ce qu'une « culture juste » (just culture) ?",
     [("Une culture qui sanctionne systematiquement les erreurs", False),
      ("Une culture qui apprend des erreurs sans chercher de bouc emissaire", True),
      ("Une culture interdisant les changements", False),
      ("Une culture sans aucune regle", False)],
     "La culture juste equilibre responsabilite et apprentissage, sans blame destructeur."),

    ("DOFD-5", 3, 4, "single",
     "Dans le modele de Westrum, comment circule l'information dans une organisation « generative » ?",
     [("Elle est dissimulee", False),
      ("Elle circule activement et la cooperation est recherchee", True),
      ("Elle est reservee a la hierarchie", False),
      ("Elle est ignoree", False)],
     "Les cultures generatives favorisent une circulation fluide de l'information et une forte cooperation."),

    ("DOFD-5", 2, 3, "single",
     "Que signifie le principe « you build it, you run it » ?",
     [("Les developpeurs n'ont aucune responsabilite en production", False),
      ("L'equipe qui construit le service est aussi responsable de son exploitation", True),
      ("Seuls les Ops deploient", False),
      ("Le code n'est jamais surveille", False)],
     "Ce principe responsabilise les equipes de bout en bout, du build a l'exploitation."),

    ("DOFD-5", 3, 4, "single",
     "Que dit la loi de Conway ?",
     [("Les systemes refletent la structure de communication de l'organisation qui les conçoit", True),
      ("Tout systeme finit par tomber en panne", False),
      ("Le code double de taille chaque annee", False),
      ("Les reunions ralentissent les projets", False)],
     "Loi de Conway : l'architecture logicielle tend a copier les structures de communication de l'organisation."),

    ("DOFD-5", 2, 3, "multiple",
     "Quels types d'equipes propose le modele Team Topologies ?",
     [("Alignee sur le flux (stream-aligned)", True),
      ("Plateforme (platform)", True),
      ("Habilitante (enabling)", True),
      ("Hierarchique pyramidale stricte", False)],
     "Team Topologies decrit 4 types : stream-aligned, platform, enabling et complicated-subsystem."),

    ("DOFD-5", 2, 3, "truefalse",
     "La securite psychologique favorise la prise de parole, l'experimentation et l'apprentissage des erreurs.",
     [("Vrai", True), ("Faux", False)],
     "Sans peur de represailles, les equipes signalent les problemes et apprennent plus vite."),

    ("DOFD-5", 3, 3, "single",
     "Quel facteur est determinant pour reussir un changement culturel DevOps ?",
     [("L'achat d'un nouvel outil uniquement", False),
      ("Un soutien visible du leadership et l'implication des equipes", True),
      ("Le gel de toute communication", False),
      ("La suppression des retrospectives", False)],
     "Le changement culturel reussit avec un leadership engage et la participation des equipes."),

    # ----------------------------- DOFD-6 ---------------------------------- #
    ("DOFD-6", 2, 2, "single",
     "Qu'est-ce que l'Infrastructure as Code (IaC) ?",
     [("Configurer les serveurs manuellement", False),
      ("Decrire et provisionner l'infrastructure via du code versionne et reproductible", True),
      ("Stocker les mots de passe en clair", False),
      ("Une base de donnees relationnelle", False)],
     "L'IaC traite l'infrastructure comme du code : versionnee, testable, reproductible et idempotente."),

    ("DOFD-6", 2, 3, "single",
     "A quoi servent les outils de gestion de configuration (Ansible, Puppet, Chef) ?",
     [("A ecrire du code applicatif", False),
      ("A garantir un etat cible coherent et reproductible des systemes", True),
      ("A remplacer le controle de version", False),
      ("A chiffrer les disques uniquement", False)],
     "Ils assurent que les systemes convergent vers un etat desire, de maniere idempotente."),

    ("DOFD-6", 2, 2, "single",
     "Quel avantage majeur apportent les conteneurs (ex. Docker) ?",
     [("Empaqueter l'application et ses dependances pour une execution coherente et portable", True),
      ("Supprimer le besoin de tests", False),
      ("Ralentir les deploiements", False),
      ("Empecher l'automatisation", False)],
     "Les conteneurs offrent une isolation legere et une portabilite coherente entre environnements."),

    ("DOFD-6", 3, 3, "single",
     "Quel est le role d'un orchestrateur comme Kubernetes ?",
     [("Editer le code source", False),
      ("Deployer, mettre a l'echelle et gerer des conteneurs sur un cluster", True),
      ("Compiler les binaires", False),
      ("Stocker les journaux uniquement", False)],
     "Kubernetes orchestre le cycle de vie, la mise a l'echelle et la resilience des conteneurs."),

    ("DOFD-6", 2, 3, "multiple",
     "Quelles categories d'outils compose-t-on dans une chaine d'outils DevOps (toolchain) ?",
     [("Gestion de versions / source", True),
      ("Build et integration continue", True),
      ("Surveillance et observabilite", True),
      ("Traitement de texte de bureautique", False)],
     "Une toolchain couvre source, build/CI, tests, deploiement, exploitation et observabilite."),

    ("DOFD-6", 2, 2, "single",
     "Lequel de ces outils est un moteur d'integration/livraison continue ?",
     [("PostgreSQL", False),
      ("GitLab CI / Jenkins / GitHub Actions", True),
      ("Microsoft Word", False),
      ("Photoshop", False)],
     "Jenkins, GitLab CI et GitHub Actions automatisent build, tests et deploiement."),

    ("DOFD-6", 3, 3, "truefalse",
     "L'infrastructure immuable consiste a remplacer les composants plutot qu'a les modifier en place.",
     [("Vrai", True), ("Faux", False)],
     "On redeploie une nouvelle version coherente au lieu de patcher l'existant, ce qui reduit la derive de configuration."),

    ("DOFD-6", 3, 4, "single",
     "Que promeut l'approche DevSecOps / « shift-left security » ?",
     [("Tester la securite uniquement apres la mise en production", False),
      ("Integrer la securite tot et tout au long du pipeline (gestion des secrets, analyses automatisees)", True),
      ("Supprimer les controles de securite", False),
      ("Confier la securite a une seule personne en fin de cycle", False)],
     "DevSecOps integre la securite des le debut et l'automatise dans le pipeline."),

    # ----------------------------- DOFD-7 ---------------------------------- #
    ("DOFD-7", 2, 2, "multiple",
     "Quelles sont les quatre metriques cles DORA ?",
     [("Frequence de deploiement", True),
      ("Delai des changements (lead time for changes)", True),
      ("Taux d'echec des changements", True),
      ("Temps de retablissement du service (MTTR)", True)],
     "Les 4 metriques DORA : frequence de deploiement, delai des changements, taux d'echec, et temps de retablissement."),

    ("DOFD-7", 2, 3, "single",
     "Que mesure le « lead time for changes » ?",
     [("Le temps entre un commit et sa mise en production", True),
      ("Le nombre de bugs ouverts", False),
      ("La duree des reunions", False),
      ("Le cout des licences", False)],
     "Le delai des changements mesure le temps du code valide jusqu'a la production."),

    ("DOFD-7", 1, 2, "single",
     "Que mesure la « frequence de deploiement » ?",
     [("La taille des equipes", False),
      ("La frequence a laquelle l'organisation deploie en production", True),
      ("Le nombre de serveurs", False),
      ("Le nombre de tickets fermes", False)],
     "Elle indique a quelle cadence on livre en production (indicateur de debit/flux)."),

    ("DOFD-7", 2, 3, "single",
     "Que mesure le « change failure rate » (taux d'echec des changements) ?",
     [("Le pourcentage de deploiements qui provoquent une degradation necessitant une remediation", True),
      ("Le nombre total de deploiements", False),
      ("La vitesse du reseau", False),
      ("Le nombre de developpeurs", False)],
     "C'est la part des changements qui echouent en production et exigent un correctif/rollback."),

    ("DOFD-7", 2, 3, "single",
     "Que designe le MTTR dans le contexte DORA / fiabilite ?",
     [("Le temps moyen pour restaurer le service apres un incident", True),
      ("Le temps moyen entre deux reunions", False),
      ("Le nombre moyen de tests", False),
      ("La moyenne des salaires", False)],
     "Le temps de retablissement mesure la rapidite a restaurer le service apres une defaillance."),

    ("DOFD-7", 2, 2, "truefalse",
     "On distingue les metriques « actionnables » des « vanity metrics » qui flattent mais n'orientent aucune decision.",
     [("Vrai", True), ("Faux", False)],
     "Les bonnes metriques guident une action ; les vanity metrics impressionnent sans eclairer de decision."),

    # ----------------------------- DOFD-8 ---------------------------------- #
    ("DOFD-8", 1, 2, "single",
     "Que recouvre le « S » de CALMS ?",
     [("Security", False),
      ("Sharing : le partage des connaissances, retours et bonnes pratiques", True),
      ("Scaling", False),
      ("Scheduling", False)],
     "Le S est Sharing : partager savoirs et retours pour diffuser l'amelioration."),

    ("DOFD-8", 2, 3, "single",
     "Qu'est-ce que le ChatOps ?",
     [("Un chatbot de support client uniquement", False),
      ("Piloter des operations et l'automatisation depuis un outil de discussion partage, de maniere tracable", True),
      ("Une messagerie chiffree sans automatisation", False),
      ("Un protocole reseau", False)],
     "ChatOps rapproche conversations, outils et automatisation dans un canal partage et historise."),

    ("DOFD-8", 2, 3, "single",
     "A quoi servent les communautes de pratique (CoP) ?",
     [("A isoler les equipes", False),
      ("A partager savoir-faire et standards entre equipes, au-dela des silos", True),
      ("A supprimer la documentation", False),
      ("A interdire l'experimentation", False)],
     "Les CoP diffusent connaissances et pratiques entre equipes et renforcent l'apprentissage collectif."),

    ("DOFD-8", 3, 3, "truefalse",
     "A l'echelle de l'entreprise, un centre d'excellence ou une plateforme interne peut accelerer l'adoption de DevOps.",
     [("Vrai", True), ("Faux", False)],
     "Centres d'excellence et plateformes internes diffusent pratiques et outils a grande echelle."),

    ("DOFD-8", 3, 4, "single",
     "Comment fait-on evoluer durablement les pratiques DevOps ?",
     [("En figeant definitivement les processus", False),
      ("Par l'experimentation continue, la mesure et l'amelioration iterative (esprit Kata/Kaizen)", True),
      ("En supprimant les retours d'experience", False),
      ("En cessant de mesurer", False)],
     "L'evolution durable repose sur des cycles d'experimentation, de mesure et d'amelioration continue."),

    # ======================================================================= #
    # Banque etoffee — questions supplementaires                              #
    # (memes regles : domaine, K, difficulte, type, enonce, options, expl.)   #
    # ======================================================================= #

    # ----------------------------- DOFD-1 ---------------------------------- #
    ("DOFD-1", 2, 2, "single",
     "Quels gains chiffres le DevOps vise-t-il typiquement pour l'entreprise ?",
     [("Reduction des couts IT, baisse du taux d'echec des changements et delais de mise a disposition plus courts", True),
      ("Augmentation des couts et baisse de la qualite", False),
      ("Aucun impact mesurable sur l'activite", False),
      ("Uniquement une reduction des effectifs", False)],
     "Le DevOps vise a la fois reduction des couts, meilleure qualite (moins d'echecs) et plus d'agilite (delais plus courts)."),

    ("DOFD-1", 1, 2, "single",
     "Quel est l'apport principal du DevOps vis-a-vis des silos organisationnels ?",
     [("Renforcer la separation entre Dev et Ops", False),
      ("Instaurer une responsabilite partagee et une collaboration entre Dev et Ops", True),
      ("Supprimer toute communication", False),
      ("Confier toute la responsabilite a un seul service", False)],
     "Le DevOps abat les silos en instaurant collaboration et responsabilite partagee de bout en bout."),

    ("DOFD-1", 1, 2, "single",
     "Dans le vocabulaire DevOps, que designe « Ops » ?",
     [("Les activites operationnelles de deploiement et d'exploitation des systemes et services", True),
      ("Uniquement les developpeurs front-end", False),
      ("Le service commercial", False),
      ("Les utilisateurs finaux", False)],
     "« Ops » regroupe les activites d'exploitation : mise en production, administration, supervision des services."),

    ("DOFD-1", 1, 2, "single",
     "Qu'est-ce qu'un « anti-pattern » (anti-modele) ?",
     [("Une bonne pratique reconnue", False),
      ("Une solution frequemment reinventee mais inefficace a un probleme", True),
      ("Un outil de supervision", False),
      ("Un type de conteneur", False)],
     "Un anti-pattern est une reponse courante mais mauvaise a un probleme recurrent."),

    ("DOFD-1", 2, 3, "single",
     "Laquelle de ces affirmations sur le DevOps est exacte ?",
     [("Le DevOps est uniquement un logiciel a acheter", False),
      ("Le DevOps est un mouvement culturel et professionnel, pas un produit ni un simple titre de poste", True),
      ("Le DevOps est une norme ISO obligatoire", False),
      ("Le DevOps remplace integralement l'Agile", False)],
     "Le DevOps est un mouvement culturel et professionnel ; ce n'est ni un produit, ni un simple poste, ni une norme."),

    ("DOFD-1", 2, 3, "truefalse",
     "Selon les etudes State of DevOps, les organisations tres performantes deploient plus souvent tout en ayant un taux d'echec des changements plus faible.",
     [("Vrai", True), ("Faux", False)],
     "Les organisations elites combinent frequence elevee de deploiement ET faible taux d'echec : vitesse et stabilite vont de pair."),

    ("DOFD-1", 1, 2, "single",
     "Comment le DevOps se situe-t-il par rapport a l'Agile et au Lean ?",
     [("Il s'oppose a l'Agile et au Lean", False),
      ("Il prolonge et s'appuie sur les principes Agile et Lean", True),
      ("Il les rend inutiles", False),
      ("Il n'a aucun lien avec eux", False)],
     "Le DevOps etend Agile et Lean a l'exploitation, en s'appuyant sur leurs principes (flux, valeur, iterations)."),

    ("DOFD-1", 2, 3, "single",
     "Que recommande le « Cercle d'Or » (Golden Circle) de Simon Sinek ?",
     [("Commencer par le « pourquoi » avant le « comment » et le « quoi »", True),
      ("Commencer par le « quoi » et ignorer le « pourquoi »", False),
      ("Supprimer toute vision", False),
      ("Se concentrer uniquement sur les outils", False)],
     "Le Golden Circle invite a partir du « pourquoi » pour donner du sens, avant le comment et le quoi."),

    # ----------------------------- DOFD-2 ---------------------------------- #
    ("DOFD-2", 1, 2, "single",
     "Dans quel ouvrage les « Trois Voies » (The Three Ways) sont-elles popularisees ?",
     [("The Phoenix Project / The DevOps Handbook (Gene Kim et al.)", True),
      ("Le Manifeste Agile", False),
      ("La documentation de Kubernetes", False),
      ("ITIL v3", False)],
     "Les Trois Voies sont issues du Phoenix Project et detaillees dans le DevOps Handbook (Gene Kim et coauteurs)."),

    ("DOFD-2", 2, 3, "multiple",
     "Quelles pratiques illustrent la Troisieme Voie (apprentissage et experimentation) ?",
     [("Mener des post-mortems sans blame", True),
      ("Injecter des pannes pour renforcer la resilience (ex. Chaos Monkey)", True),
      ("Allouer du temps a l'amelioration et a l'apprentissage", True),
      ("Interdire toute prise de risque", False)],
     "La Troisieme Voie encourage l'experimentation, l'apprentissage des echecs et la repetition deliberee."),

    ("DOFD-2", 2, 3, "single",
     "Que dit la Theorie des Contraintes a propos des ameliorations hors du goulot ?",
     [("Elles sont prioritaires", False),
      ("Toute amelioration qui ne porte pas sur la contrainte n'est qu'une illusion d'amelioration", True),
      ("Elles doublent toujours le debit", False),
      ("Elles eliminent la contrainte automatiquement", False)],
     "Goldratt : optimiser ailleurs que la contrainte ne fait pas progresser le debit global du systeme."),

    ("DOFD-2", 3, 3, "single",
     "Que relie la loi de Little (Little's Law) ?",
     [("Le nombre moyen d'elements en cours, le taux d'arrivee et le temps de presence dans le systeme", True),
      ("La taille du code et le nombre de bugs", False),
      ("Le nombre de serveurs et la latence reseau", False),
      ("Le budget et le nombre de reunions", False)],
     "Little : en-cours moyen = taux d'arrivee x temps moyen passe dans le systeme ; reduire l'en-cours reduit le temps de cycle."),

    ("DOFD-2", 2, 2, "single",
     "Que privilegie la pensee systemique mise en avant par la Premiere Voie ?",
     [("L'optimisation locale de chaque silo", False),
      ("La performance du systeme global de bout en bout plutot que d'un seul maillon", True),
      ("La suppression des mesures", False),
      ("La multiplication des transferts", False)],
     "La Premiere Voie regarde le flux complet de bout en bout, pas l'optimisation isolee d'un maillon."),

    ("DOFD-2", 2, 3, "single",
     "Que permet un mecanisme de type « cordon Andon » dans une culture DevOps ?",
     [("Masquer les defauts", False),
      ("Arreter le flux et mobiliser l'aide des qu'un probleme est detecte", True),
      ("Accelerer sans aucun controle", False),
      ("Supprimer les tests", False)],
     "L'Andon autorise a stopper la ligne et a converger sur le probleme immediatement (retroaction rapide)."),

    # ----------------------------- DOFD-3 ---------------------------------- #
    ("DOFD-3", 2, 2, "single",
     "Qu'est-ce que le test continu (continuous testing) ?",
     [("Tester uniquement a la fin du projet", False),
      ("Executer des tests automatises tout au long du pipeline pour un retour rapide sur la qualite", True),
      ("Supprimer les tests pour aller plus vite", False),
      ("Tester seulement en production", False)],
     "Le test continu integre des tests automatises a chaque etape du pipeline pour un retour qualite immediat."),

    ("DOFD-3", 3, 3, "single",
     "Qu'est-ce que le deploiement continu (continuous deployment) ?",
     [("Chaque changement validant les tests automatises est deploye automatiquement en production", True),
      ("Un deploiement manuel une fois par an", False),
      ("Un gel des deploiements", False),
      ("Le deploiement sans aucun test", False)],
     "En deploiement continu, tout changement passant les tests est mis en production sans intervention manuelle."),

    ("DOFD-3", 2, 3, "single",
     "Quel est le but d'un pipeline de deploiement (deployment pipeline) ?",
     [("Ralentir les livraisons", False),
      ("Acheminer un changement par etapes automatisees jusqu'a la production avec un retour rapide", True),
      ("Stocker les mots de passe", False),
      ("Remplacer le controle de version", False)],
     "Le pipeline automatise le cheminement du changement (build, tests, deploiement) et eclaire vite sa releasabilite."),

    ("DOFD-3", 3, 3, "single",
     "En quoi consiste un deploiement Blue/Green ?",
     [("Basculer le trafic entre deux environnements identiques (l'un actif, l'autre nouveau) pour limiter le risque", True),
      ("Tester uniquement en local", False),
      ("Supprimer l'environnement de production", False),
      ("Deployer sans pouvoir revenir en arriere", False)],
     "Le Blue/Green maintient deux environnements ; on bascule vers le nouveau une fois valide, avec retour arriere facile."),

    ("DOFD-3", 3, 3, "single",
     "Qu'est-ce qu'un deploiement « canari » (canary release) ?",
     [("Exposer la nouvelle version a une petite fraction d'utilisateurs avant un deploiement complet", True),
      ("Deployer a 100 % des utilisateurs d'emblee", False),
      ("Un test realise seulement hors ligne", False),
      ("Une sauvegarde de base de donnees", False)],
     "Le canari limite l'impact : une petite portion d'utilisateurs reçoit la version d'abord ; en cas de souci, on annule."),

    ("DOFD-3", 2, 3, "single",
     "Que favorise le developpement base sur le tronc (trunk-based development) ?",
     [("Des branches de longue duree rarement fusionnees", False),
      ("Des integrations frequentes dans une branche principale commune", True),
      ("L'abandon du controle de version", False),
      ("Le gel des fusions", False)],
     "Le trunk-based limite la divergence en integrant tot et souvent dans le tronc commun, base de la CI."),

    ("DOFD-3", 3, 4, "single",
     "Quelle est la difference entre un SLI et un SLO ?",
     [("Le SLI est un indicateur mesure du service ; le SLO est l'objectif fixe pour cet indicateur", True),
      ("Ce sont deux mots pour la meme chose", False),
      ("Le SLO mesure, le SLI fixe le budget financier", False),
      ("Aucun lien avec la fiabilite", False)],
     "Le SLI (indicator) mesure la performance reelle ; le SLO (objective) est la cible visee pour ce SLI."),

    ("DOFD-3", 3, 4, "single",
     "A quoi sert une politique de budget d'erreur (error budget policy) ?",
     [("A definir les actions a prendre lorsque le budget d'erreur est epuise", True),
      ("A augmenter les salaires", False),
      ("A supprimer les SLO", False),
      ("A interdire la mesure", False)],
     "La politique de budget d'erreur precise ce que fait l'equipe (ex. geler les nouveautes) quand le budget est consomme."),

    ("DOFD-3", 2, 3, "single",
     "Quelle phrase resume l'esprit DevSecOps ?",
     [("La securite est l'affaire de tous, integree tot et de maniere automatisee", True),
      ("La securite est traitee uniquement par une equipe en fin de cycle", False),
      ("La securite n'est pas necessaire en DevOps", False),
      ("La securite ralentit donc on la supprime", False)],
     "DevSecOps diffuse la responsabilite de la securite a tous et l'integre tot dans le pipeline (security as code)."),

    ("DOFD-3", 3, 4, "single",
     "Qu'est-ce que l'ingenierie du chaos (chaos engineering) ?",
     [("Experimenter en injectant des pannes pour eprouver la resilience du systeme", True),
      ("Laisser le systeme sans surveillance", False),
      ("Supprimer les sauvegardes", False),
      ("Coder sans methode", False)],
     "Le chaos engineering (ex. Simian Army/Chaos Monkey) injecte des defaillances controlees pour renforcer la resilience."),

    ("DOFD-3", 2, 3, "single",
     "Que decrit le Test-Driven Development (TDD) ?",
     [("Ecrire les tests avant le code, puis coder pour les faire passer", True),
      ("Ecrire le code puis ne jamais le tester", False),
      ("Tester uniquement en production", False),
      ("Supprimer les tests unitaires", False)],
     "En TDD, on ecrit d'abord un test qui echoue, puis le code minimal pour le faire passer, puis on refactorise."),

    # ----------------------------- DOFD-4 ---------------------------------- #
    ("DOFD-4", 2, 2, "multiple",
     "Quels sont les roles de l'equipe Scrum ?",
     [("Product Owner", True),
      ("Scrum Master", True),
      ("Equipe de developpement", True),
      ("Directeur financier", False)],
     "Scrum definit trois roles : Product Owner, Scrum Master et l'equipe de developpement."),

    ("DOFD-4", 2, 2, "single",
     "Lequel de ces evenements appartient a Scrum ?",
     [("Le Sprint (avec melee quotidienne, revue et retrospective)", True),
      ("Le comite de pilotage annuel", False),
      ("La revue budgetaire trimestrielle", False),
      ("Le gel de code permanent", False)],
     "Les evenements Scrum incluent le Sprint, la melee quotidienne, la revue de sprint et la retrospective."),

    ("DOFD-4", 2, 2, "single",
     "Quels sont les principes de Kanban ?",
     [("Visualiser le travail, limiter l'en-cours et tirer le flux a un rythme soutenable", True),
      ("Cacher le travail en cours", False),
      ("Pousser un maximum de taches simultanees", False),
      ("Supprimer toute limite", False)],
     "Kanban rend le travail visible, limite l'en-cours (WIP) et tire le flux a une cadence tenable."),

    ("DOFD-4", 1, 2, "single",
     "Qu'est-ce qu'ITIL ?",
     [("Un ensemble de bonnes pratiques pour la gestion des services IT (ITSM)", True),
      ("Un langage de programmation", False),
      ("Un type de conteneur", False),
      ("Un outil de CI/CD", False)],
     "ITIL est un referentiel de bonnes pratiques de gestion des services informatiques (ITSM)."),

    ("DOFD-4", 2, 3, "single",
     "A quoi sert le Scaled Agile Framework (SAFe) ?",
     [("Appliquer les principes Lean-Agile a l'echelle de l'entreprise", True),
      ("Remplacer le controle de version", False),
      ("Supprimer les equipes", False),
      ("Gerer uniquement le materiel", False)],
     "SAFe est un cadre pour mettre en oeuvre Lean et Agile a grande echelle (multi-equipes)."),

    ("DOFD-4", 2, 3, "single",
     "Que recouvre l'acronyme des gaspillages Lean « DOWNTIME » ?",
     [("Huit types de gaspillage (defauts, surproduction, attentes, talents inexploites...)", True),
      ("Un type de panne serveur", False),
      ("Une metrique de disponibilite", False),
      ("Un outil de monitoring", False)],
     "DOWNTIME est un mnemonique des huit gaspillages Lean (Defects, Overproduction, Waiting, Non-utilized talent, Transportation, Inventory, Motion, Extra-processing)."),

    ("DOFD-4", 2, 3, "single",
     "Sur quoi se concentre Six Sigma ?",
     [("Reduire les defauts et la variabilite par une approche fondee sur les donnees", True),
      ("Augmenter la variabilite", False),
      ("Supprimer les mesures", False),
      ("Accelerer sans qualite", False)],
     "Six Sigma est une demarche data-driven de reduction des defauts et de la variabilite des processus."),

    ("DOFD-4", 2, 3, "single",
     "Qu'est-ce que l'Agile Service Management (gestion de service agile) ?",
     [("Appliquer les valeurs et pratiques Agile a la conception et l'amelioration des processus ITSM", True),
      ("Supprimer la gestion des services", False),
      ("Un outil de build", False),
      ("Une base de donnees", False)],
     "L'Agile SM applique l'approche Agile (just enough, iteratif) aux processus de gestion des services IT."),

    ("DOFD-4", 1, 2, "single",
     "Sur quel cycle repose l'amelioration continue (Deming) ?",
     [("Plan-Do-Check-Act (PDCA)", True),
      ("Build-Only", False),
      ("Deploy-Forget", False),
      ("Wait-and-See", False)],
     "L'amelioration continue s'appuie sur le cycle PDCA (Planifier, Faire, Verifier, Agir) de Deming."),

    ("DOFD-4", 2, 2, "single",
     "Qu'est-ce qu'un produit minimum viable (MVP) ?",
     [("La version la plus reduite d'un produit apportant deja assez de valeur pour etre utilisee et apprendre", True),
      ("La version finale complete", False),
      ("Un produit sans aucune fonctionnalite", False),
      ("Un prototype jamais livre", False)],
     "Le MVP livre juste assez de valeur pour etre utilise et generer des apprentissages rapides."),

    ("DOFD-4", 2, 3, "single",
     "Que represente la « Definition of Done » (definition de termine) ?",
     [("Un accord partage sur les criteres qu'un increment doit remplir pour etre livrable", True),
      ("La date de fin du projet", False),
      ("Le budget restant", False),
      ("Le nombre de commits", False)],
     "La Definition of Done formalise les criteres communs garantissant qu'un increment est reellement livrable."),

    # ----------------------------- DOFD-5 ---------------------------------- #
    ("DOFD-5", 3, 4, "single",
     "Dans le modele de Westrum, comment une culture « pathologique » traite-t-elle l'information ?",
     [("Comme une ressource personnelle utilisee dans des jeux de pouvoir, souvent dissimulee", True),
      ("Elle la partage largement", False),
      ("Elle l'ignore totalement", False),
      ("Elle l'automatise", False)],
     "Les cultures pathologiques (Westrum) retiennent et politisent l'information, a l'inverse des cultures generatives."),

    ("DOFD-5", 2, 3, "single",
     "Qu'est-ce qu'un post-mortem sans blame (blameless) ?",
     [("Un compte rendu d'incident ou les acteurs s'expriment sans crainte de sanction, pour apprendre", True),
      ("Une recherche de coupable a punir", False),
      ("Un document confidentiel jamais partage", False),
      ("Une interdiction de deployer", False)],
     "Le post-mortem blameless vise l'apprentissage systemique ; il evite la peur des represailles qui masque les causes."),

    ("DOFD-5", 2, 3, "single",
     "Que decrit la courbe de Kubler-Ross appliquee au changement ?",
     [("Les etapes emotionnelles traversees par les personnes face a un changement majeur", True),
      ("Le debit d'un pipeline", False),
      ("Le cout d'un serveur", False),
      ("Le nombre de tests", False)],
     "La courbe de Kubler-Ross (deni, colere, etc.) aide a anticiper et accompagner les reactions au changement."),

    ("DOFD-5", 1, 2, "single",
     "Comment definit-on la culture organisationnelle ?",
     [("Les valeurs et comportements partages qui caracterisent l'environnement d'une organisation", True),
      ("Le nombre d'employes", False),
      ("La pile technologique", False),
      ("Le chiffre d'affaires", False)],
     "La culture organisationnelle est l'ensemble des valeurs et comportements partages propres a l'organisation."),

    ("DOFD-5", 2, 3, "single",
     "Qu'observe-t-on dans une culture de haute confiance (high-trust) ?",
     [("Bonne circulation de l'information, collaboration transverse et apprentissage des echecs", True),
      ("Retention de l'information", False),
      ("Recherche systematique de coupables", False),
      ("Cloisonnement des equipes", False)],
     "Les cultures de haute confiance favorisent le flux d'information, la collaboration et l'apprentissage."),

    ("DOFD-5", 2, 3, "multiple",
     "Quels elements caracterisent le modele d'organisation Spotify ?",
     [("Squads (equipes autonomes)", True),
      ("Tribes (regroupements de squads)", True),
      ("Chapters et Guilds (partage de competences)", True),
      ("Comites hierarchiques figes", False)],
     "Le modele Spotify s'organise en squads, tribes, chapters et guilds pour rester agile a grande echelle."),

    ("DOFD-5", 2, 3, "single",
     "Quel changement culturel le DevOps privilegie-t-il ?",
     [("De la competition interne vers la cooperation et la collaboration", True),
      ("Du partage vers le secret", False),
      ("De la confiance vers le controle systematique", False),
      ("De l'equipe vers l'individu isole", False)],
     "Le DevOps valorise la cooperation et la responsabilite partagee plutot que la competition interne et les silos."),

    ("DOFD-5", 3, 3, "single",
     "Que designe la « dette culturelle » (cultural debt) ?",
     [("L'accumulation de comportements et normes nefastes qui freinent la collaboration", True),
      ("Une dette financiere", False),
      ("Un retard de tests", False),
      ("Un bug de production", False)],
     "La dette culturelle est l'accumulation d'habitudes toxiques (peur, silos) qui entravent la transformation."),

    ("DOFD-5", 2, 3, "single",
     "Que vise la conduite du changement (organizational change management) ?",
     [("Accompagner personnes et equipes d'un etat actuel vers un etat futur souhaite", True),
      ("Empecher tout changement", False),
      ("Supprimer les equipes", False),
      ("Geler les processus", False)],
     "La conduite du changement gere le volet humain de la transition vers l'etat cible pour obtenir les resultats vises."),

    ("DOFD-5", 2, 3, "single",
     "A quoi sert un « dojo » DevOps (apprentissage immersif) ?",
     [("Un espace ou les equipes s'entrainent en immersion, avec coaching et pratique", True),
      ("Un outil de supervision", False),
      ("Un type de serveur", False),
      ("Une base de donnees", False)],
     "Le dojo offre un apprentissage immersif : l'equipe pratique de nouvelles façons de travailler avec accompagnement."),

    ("DOFD-5", 2, 3, "single",
     "Pourquoi privilegier des equipes pluridisciplinaires (cross-functional) ?",
     [("Elles regroupent les competences pour livrer de bout en bout sans transferts excessifs", True),
      ("Elles multiplient les transferts entre silos", False),
      ("Elles suppriment toute responsabilite", False),
      ("Elles ralentissent le flux", False)],
     "Les equipes pluridisciplinaires reduisent les hand-offs et accelerent le flux en reunissant les competences cles."),

    # ----------------------------- DOFD-6 ---------------------------------- #
    ("DOFD-6", 2, 2, "single",
     "Qu'est-ce qu'une chaine d'outils DevOps (toolchain) ?",
     [("L'ensemble des outils relies qui soutiennent le cycle de l'idee a la mise en valeur", True),
      ("Un unique logiciel monolithique", False),
      ("Un type de serveur", False),
      ("Une methode de recrutement", False)],
     "La toolchain est l'ensemble integre d'outils couvrant le flux de developpement et de livraison de bout en bout."),

    ("DOFD-6", 2, 3, "single",
     "Qu'est-ce qu'une architecture en microservices ?",
     [("Une application composee de petits services autonomes communiquant par API", True),
      ("Un seul bloc monolithique indivisible", False),
      ("Une base de donnees unique geante", False),
      ("Un langage de programmation", False)],
     "Les microservices decoupent l'application en services independants, deployables separement, dialoguant via API."),

    ("DOFD-6", 2, 2, "single",
     "Que designent IaaS, PaaS et SaaS ?",
     [("Des modeles de services cloud (infrastructure, plateforme, logiciel)", True),
      ("Des types de tests", False),
      ("Des metriques DORA", False),
      ("Des roles Scrum", False)],
     "IaaS, PaaS et SaaS sont les principaux modeles de services cloud (infrastructure, plateforme et logiciel a la demande)."),

    ("DOFD-6", 2, 3, "single",
     "Que permet une infrastructure elastique / l'auto-scaling ?",
     [("Augmenter ou reduire automatiquement la capacite selon la charge", True),
      ("Figer la capacite quoi qu'il arrive", False),
      ("Supprimer la supervision", False),
      ("Empecher le deploiement", False)],
     "L'elasticite ajuste la capacite a la demande (montee/descente en charge) tout en maitrisant les couts."),

    ("DOFD-6", 2, 2, "single",
     "Pourquoi le controle de version est-il central en DevOps ?",
     [("Il sert de source unique de verite pour le code (et l'infrastructure) et trace l'historique", True),
      ("Il ralentit les equipes", False),
      ("Il stocke les mots de passe en clair", False),
      ("Il remplace les tests", False)],
     "Le controle de version (Git, etc.) centralise une source unique de verite et historise tous les changements."),

    ("DOFD-6", 2, 3, "single",
     "A quoi sert un depot d'artefacts (artifact repository) ?",
     [("Stocker les binaires, paquets et metadonnees produits par les builds", True),
      ("Heberger uniquement des pages web statiques", False),
      ("Remplacer le pipeline", False),
      ("Gerer les conges", False)],
     "Le depot d'artefacts (Artifactory, Nexus...) conserve binaires et paquets versionnes issus des builds."),

    ("DOFD-6", 3, 3, "single",
     "Que designe l'orchestration dans une chaine d'outils ?",
     [("L'approche qui relie plusieurs outils pour former une chaine automatisee coherente", True),
      ("Le fait d'ecrire du code applicatif", False),
      ("Une technique de test manuel", False),
      ("Un type de base de donnees", False)],
     "L'orchestration interface (« orchestre ») plusieurs outils pour constituer une toolchain automatisee."),

    ("DOFD-6", 3, 4, "single",
     "Pourquoi la gestion des secrets (secrets management) est-elle importante ?",
     [("Pour stocker et distribuer de maniere securisee mots de passe, cles et jetons utilises par les services", True),
      ("Pour publier les mots de passe dans le code", False),
      ("Pour desactiver l'authentification", False),
      ("Pour ralentir le pipeline", False)],
     "La gestion des secrets protege les identifiants (mots de passe, cles, jetons) au lieu de les exposer dans le code."),

    ("DOFD-6", 3, 4, "single",
     "Que signifie qu'un outil de gestion de configuration est « idempotent » ?",
     [("Appliquer la meme configuration plusieurs fois aboutit toujours au meme etat cible", True),
      ("Chaque execution donne un resultat different", False),
      ("Il chiffre les disques", False),
      ("Il supprime la base de donnees", False)],
     "L'idempotence garantit qu'appliquer N fois la configuration converge toujours vers le meme etat desire."),

    ("DOFD-6", 3, 3, "single",
     "Qu'apporte l'auto-reparation (self-healing) / le rollback automatise ?",
     [("La detection et la resolution automatiques de problemes, sans intervention manuelle", True),
      ("L'arret definitif du service au moindre incident", False),
      ("La suppression de la supervision", False),
      ("L'interdiction des deploiements", False)],
     "L'auto-reparation detecte et corrige automatiquement (ex. rollback) pour limiter l'intervention humaine."),

    # ----------------------------- DOFD-7 ---------------------------------- #
    ("DOFD-7", 2, 3, "single",
     "Que mesure le MTBF (Mean Time Between Failures) ?",
     [("Le temps moyen pendant lequel un service fonctionne sans interruption (fiabilite)", True),
      ("Le temps moyen pour reparer", False),
      ("Le nombre de deploiements", False),
      ("Le cout d'un incident", False)],
     "Le MTBF mesure la duree moyenne de bon fonctionnement entre deux pannes : un indicateur de fiabilite."),

    ("DOFD-7", 2, 3, "single",
     "Que mesure le MTTD (Mean Time To Detect) ?",
     [("Le temps moyen necessaire pour detecter une defaillance", True),
      ("Le temps moyen entre deux livraisons", False),
      ("Le nombre de tests", False),
      ("La taille des lots", False)],
     "Le MTTD mesure la rapidite a detecter un incident ; le reduire raccourcit le delai avant remediation."),

    ("DOFD-7", 2, 3, "single",
     "Que mesure le « cycle time » (temps de cycle) ?",
     [("Le temps entre le debut du travail effectif et sa disponibilite a la livraison", True),
      ("Le nombre de serveurs", False),
      ("Le budget d'un projet", False),
      ("Le taux d'occupation des salles", False)],
     "Le temps de cycle mesure la duree entre le debut du travail et sa disponibilite ; complementaire du lead time."),

    ("DOFD-7", 2, 3, "single",
     "Quelle est la relation entre KPI et facteur cle de succes (CSF) ?",
     [("Les KPI sont des metriques qui mesurent l'atteinte des facteurs cles de succes", True),
      ("Les KPI remplacent toute strategie", False),
      ("Les CSF mesurent les KPI", False),
      ("Il n'y a aucun lien", False)],
     "Les KPI quantifient l'atteinte des CSF : ce qui doit reussir est suivi par des indicateurs mesurables."),

    # ----------------------------- DOFD-8 ---------------------------------- #
    ("DOFD-8", 2, 3, "multiple",
     "Quels acteurs sont des parties prenantes (stakeholders) typiques du DevOps ?",
     [("Developpeurs", True),
      ("Operations / exploitation", True),
      ("Securite et metiers", True),
      ("Aucune partie prenante hors de l'IT", False)],
     "Le DevOps implique de nombreuses parties prenantes : Dev, Ops, securite, QA, metiers, management."),

    ("DOFD-8", 2, 3, "single",
     "Qu'est-ce qu'une « guilde » (guild) dans l'organisation DevOps ?",
     [("Une communaute d'interet ouverte qui traverse toute l'organisation pour partager un sujet", True),
      ("Un comite de direction ferme", False),
      ("Un outil de CI", False),
      ("Un type de serveur", False)],
     "Une guilde rassemble, au-dela des equipes, les personnes interessees par un sujet, proche d'une communaute de pratique."),

    ("DOFD-8", 2, 3, "single",
     "Que favorise le partage et le « shadowing » entre equipes ?",
     [("La diffusion des savoir-faire et la montee en competence collective", True),
      ("La retention de l'information", False),
      ("L'isolement des experts", False),
      ("La suppression de la documentation", False)],
     "Partage et shadowing (observation en binome) diffusent les competences et reduisent les points de connaissance uniques."),

    ("DOFD-8", 3, 3, "multiple",
     "Quels elements sont des facteurs cles de succes pour adopter le DevOps ?",
     [("Soutien du leadership", True),
      ("Collaboration et responsabilite partagee", True),
      ("Mesure et amelioration continue", True),
      ("Maintien rigide des silos", False)],
     "Leadership engage, collaboration, mesure et amelioration continue sont des facteurs cles de reussite de l'adoption."),

    ("DOFD-8", 3, 3, "single",
     "Quel obstacle frequent rencontre-t-on en debutant le DevOps ?",
     [("La resistance au changement et la fatigue du changement (change fatigue)", True),
      ("Un exces de collaboration", False),
      ("Trop de retours d'experience", False),
      ("Une mesure trop precise", False)],
     "La resistance et la fatigue du changement sont des freins majeurs ; d'ou l'importance de la conduite du changement."),

    ("DOFD-8", 3, 4, "single",
     "Que designe l'« inner source » (open source interne) ?",
     [("Appliquer les pratiques de l'open source au partage du code a l'interieur de l'organisation", True),
      ("Publier tout le code en externe sans controle", False),
      ("Interdire le partage de code", False),
      ("Un outil de monitoring", False)],
     "L'inner source diffuse en interne les pratiques open source (partage, contribution) pour favoriser la reutilisation."),

    ("DOFD-8", 3, 4, "single",
     "Quelle approche est recommandee pour demarrer le DevOps a l'echelle ?",
     [("Commencer petit (projet pilote), mesurer, apprendre puis diffuser progressivement", True),
      ("Tout transformer d'un coup sans mesure", False),
      ("Interdire toute experimentation", False),
      ("Supprimer le pilotage", False)],
     "On demarre souvent par un pilote, on mesure les resultats, on apprend, puis on etend l'adoption progressivement."),

    # ======================================================================= #
    # Banque etoffee — niveaux superieurs (K3 a K7, difficulte 3 a 5)         #
    # Questions d'application, d'analyse, d'evaluation et de synthese,         #
    # classees par section d'apprentissage (DOFD-1 a DOFD-8).                  #
    # Le seuil de l'examen reel est K1-K2 ; K3-K7 servent au sur-apprentissage.#
    # ======================================================================= #

    # ----------------------------- DOFD-1 ---------------------------------- #
    ("DOFD-1", 3, 3, "single",
     "Une organisation deploie rarement et chaque mise en production est douloureuse ; Dev et Ops se rejettent la faute. Quel changement DevOps traite la cause racine ?",
     [("Acheter un nouvel outil de ticketing", False),
      ("Instaurer une responsabilite partagee et des objectifs communs entre Dev et Ops", True),
      ("Augmenter le nombre de validations manuelles", False),
      ("Separer davantage les equipes", False)],
     "La cause racine est culturelle (silos, blame) ; le DevOps y repond par la responsabilite partagee et des buts communs."),

    ("DOFD-1", 3, 3, "single",
     "Un manager affirme « adopter le DevOps » en installant uniquement un serveur d'integration continue. Quelle est la principale limite de cette approche ?",
     [("Aucune limite, l'outil suffit", False),
      ("Le DevOps exige aussi des evolutions de culture et de processus, pas seulement un outil", True),
      ("La CI est inutile en DevOps", False),
      ("Il faut d'abord supprimer les tests", False)],
     "Le DevOps est culture + pratiques + outils : l'outillage seul, sans changement culturel et de processus, ne suffit pas."),

    ("DOFD-1", 3, 3, "single",
     "En DevOps, quelle est la difference entre un « output » et un « outcome » ?",
     [("L'output est un livrable produit ; l'outcome est le resultat/la valeur obtenue pour le client", True),
      ("Ce sont des synonymes", False),
      ("L'outcome est un fichier de log", False),
      ("L'output est toujours plus important que l'outcome", False)],
     "On vise les outcomes (valeur, resultats) et pas seulement les outputs (livrables) : livrer ne suffit pas, il faut creer de la valeur."),

    ("DOFD-1", 4, 3, "single",
     "Pour convaincre une direction financiere d'investir dans le DevOps, quel argument est le plus pertinent ?",
     [("Le DevOps reduit les couts, accelere la mise sur le marche et ameliore la qualite/la stabilite", True),
      ("Le DevOps supprime tout besoin de budget", False),
      ("Le DevOps elimine les equipes operationnelles", False),
      ("Le DevOps garantit zero incident", False)],
     "L'argumentaire business du DevOps repose sur cout, vitesse et qualite/stabilite, pas sur des promesses absolues."),

    ("DOFD-1", 4, 4, "single",
     "Une equipe deploie tres souvent mais avec un taux d'echec des changements eleve. Peut-on la qualifier de « tres performante » au sens DevOps ?",
     [("Oui, seule la frequence compte", False),
      ("Non : la haute performance combine frequence elevee ET faible taux d'echec (vitesse et stabilite)", True),
      ("Oui, le taux d'echec n'a aucune importance", False),
      ("Non, car deployer souvent est toujours mauvais", False)],
     "Les organisations elites conjuguent debit eleve et stabilite ; frequence elevee avec beaucoup d'echecs n'est pas une vraie performance."),

    ("DOFD-1", 4, 4, "single",
     "Quelle affirmation reflete le mieux la nature du DevOps ?",
     [("Un projet ponctuel avec une date de fin", False),
      ("Un parcours d'amelioration continue, sans etat final fige", True),
      ("Une certification a obtenir une fois pour toutes", False),
      ("Un service achete cle en main", False)],
     "Le DevOps est un cheminement continu d'amelioration, pas un projet ponctuel qu'on termine."),

    ("DOFD-1", 5, 4, "single",
     "De longs transferts (hand-offs) entre de nombreuses equipes ralentissent les livraisons. Quel principe DevOps est principalement bafoue ?",
     [("La fluidite du flux de valeur de bout en bout", True),
      ("L'obligation de documenter", False),
      ("La necessite de plus de comites", False),
      ("L'interdiction d'automatiser", False)],
     "Les hand-offs multiples brisent le flux ; le DevOps cherche a fluidifier le flux de valeur de bout en bout."),

    ("DOFD-1", 5, 4, "single",
     "Pour amorcer une demarche DevOps dans une organisation cloisonnee, quelle premiere etape est la plus judicieuse ?",
     [("Imposer un outil unique a toutes les equipes du jour au lendemain", False),
      ("Lancer un projet pilote avec objectifs communs, mesurer et diffuser les apprentissages", True),
      ("Supprimer l'equipe des operations", False),
      ("Geler les deploiements pendant un an", False)],
     "Demarrer petit (pilote), avec buts partages et mesure, puis diffuser, est plus efficace qu'un big bang outil-centre."),

    ("DOFD-1", 6, 5, "single",
     "Une transformation DevOps stagne malgre de bons outils. Quelle cause racine est la plus probable ?",
     [("Un manque de changement culturel et de soutien du leadership", True),
      ("Trop de collaboration entre equipes", False),
      ("Un exces de mesure", False),
      ("Des outils trop performants", False)],
     "Quand l'outillage est bon mais la transformation cale, la cause est generalement culturelle/leadership, pas technique."),

    ("DOFD-1", 6, 5, "single",
     "Quelle distinction est exacte concernant DevOps, Agile, Lean et ITSM ?",
     [("Le DevOps s'appuie sur Agile et Lean et peut coexister avec l'ITSM ; aucun ne remplace les autres", True),
      ("Le DevOps remplace integralement l'Agile, le Lean et l'ITSM", False),
      ("Agile et DevOps sont incompatibles", False),
      ("L'ITSM interdit le DevOps", False)],
     "DevOps prolonge Agile/Lean et se combine a l'ITSM ; ce sont des approches complementaires, non exclusives."),

    ("DOFD-1", 5, 5, "single",
     "Que repondre au mythe « il faut choisir entre vitesse et stabilite » ?",
     [("Les donnees montrent que vitesse et stabilite progressent ensemble dans les organisations performantes", True),
      ("Il faut toujours sacrifier la stabilite", False),
      ("Il faut toujours sacrifier la vitesse", False),
      ("Les deux sont impossibles a ameliorer", False)],
     "Vitesse et stabilite ne s'opposent pas : les pratiques DevOps ameliorent les deux simultanement."),

    ("DOFD-1", 7, 5, "single",
     "Dirigeant d'une DSI cloisonnee, vous devez lancer le DevOps. Quelle combinaison d'actions initiales est la plus coherente ?",
     [("Sponsoring visible du leadership, objectifs partages Dev/Ops, projet pilote mesurable et boucle d'apprentissage", True),
      ("Achat d'outils uniquement, sans changer l'organisation", False),
      ("Reorganisation massive immediate sans pilote ni mesure", False),
      ("Interdiction de toute experimentation", False)],
     "Une amorce solide combine leadership, buts communs, pilote mesurable et apprentissage : les leviers culturels priment."),

    # ----------------------------- DOFD-2 ---------------------------------- #
    ("DOFD-2", 3, 3, "single",
     "Le temps d'attente entre etapes explose et l'en-cours s'accumule. Quelle pratique de la Premiere Voie appliquer en priorite ?",
     [("Limiter le travail en cours (WIP) et reduire la taille des lots", True),
      ("Augmenter le nombre de taches simultanees", False),
      ("Multiplier les transferts", False),
      ("Cacher le travail en cours", False)],
     "Reduire le WIP et la taille des lots fluidifie le flux (Premiere Voie) et reduit attentes et en-cours."),

    ("DOFD-2", 3, 4, "single",
     "Pour appliquer la Deuxieme Voie, quelle action renforce les boucles de retroaction ?",
     [("Detecter les problemes au plus tot et remonter vite l'information vers l'amont", True),
      ("Attendre la fin du projet pour tout tester", False),
      ("Supprimer la telemetrie", False),
      ("Eviter les revues", False)],
     "La Deuxieme Voie amplifie et raccourcit les boucles de retour : detecter tot et faire remonter vite l'information."),

    ("DOFD-2", 3, 3, "single",
     "Comment appliquer concretement la Troisieme Voie au quotidien d'une equipe ?",
     [("Reserver du temps a l'experimentation, l'apprentissage et l'amelioration", True),
      ("Interdire toute erreur", False),
      ("Figer les pratiques definitivement", False),
      ("Supprimer les retrospectives", False)],
     "La Troisieme Voie institue l'apprentissage continu : du temps dedie a l'experimentation et a l'amelioration."),

    ("DOFD-2", 4, 4, "single",
     "Selon la Theorie des Contraintes, apres avoir identifie le goulot, quelle est l'etape suivante ?",
     [("Exploiter au maximum la contrainte puis subordonner le reste du systeme a cette contrainte", True),
      ("Optimiser toutes les autres etapes d'abord", False),
      ("Ignorer la contrainte", False),
      ("Ajouter de l'en-cours partout", False)],
     "ToC : identifier, exploiter la contrainte, subordonner le reste, elever la contrainte, puis recommencer."),

    ("DOFD-2", 4, 4, "single",
     "Une amelioration locale d'une etape non contrainte n'augmente pas le debit global. Quel principe l'explique ?",
     [("La Theorie des Contraintes : seule l'amelioration de la contrainte accroit le debit du systeme", True),
      ("La loi de Conway", False),
      ("Le theoreme de Bayes", False),
      ("La loi de Moore", False)],
     "Optimiser hors de la contrainte ne change pas le debit global : c'est le coeur de la Theorie des Contraintes."),

    ("DOFD-2", 5, 5, "single",
     "D'apres la loi de Little, comment reduire le temps de cycle moyen a debit constant ?",
     [("Reduire le travail en cours (en-cours)", True),
      ("Augmenter le travail en cours", False),
      ("Ajouter des transferts", False),
      ("Allonger les lots", False)],
     "Little : temps de cycle = en-cours / debit ; a debit constant, moins d'en-cours = temps de cycle plus court."),

    ("DOFD-2", 4, 4, "single",
     "Dans The Phoenix Project, un correctif urgent non prevu releve de quel type de travail ?",
     [("Le travail non planifie", True),
      ("Les projets metier", False),
      ("Les projets internes", False),
      ("Les changements planifies", False)],
     "Le travail non planifie (pannes, urgences) est l'un des quatre types ; il perturbe le flux des autres types."),

    ("DOFD-2", 5, 4, "single",
     "Pourquoi privilegier de petits lots plutot que de gros lots de changements ?",
     [("Retour plus rapide, risque plus faible, localisation des problemes plus aisee", True),
      ("Cela augmente le risque et l'attente", False),
      ("Cela supprime le besoin de tests", False),
      ("Cela ralentit la retroaction", False)],
     "Les petits lots accelerent la retroaction, reduisent le risque par changement et facilitent le diagnostic."),

    ("DOFD-2", 6, 5, "single",
     "Le goulot d'une equipe est l'environnement de test partage, sature. Quelle approche est la plus alignee sur les Trois Voies et la ToC ?",
     [("Exploiter/elargir la contrainte (ex. environnements a la demande) et subordonner le flux a celle-ci", True),
      ("Optimiser le codage, qui n'est pas la contrainte", False),
      ("Augmenter l'en-cours pour 'remplir' l'attente", False),
      ("Supprimer les tests pour contourner le goulot", False)],
     "On agit sur la contrainte (capacite de test) et on subordonne le reste : Premiere Voie eclairee par la ToC."),

    ("DOFD-2", 7, 5, "single",
     "Apres un incident majeur, quelle demarche incarne le mieux la Troisieme Voie ?",
     [("Post-mortem sans blame, partage des apprentissages et experimentation pour eviter la recidive", True),
      ("Sanction de l'operateur fautif", False),
      ("Gel de tous les changements", False),
      ("Dissimulation de l'incident", False)],
     "La Troisieme Voie transforme l'incident en apprentissage organisationnel via un post-mortem sans blame et des experimentations."),

    ("DOFD-2", 6, 5, "single",
     "Quelle combinaison decrit correctement l'ordre des Trois Voies ?",
     [("Flux (gauche-droite), puis retroaction (droite-gauche), puis apprentissage/experimentation continus", True),
      ("Apprentissage, puis flux, puis retroaction", False),
      ("Retroaction, puis apprentissage, puis flux", False),
      ("Flux, puis apprentissage, puis retroaction", False)],
     "Les Trois Voies : d'abord le flux, puis l'amplification des retours, puis la culture d'apprentissage continu."),

    ("DOFD-2", 5, 4, "single",
     "Rendre le travail visible (tableaux, kanban) sert principalement a :",
     [("Exposer le flux, les blocages et l'en-cours pour pouvoir agir dessus", True),
      ("Augmenter la charge administrative sans valeur", False),
      ("Cacher les problemes au management", False),
      ("Remplacer les tests automatises", False)],
     "Rendre le travail visible (Premiere Voie) revele goulots, en-cours et blocages : condition pour les traiter."),

    # ----------------------------- DOFD-3 ---------------------------------- #
    ("DOFD-3", 3, 3, "single",
     "Les developpeurs integrent leur code une fois par mois et les fusions sont douloureuses. Quelle pratique recommander ?",
     [("Integrer frequemment (au moins quotidiennement) avec build et tests automatises (CI)", True),
      ("Attendre encore plus longtemps entre les fusions", False),
      ("Supprimer les tests pour fusionner plus vite", False),
      ("Travailler sur des branches de tres longue duree", False)],
     "L'integration continue reduit la douleur des fusions en integrant souvent, valide par build et tests automatises."),

    ("DOFD-3", 3, 4, "single",
     "Une fonctionnalite doit etre deployee mais activee plus tard pour certains utilisateurs. Quelle technique utiliser ?",
     [("Les feature flags (drapeaux de fonctionnalite)", True),
      ("Recompiler pour chaque utilisateur", False),
      ("Supprimer la CI", False),
      ("Geler la branche principale", False)],
     "Les feature flags decouplent deploiement et activation, permettant d'activer une fonctionnalite progressivement."),

    ("DOFD-3", 3, 3, "single",
     "Pour limiter le risque lors d'une mise en production, quelle strategie expose d'abord une petite part d'utilisateurs ?",
     [("Le deploiement canari", True),
      ("Le big bang a 100 %", False),
      ("Le gel des deploiements", False),
      ("La suppression des tests", False)],
     "Le canari expose la nouveaute a une fraction d'utilisateurs pour detecter tot les problemes avant generalisation."),

    ("DOFD-3", 4, 4, "single",
     "Le budget d'erreur d'un service est epuise avant la fin du mois. Quelle decision est coherente avec une error budget policy ?",
     [("Suspendre les nouvelles fonctionnalites et prioriser la fiabilite jusqu'a reconstitution du budget", True),
      ("Accelerer encore les deploiements de nouveautes", False),
      ("Supprimer le SLO", False),
      ("Ignorer la situation", False)],
     "Budget d'erreur consomme : la politique impose generalement de geler les nouveautes au profit de la fiabilite."),

    ("DOFD-3", 4, 5, "single",
     "Les tests de bout en bout sont lents et instables et bloquent le pipeline. Quelle correction est la plus alignee sur la pyramide des tests ?",
     [("Renforcer une large base de tests unitaires rapides et limiter les tests E2E aux parcours critiques", True),
      ("Supprimer tous les tests", False),
      ("Ne garder que des tests E2E manuels", False),
      ("Tester uniquement en production", False)],
     "La pyramide privilegie beaucoup de tests unitaires rapides ; on limite les E2E lents/fragiles aux cas essentiels."),

    ("DOFD-3", 4, 4, "single",
     "Quelle difference fondamentale entre livraison continue et deploiement continu ?",
     [("La livraison continue garde le logiciel toujours deployable (declenchement decide) ; le deploiement continu pousse automatiquement en production", True),
      ("Aucune difference", False),
      ("Le deploiement continu n'a pas de tests", False),
      ("La livraison continue interdit l'automatisation", False)],
     "Livraison continue = toujours pret a livrer (decision humaine) ; deploiement continu = mise en prod automatique apres tests."),

    ("DOFD-3", 5, 4, "single",
     "Un SLO de disponibilite est fixe a 99,9 %. Que represente alors le budget d'erreur ?",
     [("La part d'indisponibilite toleree, soit environ 0,1 % du temps", True),
      ("100 % du temps", False),
      ("Le budget financier de l'equipe", False),
      ("Le nombre de tickets", False)],
     "Budget d'erreur = 1 - SLO ; pour 99,9 %, environ 0,1 % d'indisponibilite est tolere sur la periode."),

    ("DOFD-3", 4, 4, "single",
     "Un SRE doit arbitrer entre livrer vite et rester fiable. Quel mecanisme objective cet arbitrage ?",
     [("Le budget d'erreur derive du SLO", True),
      ("Le nombre de commits", False),
      ("La taille de l'equipe", False),
      ("Le cout des licences", False)],
     "Le budget d'erreur (1 - SLO) arbitre : tant qu'il en reste, on livre ; epuise, on priorise la fiabilite."),

    ("DOFD-3", 6, 5, "single",
     "Pour valider la resilience d'un systeme en production de maniere proactive, quelle pratique mettre en place ?",
     [("L'ingenierie du chaos : injecter des pannes controlees pour verifier la tenue du systeme", True),
      ("Attendre une vraie panne pour reagir", False),
      ("Desactiver la supervision", False),
      ("Supprimer les sauvegardes", False)],
     "L'ingenierie du chaos eprouve la resilience en injectant des defaillances controlees (ex. Chaos Monkey)."),

    ("DOFD-3", 7, 5, "single",
     "Une organisation veut un pipeline ou chaque commit valide part automatiquement en production. Quels pre-requis sont indispensables ?",
     [("Tests automatises fiables et complets, et capacite de retour arriere rapide", True),
      ("Aucun test, pour aller plus vite", False),
      ("Des deploiements manuels mensuels", False),
      ("La suppression du controle de version", False)],
     "Le deploiement continu exige une suite de tests fiable et un rollback rapide : sinon l'automatisation propage les defauts."),

    ("DOFD-3", 6, 5, "single",
     "Quel enchainement decrit le mieux un cycle TDD ?",
     [("Ecrire un test qui echoue, ecrire le code minimal pour le faire passer, puis refactoriser", True),
      ("Coder, livrer, puis eventuellement tester", False),
      ("Tester seulement apres la mise en production", False),
      ("Supprimer les tests apres le build", False)],
     "TDD : red (test qui echoue) -> green (code minimal) -> refactor, en boucle courte."),

    ("DOFD-3", 5, 4, "single",
     "Pourquoi appliquer le principe « shift left » a la qualite et a la securite ?",
     [("Pour detecter et corriger les problemes au plus tot, ou ils coutent moins cher", True),
      ("Pour repousser les tests apres la production", False),
      ("Pour supprimer les controles", False),
      ("Pour concentrer la qualite en fin de cycle", False)],
     "Decaler a gauche rapproche tests/securite des phases initiales : les defauts y sont moins couteux a corriger."),

    # ----------------------------- DOFD-4 ---------------------------------- #
    ("DOFD-4", 3, 3, "single",
     "Une equipe veut visualiser ou la valeur est ralentie de l'idee a la production. Quel outil utiliser ?",
     [("La cartographie de la chaine de valeur (Value Stream Mapping)", True),
      ("Un diagramme de Gantt fige", False),
      ("Un organigramme RH", False),
      ("Un schema reseau", False)],
     "Le VSM cartographie le flux de valeur de bout en bout et revele attentes, goulots et gaspillages."),

    ("DOFD-4", 3, 4, "single",
     "Dans Scrum, qui est responsable de la priorisation du backlog produit ?",
     [("Le Product Owner", True),
      ("Le Scrum Master", False),
      ("Le directeur financier", False),
      ("L'equipe de test uniquement", False)],
     "Le Product Owner maximise la valeur du produit et ordonne le backlog ; le Scrum Master facilite le processus."),

    ("DOFD-4", 3, 3, "single",
     "Kanban impose une limite de travail en cours (WIP). Quel effet principal en attendre ?",
     [("Reduire le multitache, fluidifier le flux et reveler les goulots", True),
      ("Augmenter le nombre de taches en parallele", False),
      ("Supprimer la visualisation", False),
      ("Allonger les files d'attente", False)],
     "Limiter le WIP reduit le multitache, ameliore le flux et met en evidence les blocages a traiter."),

    ("DOFD-4", 4, 4, "single",
     "Une grande organisation veut coordonner plusieurs equipes Agile sur un meme produit. Quel cadre est concu pour cela ?",
     [("Le Scaled Agile Framework (SAFe)", True),
      ("Un simple tableau Kanban individuel", False),
      ("Le modele en cascade", False),
      ("La suppression de toute coordination", False)],
     "SAFe applique Lean-Agile a l'echelle, pour aligner plusieurs equipes sur un meme produit/programme."),

    ("DOFD-4", 4, 5, "single",
     "Une analyse Lean revele du stock d'en-cours, des attentes et des reprises. A quoi ces elements se rattachent-ils ?",
     [("Aux gaspillages (waste) que le Lean cherche a eliminer", True),
      ("A de la valeur ajoutee", False),
      ("A des metriques DORA", False),
      ("A des roles Scrum", False)],
     "En-cours excessif, attentes et reprises sont des formes de gaspillage (muda) que le Lean traque."),

    ("DOFD-4", 4, 4, "single",
     "Comment DevOps et ITSM/ITIL peuvent-ils coexister ?",
     [("DevOps s'integre aux processus ITSM (incidents, changements) et les rend plus agiles", True),
      ("DevOps interdit toute gestion de service", False),
      ("ITSM remplace le DevOps", False),
      ("Ils sont totalement incompatibles", False)],
     "DevOps et ITSM sont complementaires : on applique l'esprit Agile/Lean aux processus de gestion des services."),

    ("DOFD-4", 4, 4, "single",
     "Quel est l'apport principal d'un financement par produit plutot que par projet ?",
     [("Des equipes stables et durables centrees sur un flux de valeur continu", True),
      ("Des equipes dissoutes a chaque livraison", False),
      ("La suppression de toute mesure de valeur", False),
      ("Le gel des budgets", False)],
     "Le mode produit finance des equipes perennes et un flux de valeur continu, contrairement au mode projet temporaire."),

    ("DOFD-4", 5, 4, "single",
     "Le cycle PDCA (Deming) sert principalement a :",
     [("Structurer l'amelioration continue (Planifier, Faire, Verifier, Agir)", True),
      ("Remplacer le controle de version", False),
      ("Supprimer les tests", False),
      ("Geler les processus", False)],
     "PDCA est la boucle d'amelioration continue : planifier, experimenter, mesurer puis ajuster, en repetant."),

    ("DOFD-4", 6, 5, "single",
     "Une equipe livre un increment 'termine' mais non deployable (tests manquants, non integre). Quel artefact aurait du le prevenir ?",
     [("Une Definition of Done explicite et partagee", True),
      ("Un diagramme reseau", False),
      ("Un budget previsionnel", False),
      ("Un organigramme", False)],
     "La Definition of Done fixe les criteres de 'reellement livrable' ; son absence laisse passer des increments incomplets."),

    ("DOFD-4", 7, 5, "single",
     "Pour reduire le delai entre une demande et sa livraison, sur quels leviers Lean/ToC agir en priorite ?",
     [("Reduire la taille des lots et l'en-cours, et lever la contrainte du flux", True),
      ("Augmenter l'en-cours et la taille des lots", False),
      ("Ajouter des etapes de validation manuelle", False),
      ("Multiplier les transferts entre equipes", False)],
     "On agit sur lots, en-cours et contrainte : ces leviers Lean/ToC raccourcissent le delai de bout en bout."),

    ("DOFD-4", 6, 5, "single",
     "Quelle affirmation sur Lean et Six Sigma est correcte ?",
     [("Lean vise a eliminer le gaspillage et Six Sigma a reduire la variabilite/les defauts ; ils sont complementaires", True),
      ("Lean augmente les defauts volontairement", False),
      ("Six Sigma ignore les donnees", False),
      ("Les deux interdisent l'amelioration continue", False)],
     "Lean (gaspillage) et Six Sigma (variabilite/defauts) se combinent souvent (Lean Six Sigma) pour ameliorer les processus."),

    ("DOFD-4", 5, 4, "single",
     "Pourquoi livrer d'abord un produit minimum viable (MVP) ?",
     [("Pour valider la valeur et apprendre vite avec un minimum d'effort avant d'investir davantage", True),
      ("Pour livrer la version finale complete d'emblee", False),
      ("Pour eviter tout retour utilisateur", False),
      ("Pour supprimer les tests", False)],
     "Le MVP permet d'apprendre rapidement aupres des utilisateurs avec un effort minimal, reduisant le risque."),

    # ----------------------------- DOFD-5 ---------------------------------- #
    ("DOFD-5", 3, 3, "single",
     "Apres un incident, le management cherche un coupable a sanctionner. Quel effet sur la culture ?",
     [("La peur reduit la remontee d'information et masque les causes reelles", True),
      ("Cela ameliore la transparence", False),
      ("Cela accelere l'apprentissage", False),
      ("Cela n'a aucun effet", False)],
     "La culture du blame fait taire les signaux ; une culture juste/sans blame favorise au contraire l'apprentissage."),

    ("DOFD-5", 3, 4, "single",
     "Une equipe construit un service mais une autre l'exploite sans contexte. Quel principe corrigerait cela ?",
     [("« You build it, you run it » : responsabiliser l'equipe de bout en bout", True),
      ("Renforcer la separation Dev/Ops", False),
      ("Supprimer la supervision", False),
      ("Interdire les astreintes", False)],
     "Faire porter la construction ET l'exploitation par la meme equipe ameliore la qualite et la responsabilisation."),

    ("DOFD-5", 3, 3, "single",
     "Quel signe distingue une culture generative (Westrum) d'une culture pathologique ?",
     [("L'information circule largement et la cooperation est recherchee", True),
      ("L'information est dissimulee et politisee", False),
      ("Les porteurs de mauvaises nouvelles sont punis", False),
      ("Les responsabilites sont fuies", False)],
     "Les cultures generatives font circuler l'information et cooperent, la ou les cultures pathologiques la retiennent."),

    ("DOFD-5", 3, 4, "single",
     "Pour qu'une equipe ose signaler les problemes et experimenter, quel facteur est determinant ?",
     [("La securite psychologique", True),
      ("La peur de la sanction", False),
      ("Le secret de l'information", False),
      ("La competition interne", False)],
     "La securite psychologique (oser prendre des risques interpersonnels sans crainte) libere la parole et l'experimentation."),

    ("DOFD-5", 4, 4, "single",
     "Un nouveau systeme reproduit exactement les frontieres des equipes qui l'ont conçu. Quel principe l'explique ?",
     [("La loi de Conway", True),
      ("La loi de Little", False),
      ("La Theorie des Contraintes", False),
      ("La loi de Moore", False)],
     "Loi de Conway : l'architecture tend a refleter les structures de communication de l'organisation."),

    ("DOFD-5", 4, 5, "single",
     "Une transformation provoque deni puis colere chez les equipes. Quel modele aide a anticiper ces reactions ?",
     [("La courbe du changement de Kubler-Ross", True),
      ("Le modele CALMS", False),
      ("La pyramide des tests", False),
      ("Le budget d'erreur", False)],
     "La courbe de Kubler-Ross decrit les etapes emotionnelles du changement, utile pour accompagner les personnes."),

    ("DOFD-5", 4, 4, "single",
     "Pour reduire les transferts et accelerer le flux, comment structurer les equipes ?",
     [("En equipes pluridisciplinaires regroupant les competences necessaires", True),
      ("En silos fonctionnels etanches", False),
      ("En multipliant les hand-offs", False),
      ("En centralisant toutes les decisions", False)],
     "Les equipes pluridisciplinaires reunissent les competences pour livrer de bout en bout avec moins de transferts."),

    ("DOFD-5", 5, 4, "single",
     "Que designe la « maneuvre de Conway inverse » (inverse Conway maneuver) ?",
     [("Organiser deliberement les equipes pour obtenir l'architecture souhaitee", True),
      ("Interdire toute reorganisation", False),
      ("Supprimer les API", False),
      ("Centraliser tout le code", False)],
     "La maneuvre de Conway inverse façonne volontairement les equipes pour induire l'architecture cible visee."),

    ("DOFD-5", 6, 5, "single",
     "Une organisation a de bons outils mais l'information reste cloisonnee et les mauvaises nouvelles sont etouffees. Quel diagnostic culturel poser ?",
     [("Une culture bureaucratique/pathologique a faire evoluer vers le generatif", True),
      ("Une culture deja generative", False),
      ("Un probleme purement technique", False),
      ("Un exces de securite psychologique", False)],
     "Cloisonnement de l'information et etouffement des signaux trahissent une culture non generative a transformer."),

    ("DOFD-5", 7, 5, "single",
     "Pour ancrer durablement un changement culturel DevOps, quelle combinaison est la plus efficace ?",
     [("Leadership exemplaire, securite psychologique, objectifs partages et apprentissage des echecs", True),
      ("Sanctions systematiques des erreurs", False),
      ("Outils seuls, sans accompagnement", False),
      ("Renforcement des silos", False)],
     "Le changement culturel s'ancre par l'exemplarite du leadership, la securite psychologique, des buts communs et l'apprentissage."),

    ("DOFD-5", 6, 5, "single",
     "Le modele Spotify (squads, tribes, chapters, guilds) vise principalement a :",
     [("Garder l'agilite et l'autonomie des equipes a grande echelle", True),
      ("Centraliser toutes les decisions", False),
      ("Supprimer toute coordination", False),
      ("Figer les equipes", False)],
     "Le modele Spotify cherche a conserver autonomie et agilite des equipes (squads) tout en restant coordonne a l'echelle."),

    ("DOFD-5", 5, 4, "single",
     "Qu'est-ce que la « dette culturelle » et pourquoi la surveiller ?",
     [("L'accumulation d'habitudes nefastes (peur, silos) qui finit par bloquer la transformation", True),
      ("Une dette financiere a rembourser", False),
      ("Un retard de tests automatises", False),
      ("Un bug en production", False)],
     "Comme la dette technique, la dette culturelle s'accumule et freine la collaboration si on ne la traite pas."),

    # ----------------------------- DOFD-6 ---------------------------------- #
    ("DOFD-6", 3, 3, "single",
     "Une equipe configure ses serveurs a la main, avec des ecarts entre environnements. Quelle pratique recommander ?",
     [("L'Infrastructure as Code (IaC), versionnee et reproductible", True),
      ("Continuer la configuration manuelle", False),
      ("Supprimer les environnements de test", False),
      ("Documenter sans automatiser", False)],
     "L'IaC rend l'infrastructure reproductible et versionnee, eliminant les ecarts de configuration manuels."),

    ("DOFD-6", 3, 4, "single",
     "Pour deployer, mettre a l'echelle et superviser des conteneurs sur un cluster, quel outil utiliser ?",
     [("Un orchestrateur de conteneurs comme Kubernetes", True),
      ("Un tableur", False),
      ("Un editeur de texte", False),
      ("Une base de donnees relationnelle", False)],
     "Kubernetes orchestre le cycle de vie, la mise a l'echelle et la resilience des conteneurs sur un cluster."),

    ("DOFD-6", 3, 3, "single",
     "Pourquoi empaqueter une application dans un conteneur ?",
     [("Pour une execution coherente et portable avec ses dependances entre environnements", True),
      ("Pour supprimer le besoin de tests", False),
      ("Pour ralentir les deploiements", False),
      ("Pour empecher l'automatisation", False)],
     "Le conteneur embarque l'app et ses dependances, garantissant une execution coherente d'un environnement a l'autre."),

    ("DOFD-6", 3, 4, "single",
     "Des secrets (mots de passe, cles) trainent en clair dans le depot de code. Quelle correction ?",
     [("Mettre en place une gestion des secrets dediee et retirer les secrets du code", True),
      ("Publier les secrets dans le README", False),
      ("Desactiver l'authentification", False),
      ("Ignorer le probleme", False)],
     "On externalise les secrets dans un gestionnaire dedie (coffre) et on ne les stocke jamais en clair dans le depot."),

    ("DOFD-6", 4, 4, "single",
     "Plutot que de patcher les serveurs en place, l'equipe redeploie des instances neuves a chaque changement. Quel principe applique-t-elle ?",
     [("L'infrastructure immuable", True),
      ("La configuration manuelle", False),
      ("Le couplage fort", False),
      ("Le deploiement big bang sans test", False)],
     "L'infrastructure immuable remplace les composants au lieu de les modifier, reduisant la derive de configuration."),

    ("DOFD-6", 4, 5, "single",
     "Un script de configuration applique deux fois produit deux etats differents. Quel principe est viole ?",
     [("L'idempotence", True),
      ("La loi de Conway", False),
      ("La pyramide des tests", False),
      ("Le budget d'erreur", False)],
     "Un outil de configuration doit etre idempotent : N applications convergent vers le meme etat cible."),

    ("DOFD-6", 4, 4, "single",
     "Quel role joue le controle de version dans une chaine d'outils DevOps ?",
     [("Source unique de verite pour le code et l'infrastructure, avec historique des changements", True),
      ("Un simple espace de stockage de documents", False),
      ("Un outil de paie", False),
      ("Un remplacement des tests", False)],
     "Le controle de version est la source unique de verite (code + IaC) et trace l'historique, socle de la CI/CD."),

    ("DOFD-6", 5, 4, "single",
     "Que designe l'orchestration d'outils dans une toolchain ?",
     [("Relier et coordonner plusieurs outils pour automatiser le flux de bout en bout", True),
      ("Ecrire du code applicatif", False),
      ("Tester manuellement", False),
      ("Stocker des binaires uniquement", False)],
     "L'orchestration interface plusieurs outils en une chaine automatisee coherente (build, test, deploiement, supervision)."),

    ("DOFD-6", 6, 5, "single",
     "Une application monolithique freine les deploiements independants. Quelle evolution architecturale envisager, et a quel cout ?",
     [("Les microservices, qui permettent des deploiements independants mais ajoutent de la complexite operationnelle", True),
      ("Un monolithe encore plus gros, sans inconvenient", False),
      ("La suppression de toute architecture", False),
      ("Le retour a la configuration manuelle", False)],
     "Les microservices autorisent des deploiements independants au prix d'une complexite accrue (reseau, observabilite, orchestration)."),

    ("DOFD-6", 7, 5, "single",
     "Pour integrer la securite dans la chaine d'outils sans freiner le flux, quelle approche DevSecOps privilegier ?",
     [("Automatiser les controles de securite tot dans le pipeline (analyses, secrets, dependances)", True),
      ("Faire un audit unique apres la mise en production", False),
      ("Supprimer les controles pour aller plus vite", False),
      ("Confier la securite a une seule personne en fin de cycle", False)],
     "DevSecOps automatise et decale a gauche les controles de securite, integres au pipeline plutot qu'en fin de cycle."),

    ("DOFD-6", 6, 5, "single",
     "Quel benefice principal d'une infrastructure cloud elastique pour une charge variable ?",
     [("Ajuster automatiquement la capacite a la demande tout en maitrisant les couts", True),
      ("Figer la capacite au maximum en permanence", False),
      ("Supprimer la supervision", False),
      ("Empecher l'auto-scaling", False)],
     "L'elasticite cloud adapte la capacite a la charge (montee/descente), optimisant performance et couts."),

    ("DOFD-6", 5, 4, "single",
     "A quoi sert un depot d'artefacts dans le pipeline ?",
     [("Stocker de maniere versionnee les binaires/paquets produits, reutilisables par les etapes suivantes", True),
      ("Heberger uniquement la documentation", False),
      ("Remplacer le controle de version du code source", False),
      ("Gerer les incidents", False)],
     "Le depot d'artefacts conserve les binaires/paquets versionnes issus du build, consommes par les etapes de deploiement."),

    # ----------------------------- DOFD-7 ---------------------------------- #
    ("DOFD-7", 3, 3, "single",
     "Lesquelles des metriques DORA refletent la VITESSE de livraison ?",
     [("Frequence de deploiement et delai des changements", True),
      ("Taux d'echec et MTTR uniquement", False),
      ("Nombre d'employes", False),
      ("Cout des licences", False)],
     "DORA distingue vitesse (frequence de deploiement, lead time) et stabilite (taux d'echec, temps de retablissement)."),

    ("DOFD-7", 3, 4, "single",
     "Lesquelles des metriques DORA refletent la STABILITE ?",
     [("Taux d'echec des changements et temps de retablissement (MTTR)", True),
      ("Frequence de deploiement et lead time", False),
      ("Nombre de commits", False),
      ("Taille de l'equipe", False)],
     "La stabilite se lit via le taux d'echec des changements et le temps de retablissement du service."),

    ("DOFD-7", 3, 3, "single",
     "Une direction se vante d'un nombre eleve de lignes de code ecrites. Quel est le probleme ?",
     [("C'est une vanity metric : elle n'oriente aucune decision utile", True),
      ("C'est une excellente metrique de valeur", False),
      ("Elle mesure la satisfaction client", False),
      ("Elle mesure la fiabilite", False)],
     "Le volume de code est une vanity metric : impressionnant mais sans lien direct avec la valeur ou les decisions."),

    ("DOFD-7", 4, 4, "single",
     "Un service affiche un MTTR tres eleve. Sur quoi agir en priorite pour l'ameliorer ?",
     [("La detection et la restauration rapides (observabilite, runbooks, rollback)", True),
      ("Le nombre de fonctionnalites livrees", False),
      ("La taille de la documentation", False),
      ("Le nombre de reunions", False)],
     "Reduire le MTTR passe par une detection rapide et une restauration efficace (observabilite, automatisation, rollback)."),

    ("DOFD-7", 4, 5, "single",
     "Quel critere distingue une bonne metrique d'une vanity metric ?",
     [("Elle est actionnable : elle oriente une decision ou une action", True),
      ("Elle est impressionnante a presenter", False),
      ("Elle est toujours en hausse", False),
      ("Elle est facile a manipuler", False)],
     "Une bonne metrique est actionnable (guide une decision), au contraire d'une vanity metric qui flatte sans informer."),

    ("DOFD-7", 4, 4, "single",
     "Quelle est la difference entre lead time des changements et cycle time ?",
     [("Le lead time va de la demande/commit jusqu'a la prod ; le cycle time part du debut du travail effectif", True),
      ("Ce sont des synonymes stricts", False),
      ("Le cycle time mesure le budget", False),
      ("Le lead time mesure le nombre de serveurs", False)],
     "Le lead time couvre de la demande a la livraison ; le cycle time mesure du debut du travail effectif a la disponibilite."),

    ("DOFD-7", 5, 4, "single",
     "Quelle relation lie KPI et facteurs cles de succes (CSF) ?",
     [("Les KPI mesurent l'atteinte des CSF", True),
      ("Les CSF mesurent les KPI", False),
      ("Ils sont sans rapport", False),
      ("Les KPI remplacent la strategie", False)],
     "Les CSF sont ce qui doit reussir ; les KPI sont les indicateurs qui en mesurent l'atteinte."),

    ("DOFD-7", 6, 5, "single",
     "Deux equipes ont la meme frequence de deploiement, mais l'une a un taux d'echec bien plus eleve. Que conclure ?",
     [("La vitesse seule ne suffit pas : la stabilite (faible taux d'echec) distingue la vraie performance", True),
      ("Les deux equipes sont identiques en performance", False),
      ("Le taux d'echec n'a aucune importance", False),
      ("Il faut deployer encore plus souvent quoi qu'il arrive", False)],
     "Les quatre metriques DORA s'evaluent ensemble : a frequence egale, le taux d'echec departage la performance reelle."),

    ("DOFD-7", 7, 5, "single",
     "Pour piloter une amelioration DevOps, quelle demarche de mesure est la plus saine ?",
     [("Choisir quelques metriques actionnables (ex. DORA), les suivre dans le temps et agir sur les causes", True),
      ("Multiplier les vanity metrics pour le reporting", False),
      ("Mesurer une seule fois puis arreter", False),
      ("Optimiser une metrique au detriment des autres (gaming)", False)],
     "On suit un petit jeu de metriques actionnables (ex. DORA) dans la duree, en agissant sur les causes, sans 'gaming'."),

    ("DOFD-7", 6, 5, "single",
     "Optimiser a l'extreme une seule metrique (ex. frequence de deploiement) peut conduire a :",
     [("Des effets pervers si la stabilite et la valeur sont negligees (optimisation locale)", True),
      ("Une amelioration garantie de tout le systeme", False),
      ("Aucune consequence", False),
      ("La disparition des incidents", False)],
     "Optimiser une metrique isolee peut degrader le systeme global ; il faut equilibrer vitesse, stabilite et valeur."),

    ("DOFD-7", 5, 4, "single",
     "Que mesure le MTBF et a quoi sert-il ?",
     [("Le temps moyen de bon fonctionnement entre deux pannes ; il renseigne sur la fiabilite", True),
      ("Le temps moyen de reparation", False),
      ("Le nombre de deploiements", False),
      ("Le cout d'un incident", False)],
     "Le MTBF (Mean Time Between Failures) mesure la duree moyenne sans panne : un indicateur de fiabilite."),

    ("DOFD-7", 5, 5, "single",
     "Que mesure le taux d'echec des changements (change failure rate) ?",
     [("La part des changements qui degradent le service et necessitent une remediation", True),
      ("Le nombre total de deploiements", False),
      ("La vitesse du reseau", False),
      ("Le nombre de developpeurs", False)],
     "Le change failure rate est la proportion de changements provoquant une defaillance necessitant correctif/rollback."),

    # ----------------------------- DOFD-8 ---------------------------------- #
    ("DOFD-8", 3, 3, "single",
     "Une expertise critique repose sur une seule personne (bus factor de 1). Quelle pratique de partage attenue ce risque ?",
     [("Le shadowing/binomage et la documentation partagee pour diffuser le savoir", True),
      ("Concentrer encore plus le savoir sur cette personne", False),
      ("Interdire la documentation", False),
      ("Supprimer les revues", False)],
     "Le partage (shadowing, binomes, documentation) reduit les points de connaissance uniques et le risque associe."),

    ("DOFD-8", 3, 4, "single",
     "Pour diffuser des bonnes pratiques au-dela d'une seule equipe, quel dispositif mettre en place ?",
     [("Une communaute de pratique ou une guilde transverse", True),
      ("Un silo supplementaire", False),
      ("La suppression des echanges inter-equipes", False),
      ("Un gel des partages", False)],
     "Communautes de pratique et guildes diffusent savoir-faire et standards entre equipes, au-dela des silos."),

    ("DOFD-8", 3, 3, "single",
     "Quel est l'interet principal du ChatOps pour le partage ?",
     [("Centraliser conversations, outils et automatisation dans un canal partage et tracable", True),
      ("Remplacer toute la documentation", False),
      ("Isoler les operations des equipes", False),
      ("Empecher l'automatisation", False)],
     "Le ChatOps rend les operations visibles et partagees : actions et contexte cohabitent dans un canal historise."),

    ("DOFD-8", 3, 4, "single",
     "Pour partager du code et favoriser la reutilisation a l'interieur de l'entreprise, quelle approche adopter ?",
     [("L'inner source : appliquer les pratiques open source en interne", True),
      ("Interdire tout partage de code", False),
      ("Cloisonner chaque equipe", False),
      ("Publier sans controle a l'exterieur", False)],
     "L'inner source diffuse en interne les pratiques open source (partage, contribution), favorisant la reutilisation."),

    ("DOFD-8", 4, 4, "multiple",
     "Quels sont des facteurs cles de succes recurrents d'une adoption DevOps ?",
     [("Soutien et exemplarite du leadership", True),
      ("Collaboration et responsabilite partagee", True),
      ("Mesure et amelioration continue", True),
      ("Renforcement des silos et de la peur", False)],
     "Leadership, collaboration, mesure et amelioration continue reviennent comme facteurs cles de reussite."),

    ("DOFD-8", 4, 5, "single",
     "Une initiative DevOps se heurte a une forte fatigue du changement (change fatigue). Quelle reponse est adaptee ?",
     [("Rythmer le changement, communiquer le sens et accompagner les personnes", True),
      ("Imposer encore plus de changements simultanes", False),
      ("Ignorer le ressenti des equipes", False),
      ("Supprimer toute communication", False)],
     "Face a la fatigue du changement, on cadence, on donne du sens et on accompagne (conduite du changement)."),

    ("DOFD-8", 4, 4, "single",
     "A quoi sert un centre d'excellence ou une plateforme interne pour le DevOps a l'echelle ?",
     [("Diffuser pratiques, outils et standards pour accelerer l'adoption entre equipes", True),
      ("Recentraliser et figer toutes les decisions", False),
      ("Supprimer l'autonomie des equipes", False),
      ("Interdire le partage", False)],
     "Centres d'excellence et plateformes internes mutualisent pratiques/outils et accelerent l'adoption a l'echelle."),

    ("DOFD-8", 5, 4, "single",
     "Quel role jouent les parties prenantes (stakeholders) metier dans une demarche DevOps ?",
     [("Elles font partie integrante du flux de valeur et doivent etre impliquees", True),
      ("Elles n'ont aucun role hors de l'IT", False),
      ("Elles ralentissent toujours le projet", False),
      ("Elles ne sont consultees qu'a la toute fin", False)],
     "Le DevOps implique les metiers comme parties prenantes du flux de valeur, pas seulement l'IT."),

    ("DOFD-8", 6, 5, "single",
     "Pour faire passer le DevOps d'un pilote reussi a toute l'entreprise, quelle approche est la plus sure ?",
     [("Diffuser progressivement en s'appuyant sur les apprentissages, les communautes et une plateforme commune", True),
      ("Imposer partout d'un coup sans accompagnement", False),
      ("Arreter de mesurer une fois le pilote fini", False),
      ("Recreer des silos a l'echelle", False)],
     "On etend par diffusion progressive, en capitalisant les apprentissages et en s'appuyant sur communautes et plateforme."),

    ("DOFD-8", 7, 5, "single",
     "Comment faire evoluer durablement les pratiques DevOps dans le temps ?",
     [("Par des cycles continus d'experimentation, de mesure et d'amelioration (Kata/Kaizen)", True),
      ("En figeant les processus une fois pour toutes", False),
      ("En cessant de mesurer", False),
      ("En supprimant les retours d'experience", False)],
     "L'evolution durable repose sur l'amelioration continue : experimenter, mesurer, apprendre, recommencer."),

    ("DOFD-8", 6, 5, "single",
     "Quel est l'interet d'un dojo ou d'un apprentissage immersif pour faire evoluer les equipes ?",
     [("Apprendre de nouvelles façons de travailler par la pratique encadree, transferable au quotidien", True),
      ("Remplacer toute documentation", False),
      ("Eviter la pratique reelle", False),
      ("Centraliser les decisions", False)],
     "Le dojo/apprentissage immersif fait monter les equipes en competence par la pratique accompagnee, ancree dans le reel."),

    ("DOFD-8", 5, 4, "single",
     "Pourquoi le partage (le 'S' de CALMS) est-il un pilier du DevOps ?",
     [("Partager savoirs, retours et succes diffuse l'amelioration et brise les silos", True),
      ("Pour augmenter le secret entre equipes", False),
      ("Pour ralentir l'apprentissage", False),
      ("Parce qu'il remplace l'automatisation", False)],
     "Le partage (Sharing) diffuse connaissances et retours, accelere l'apprentissage collectif et reduit les silos."),

    # ======================================================================= #
    # 3e serie — volume additionnel pour reduire le recouvrement entre examens #
    # Angles nouveaux, types varies (vrai/faux, choix multiple), K2 a K7.      #
    # ======================================================================= #

    # ----------------------------- DOFD-1 ---------------------------------- #
    ("DOFD-1", 2, 2, "truefalse",
     "Le DevOps se resume a l'achat et a l'installation d'outils.",
     [("Vrai", False), ("Faux", True)],
     "Faux : le DevOps combine personnes, processus et outils ; l'outillage seul ne fait pas le DevOps."),

    ("DOFD-1", 2, 2, "single",
     "Quel est l'objectif premier du DevOps ?",
     [("Livrer de la valeur plus vite et de maniere fiable, de l'idee a la production", True),
      ("Reduire le nombre de developpeurs", False),
      ("Eliminer la phase de test", False),
      ("Produire le plus de code possible", False)],
     "Le DevOps vise a accelerer la livraison de valeur fiable de bout en bout."),

    ("DOFD-1", 3, 3, "single",
     "Une organisation se felicite du nombre de fonctionnalites livrees, sans regarder leur usage reel. Quel piege guette ?",
     [("Le syndrome de l'usine a fonctionnalites : produire beaucoup sans creer de valeur d'usage", True),
      ("Un exces d'orientation client", False),
      ("Trop de mesure de la valeur", False),
      ("Une dette technique nulle", False)],
     "Mesurer la production plutot que la valeur d'usage conduit a la 'feature factory' : beaucoup d'outputs, peu d'outcomes."),

    ("DOFD-1", 3, 3, "truefalse",
     "Le DevOps ne s'applique qu'aux start-ups et pas aux grandes organisations avec du legacy.",
     [("Vrai", False), ("Faux", True)],
     "Faux : le DevOps s'applique aussi aux grandes organisations et aux systemes existants, avec une adaptation du rythme."),

    ("DOFD-1", 3, 3, "single",
     "En quoi le DevOps reduit-il le time-to-market ?",
     [("En fluidifiant et automatisant le flux de l'idee a la production", True),
      ("En supprimant les exigences de qualite", False),
      ("En allongeant les cycles de livraison", False),
      ("En ajoutant des transferts entre equipes", False)],
     "Le DevOps raccourcit le delai idee->production en fluidifiant et automatisant le flux de valeur."),

    ("DOFD-1", 4, 4, "single",
     "Quelle est la difference entre « faire du DevOps » et « etre DevOps » ?",
     [("'Faire' = adopter quelques pratiques ; 'etre' = un etat d'esprit et une culture durables", True),
      ("Aucune difference", False),
      ("'Etre DevOps' signifie ne plus rien automatiser", False),
      ("'Faire du DevOps' signifie supprimer les operations", False)],
     "Au-dela des pratiques ponctuelles, le DevOps est surtout une culture et un etat d'esprit durables."),

    ("DOFD-1", 4, 4, "truefalse",
     "Adopter le DevOps garantit l'absence totale d'incidents en production.",
     [("Vrai", False), ("Faux", True)],
     "Faux : le DevOps vise la resilience et un retablissement rapide, pas l'illusion du zero incident."),

    ("DOFD-1", 4, 4, "single",
     "Quel benefice du DevOps profite le plus directement au client final ?",
     [("Une valeur livree plus rapidement et de maniere plus fiable", True),
      ("Un nombre de reunions internes plus eleve", False),
      ("Davantage de documentation interne", False),
      ("Une organisation plus cloisonnee", False)],
     "Pour le client, le benefice tangible est une valeur livree plus vite et plus surement."),

    ("DOFD-1", 4, 4, "multiple",
     "Quels signes revelent une organisation a la culture DevOps mature ?",
     [("Responsabilite partagee Dev/Ops", True),
      ("Amelioration continue et mesure", True),
      ("Collaboration entre equipes", True),
      ("Cloisonnement et culture du blame", False)],
     "Responsabilite partagee, amelioration continue/mesure et collaboration caracterisent une culture DevOps mature."),

    ("DOFD-1", 5, 4, "single",
     "Une transformation imposee d'en haut, sans adhesion des equipes, echoue souvent. Que manque-t-il le plus ?",
     [("L'engagement des equipes, en complement du soutien du leadership", True),
      ("Davantage d'outils", False),
      ("Plus de validations manuelles", False),
      ("Un cloisonnement renforce", False)],
     "Le changement reussit quand le leadership ET l'adhesion des equipes se conjuguent ; l'un sans l'autre echoue."),

    ("DOFD-1", 5, 4, "truefalse",
     "Le DevOps supprime purement et simplement le besoin d'operations.",
     [("Vrai", False), ("Faux", True)],
     "Faux : les operations ne disparaissent pas, elles evoluent (ex. SRE, equipes plateforme) et collaborent avec le Dev."),

    ("DOFD-1", 6, 5, "single",
     "Pour evaluer la maturite DevOps d'une organisation, quelle approche est la plus pertinente ?",
     [("Apprecier ensemble culture, pratiques, automatisation et mesure, plutot qu'un seul critere", True),
      ("Compter uniquement le nombre d'outils installes", False),
      ("Mesurer seulement les lignes de code", False),
      ("Se fier au nombre d'employes", False)],
     "La maturite s'evalue de maniere multidimensionnelle (culture, pratiques, automatisation, mesure), pas sur un critere unique."),

    # ----------------------------- DOFD-2 ---------------------------------- #
    ("DOFD-2", 2, 2, "single",
     "Que privilegie la Premiere Voie (le flux) ?",
     [("Le flux de gauche a droite, du developpement vers la production", True),
      ("Les retours de droite a gauche", False),
      ("L'experimentation continue", False),
      ("La suppression des tests", False)],
     "La Premiere Voie optimise le flux de travail du developpement vers les operations (gauche->droite)."),

    ("DOFD-2", 2, 2, "truefalse",
     "Augmenter le travail en cours (WIP) accelere toujours la livraison.",
     [("Vrai", False), ("Faux", True)],
     "Faux : trop d'en-cours augmente les attentes et le temps de cycle ; on cherche au contraire a limiter le WIP."),

    ("DOFD-2", 3, 3, "single",
     "Quel est l'apport principal de la Deuxieme Voie (retroaction) ?",
     [("Creer des boucles de retour rapides pour corriger au plus tot", True),
      ("Supprimer toute mesure", False),
      ("Allonger les cycles de validation", False),
      ("Empecher la communication amont", False)],
     "La Deuxieme Voie etablit des boucles de retroaction rapides et constantes pour corriger tot."),

    ("DOFD-2", 3, 3, "single",
     "Selon la Theorie des Contraintes, quel est le tout premier pas ?",
     [("Identifier la contrainte (le goulot) du systeme", True),
      ("Elever la contrainte avant de l'identifier", False),
      ("Optimiser toutes les etapes en meme temps", False),
      ("Ignorer le systeme", False)],
     "La ToC commence par identifier la contrainte, avant de l'exploiter, subordonner, puis elever."),

    ("DOFD-2", 3, 3, "truefalse",
     "Optimiser une etape qui n'est pas la contrainte augmente le debit global du systeme.",
     [("Vrai", False), ("Faux", True)],
     "Faux : seule l'amelioration de la contrainte accroit le debit global (Theorie des Contraintes)."),

    ("DOFD-2", 4, 4, "single",
     "Dans The Phoenix Project, quels sont les quatre types de travail ?",
     [("Projets metier, projets internes, changements et travail non planifie", True),
      ("Code, tests, build et deploiement", False),
      ("Dev, Ops, QA et securite", False),
      ("Planifie, urgent, important et secondaire", False)],
     "Les quatre types : projets metier, projets internes, changements et travail non planifie."),

    ("DOFD-2", 4, 4, "single",
     "Pourquoi rendre le travail visible est-il un prealable a l'amelioration du flux ?",
     [("On ne peut gerer et ameliorer que ce que l'on voit (goulots, en-cours, blocages)", True),
      ("Cela complique inutilement le suivi", False),
      ("Cela cache les problemes", False),
      ("Cela remplace la mesure", False)],
     "Visualiser le travail revele goulots et blocages : c'est la condition pour agir et ameliorer le flux."),

    ("DOFD-2", 4, 4, "multiple",
     "Parmi ces pratiques, lesquelles servent directement la Premiere Voie (le flux) ?",
     [("Limiter le travail en cours", True),
      ("Reduire la taille des lots", True),
      ("Rendre le travail visible", True),
      ("Punir les porteurs de mauvaises nouvelles", False)],
     "Limiter le WIP, reduire les lots et rendre le travail visible ameliorent le flux (Premiere Voie)."),

    ("DOFD-2", 5, 5, "single",
     "Le debit d'un service est de 5 elements/jour et l'en-cours moyen de 20. Quel temps de cycle moyen la loi de Little donne-t-elle ?",
     [("Environ 4 jours", True),
      ("Environ 100 jours", False),
      ("Environ 0,25 jour", False),
      ("Environ 25 jours", False)],
     "Little : temps de cycle = en-cours / debit = 20 / 5 = 4 jours."),

    ("DOFD-2", 6, 5, "single",
     "Une equipe ajoute des personnes sur une etape deja rapide, en amont du veritable goulot. Quel resultat attendre ?",
     [("Plus d'en-cours s'accumule devant le goulot, sans gain de debit", True),
      ("Le debit global double", False),
      ("La contrainte disparait d'elle-meme", False),
      ("Le temps de cycle diminue fortement", False)],
     "Renforcer une etape non contrainte ne fait qu'empiler l'en-cours devant le goulot : le debit global ne change pas."),

    ("DOFD-2", 7, 5, "single",
     "Comment les Trois Voies et la Theorie des Contraintes se completent-elles dans une demarche d'amelioration ?",
     [("La ToC localise la contrainte ; les Trois Voies guident flux, retroaction et apprentissage pour la traiter durablement", True),
      ("Elles s'opposent et ne peuvent etre utilisees ensemble", False),
      ("La ToC interdit toute retroaction", False),
      ("Les Trois Voies ignorent le flux", False)],
     "La ToC cible ou agir (la contrainte) ; les Trois Voies fournissent le cadre (flux, retours, apprentissage) pour ameliorer durablement."),

    # ----------------------------- DOFD-3 ---------------------------------- #
    ("DOFD-3", 2, 2, "truefalse",
     "L'integration continue consiste a integrer le code rarement, en gros lots.",
     [("Vrai", False), ("Faux", True)],
     "Faux : la CI integre frequemment (souvent plusieurs fois par jour), en petits increments valides automatiquement."),

    ("DOFD-3", 3, 3, "single",
     "Quel est l'objectif d'un pipeline de deploiement ?",
     [("Automatiser et fiabiliser le passage du code de l'integration jusqu'a la production", True),
      ("Ralentir volontairement les livraisons", False),
      ("Remplacer le controle de version", False),
      ("Supprimer les tests", False)],
     "Le pipeline de deploiement automatise les etapes (build, tests, deploiement) pour livrer de maniere fiable et repetable."),

    ("DOFD-3", 3, 3, "single",
     "Quelle strategie permet un retour arriere instantane en basculant entre deux environnements identiques ?",
     [("Le deploiement Blue-Green", True),
      ("Le deploiement big bang", False),
      ("Le gel des versions", False),
      ("La suppression des sauvegardes", False)],
     "Le Blue-Green maintient deux environnements ; on bascule le trafic et on peut revenir instantanement en cas de probleme."),

    ("DOFD-3", 3, 4, "truefalse",
     "Un SLA et un SLO designent exactement la meme chose.",
     [("Vrai", False), ("Faux", True)],
     "Faux : le SLO est un objectif interne de niveau de service ; le SLA est un engagement contractuel (souvent avec penalites)."),

    ("DOFD-3", 4, 4, "single",
     "Que mesure principalement un SLI (Service Level Indicator) ?",
     [("Une mesure quantitative concrete du niveau de service (ex. latence, disponibilite)", True),
      ("Un objectif contractuel avec penalites", False),
      ("Le nombre de developpeurs", False),
      ("Le budget du projet", False)],
     "Le SLI est l'indicateur mesure (latence, taux d'erreur, disponibilite) ; le SLO en fixe la cible."),

    ("DOFD-3", 4, 4, "single",
     "Une equipe a beaucoup de tests manuels lents et peu de tests automatises. Quel premier pas vers la CI/CD ?",
     [("Automatiser progressivement les tests, en commençant par une base de tests unitaires", True),
      ("Supprimer tous les tests existants", False),
      ("Deployer directement sans tester", False),
      ("Augmenter encore les tests manuels", False)],
     "On automatise par etapes, en batissant d'abord une base solide de tests unitaires rapides."),

    ("DOFD-3", 4, 4, "multiple",
     "Lesquelles sont des pratiques techniques cles du DevOps ?",
     [("Integration continue", True),
      ("Livraison/deploiement continu", True),
      ("Tests automatises", True),
      ("Branches manuelles de tres longue duree", False)],
     "CI, livraison/deploiement continu et tests automatises sont des pratiques techniques cles ; les branches longues sont un anti-pattern."),

    ("DOFD-3", 5, 4, "single",
     "A quoi sert principalement l'observabilite (logs, metriques, traces) ?",
     [("Comprendre l'etat interne d'un systeme a partir de ses sorties, pour diagnostiquer vite", True),
      ("Empecher tout deploiement", False),
      ("Remplacer les tests unitaires", False),
      ("Augmenter le couplage", False)],
     "L'observabilite (logs, metriques, traces) permet de comprendre et diagnostiquer le comportement d'un systeme en production."),

    ("DOFD-3", 5, 5, "single",
     "Un service a un SLO de 99,5 % sur 30 jours. A combien d'indisponibilite correspond environ le budget d'erreur ?",
     [("Environ 3 h 36 min sur le mois", True),
      ("Environ 30 minutes sur le mois", False),
      ("Zero minute", False),
      ("Environ 15 heures sur le mois", False)],
     "0,5 % de 30 jours (43 200 min) = 216 min, soit environ 3 h 36 : c'est le budget d'erreur tolere."),

    ("DOFD-3", 6, 5, "single",
     "Pourquoi le deploiement continu sans suite de tests fiable est-il dangereux ?",
     [("L'automatisation propage instantanement les defauts en production", True),
      ("Il ralentit trop les livraisons", False),
      ("Il empeche toute mise en production", False),
      ("Il supprime le besoin d'observabilite", False)],
     "Sans tests fiables, le deploiement continu pousse automatiquement aussi les regressions : les defauts arrivent vite en prod."),

    ("DOFD-3", 6, 5, "single",
     "Quelle pratique reduit le risque d'une mise en production tout en collectant des donnees reelles, en comparant deux variantes ?",
     [("Le test A/B (ou deploiement progressif compare)", True),
      ("Le gel complet des deploiements", False),
      ("La suppression de la telemetrie", False),
      ("Le big bang sans mesure", False)],
     "Le test A/B expose des variantes a des sous-ensembles d'utilisateurs et compare les resultats reels avant generalisation."),

    ("DOFD-3", 7, 5, "single",
     "Pour reduire durablement le MTTR d'un service critique, quelle combinaison est la plus efficace ?",
     [("Observabilite, alerting pertinent, runbooks et rollback automatise", True),
      ("Davantage de validations manuelles en cas d'incident", False),
      ("Supprimer la supervision pour reduire le bruit", False),
      ("Attendre que les utilisateurs signalent les pannes", False)],
     "Detecter vite (observabilite, alertes) et restaurer vite (runbooks, rollback automatise) fait baisser le MTTR."),

    # ----------------------------- DOFD-4 ---------------------------------- #
    ("DOFD-4", 2, 2, "single",
     "Que cherche a maximiser le Lean ?",
     [("La valeur pour le client en eliminant les gaspillages", True),
      ("Le nombre d'etapes du processus", False),
      ("La taille des lots", False),
      ("Le stock d'en-cours", False)],
     "Le Lean maximise la valeur client en supprimant les gaspillages (muda) tout au long du flux."),

    ("DOFD-4", 2, 2, "truefalse",
     "Dans Scrum, le Scrum Master priorise le backlog produit.",
     [("Vrai", False), ("Faux", True)],
     "Faux : c'est le Product Owner qui priorise le backlog ; le Scrum Master facilite le processus et leve les obstacles."),

    ("DOFD-4", 3, 3, "single",
     "Quel evenement Scrum sert principalement a l'inspection et a l'adaptation du processus de l'equipe ?",
     [("La retrospective de sprint", True),
      ("La revue de sprint (demo)", False),
      ("La planification de sprint", False),
      ("Le daily standup", False)],
     "La retrospective inspecte le fonctionnement de l'equipe et decide des ameliorations pour le sprint suivant."),

    ("DOFD-4", 3, 3, "single",
     "Que represente le 'pull' (flux tire) en Lean/Kanban ?",
     [("Demarrer un nouveau travail seulement quand il y a de la capacite disponible", True),
      ("Pousser le maximum de travail dans le systeme", False),
      ("Supprimer toute limite de WIP", False),
      ("Ignorer la demande client", False)],
     "Le flux tire (pull) declenche le travail en fonction de la capacite reelle, evitant la surcharge."),

    ("DOFD-4", 3, 4, "truefalse",
     "ITIL et DevOps sont fondamentalement incompatibles.",
     [("Vrai", False), ("Faux", True)],
     "Faux : ITIL (gestion des services) et DevOps sont complementaires ; on applique l'agilite aux processus de service."),

    ("DOFD-4", 4, 4, "single",
     "Une organisation veut un financement aligne sur la valeur livree en continu. Quel modele adopter ?",
     [("Le financement par produit (equipes perennes) plutot que par projet", True),
      ("Un budget unique fige sur cinq ans", False),
      ("Le financement par tache isolee", False),
      ("La suppression de tout budget", False)],
     "Le financement par produit soutient des equipes durables centrees sur un flux de valeur continu."),

    ("DOFD-4", 4, 4, "single",
     "Quel cadre fournit des roles comme Release Train Engineer et des Agile Release Trains ?",
     [("SAFe (Scaled Agile Framework)", True),
      ("Scrum simple", False),
      ("Kanban personnel", False),
      ("Le modele en cascade", False)],
     "SAFe structure l'agilite a l'echelle avec, notamment, les Agile Release Trains et le Release Train Engineer."),

    ("DOFD-4", 4, 4, "multiple",
     "Lesquels sont des cadres ou approches mobilisables en complement du DevOps ?",
     [("Agile / Scrum", True),
      ("Lean", True),
      ("ITSM / ITIL", True),
      ("Le rejet de toute mesure", False)],
     "Agile, Lean et ITSM/ITIL se combinent avec le DevOps ; le refus de mesurer n'est pas un cadre."),

    ("DOFD-4", 5, 4, "single",
     "Quel est l'esprit du cycle d'amelioration Kaizen ?",
     [("Des ameliorations continues, petites et frequentes, par tous", True),
      ("Une seule grande transformation tous les cinq ans", False),
      ("L'arret de toute remise en question", False),
      ("La centralisation des decisions d'amelioration", False)],
     "Le Kaizen promeut l'amelioration continue par petites touches, impliquant l'ensemble des acteurs."),

    ("DOFD-4", 6, 5, "single",
     "Une equipe applique Scrum a la lettre mais reste lente a livrer en production. Quelle piste est la plus pertinente ?",
     [("Etendre l'amelioration au flux de livraison (CI/CD, ToC) au-dela des seules ceremonies Scrum", True),
      ("Ajouter davantage de reunions Scrum", False),
      ("Abandonner toute mesure", False),
      ("Allonger la duree des sprints a six mois", False)],
     "Scrum gere le 'quoi/quand' cote produit ; livrer vite exige aussi d'optimiser le flux technique (CI/CD) et la contrainte."),

    ("DOFD-4", 6, 5, "single",
     "En quoi la cartographie de la chaine de valeur aide-t-elle a prioriser les ameliorations ?",
     [("Elle revele les temps d'attente et gaspillages, indiquant ou agir en priorite", True),
      ("Elle augmente le nombre d'etapes", False),
      ("Elle masque les goulots", False),
      ("Elle remplace la strategie produit", False)],
     "Le VSM rend visibles attentes et gaspillages le long du flux, ce qui oriente les efforts d'amelioration."),

    ("DOFD-4", 7, 5, "single",
     "Pour reduire le delai de livraison d'un bout a l'autre, quelle sequence d'actions Lean/ToC est la plus coherente ?",
     [("Cartographier le flux, identifier la contrainte, reduire lots et en-cours, puis automatiser", True),
      ("Augmenter l'en-cours, puis ajouter des validations manuelles", False),
      ("Multiplier les transferts entre equipes", False),
      ("Optimiser une etape au hasard", False)],
     "On rend le flux visible (VSM), on cible la contrainte, on reduit lots/en-cours, puis on automatise : demarche Lean/ToC."),

    # ----------------------------- DOFD-5 ---------------------------------- #
    ("DOFD-5", 2, 2, "truefalse",
     "Une culture du blame ameliore la remontee des problemes.",
     [("Vrai", False), ("Faux", True)],
     "Faux : la peur de la sanction fait taire les signaux ; une culture sans blame favorise la remontee et l'apprentissage."),

    ("DOFD-5", 2, 2, "single",
     "Que designe une culture « generative » selon Westrum ?",
     [("Une culture orientee performance, ou l'information circule et la cooperation est forte", True),
      ("Une culture ou l'information est dissimulee", False),
      ("Une culture qui punit les messagers", False),
      ("Une culture sans aucune regle", False)],
     "Chez Westrum, la culture generative privilegie la circulation de l'information et la cooperation orientee mission."),

    ("DOFD-5", 3, 3, "single",
     "Qu'est-ce qu'un post-mortem « sans blame » (blameless) ?",
     [("Une analyse d'incident centree sur les causes systemiques, pas sur la recherche d'un coupable", True),
      ("Un rapport qui designe le responsable a sanctionner", False),
      ("Une reunion sans aucune analyse", False),
      ("Un document confidentiel jamais partage", False)],
     "Le post-mortem sans blame cherche les causes systemiques et les apprentissages, sans designer de coupable."),

    ("DOFD-5", 3, 3, "single",
     "Pourquoi la diversite et l'inclusion sont-elles utiles a une equipe DevOps ?",
     [("Elles enrichissent les points de vue et ameliorent la resolution de problemes", True),
      ("Elles ralentissent toujours les decisions", False),
      ("Elles n'ont aucun effet sur la performance", False),
      ("Elles remplacent l'automatisation", False)],
     "Des perspectives variees ameliorent la creativite et la qualite des decisions, utiles a la resolution de problemes."),

    ("DOFD-5", 3, 4, "truefalse",
     "La loi de Conway affirme que l'architecture d'un systeme tend a refleter la structure de communication de l'organisation.",
     [("Vrai", True), ("Faux", False)],
     "Vrai : c'est l'enonce de la loi de Conway ; d'ou l'interet de structurer les equipes en consequence."),

    ("DOFD-5", 4, 4, "single",
     "Qu'est-ce qu'une « team topology » de type equipe plateforme ?",
     [("Une equipe qui fournit en self-service des capacites reutilisables aux equipes produit", True),
      ("Une equipe qui valide manuellement chaque deploiement", False),
      ("Une equipe sans aucune mission", False),
      ("Une equipe qui centralise toutes les decisions metier", False)],
     "L'equipe plateforme offre des services/outils en self-service pour reduire la charge cognitive des equipes produit."),

    ("DOFD-5", 4, 4, "single",
     "Que vise a reduire une bonne conception d'equipes et de plateformes ?",
     [("La charge cognitive pesant sur les equipes produit", True),
      ("Le nombre de tests automatises", False),
      ("La securite psychologique", False),
      ("La circulation de l'information", False)],
     "Reduire la charge cognitive des equipes (via plateformes/self-service) leur permet de se concentrer sur la valeur."),

    ("DOFD-5", 4, 4, "multiple",
     "Quels elements favorisent une culture DevOps saine ?",
     [("Securite psychologique", True),
      ("Apprentissage des echecs (sans blame)", True),
      ("Responsabilite partagee", True),
      ("Cloisonnement de l'information", False)],
     "Securite psychologique, apprentissage sans blame et responsabilite partagee nourrissent une culture DevOps saine."),

    ("DOFD-5", 5, 4, "single",
     "Quel risque y a-t-il a reorganiser les equipes sans tenir compte de la loi de Conway ?",
     [("Obtenir une architecture qui contredit l'organisation, source de frictions", True),
      ("Aucune consequence sur l'architecture", False),
      ("Une suppression automatique de la dette technique", False),
      ("Une amelioration garantie du flux", False)],
     "Ignorer Conway peut produire un desalignement entre structure d'equipes et architecture, generant des frictions."),

    ("DOFD-5", 6, 5, "single",
     "Une transformation suscite resistance et anxiete. Quelle reponse manageriale est la plus alignee sur la conduite du changement ?",
     [("Communiquer le sens, accompagner les emotions (courbe du changement) et impliquer les equipes", True),
      ("Imposer le changement sans explication", False),
      ("Sanctionner ceux qui expriment des doutes", False),
      ("Cacher les objectifs de la transformation", False)],
     "Accompagner les emotions (Kubler-Ross), donner du sens et impliquer les equipes facilite l'adoption du changement."),

    ("DOFD-5", 6, 5, "single",
     "Pourquoi la « manoeuvre de Conway inverse » est-elle utile en DevOps ?",
     [("Elle façonne volontairement les equipes pour obtenir l'architecture modulaire visee", True),
      ("Elle interdit toute API entre services", False),
      ("Elle centralise toutes les equipes en une seule", False),
      ("Elle supprime la communication", False)],
     "On organise deliberement les equipes (autonomes, alignees sur les services) pour induire l'architecture cible."),

    ("DOFD-5", 7, 5, "single",
     "Comment evaluer si une initiative culturelle DevOps porte ses fruits, au-dela des outils ?",
     [("Observer la collaboration, la securite psychologique, l'apprentissage et des indicateurs comme les metriques DORA", True),
      ("Compter uniquement le nombre de deploiements", False),
      ("Se fier au nombre d'outils installes", False),
      ("Mesurer la quantite de documentation produite", False)],
     "On combine signaux culturels (collaboration, securite psychologique, apprentissage) et indicateurs de performance (DORA)."),

    # ----------------------------- DOFD-6 ---------------------------------- #
    ("DOFD-6", 2, 2, "truefalse",
     "L'Infrastructure as Code consiste a configurer les serveurs manuellement, sans versionner.",
     [("Vrai", False), ("Faux", True)],
     "Faux : l'IaC decrit l'infrastructure dans des fichiers versionnes, reproductibles et automatisables."),

    ("DOFD-6", 2, 2, "single",
     "Quel est l'avantage cle de la conteneurisation ?",
     [("Une portabilite et une coherence d'execution entre environnements", True),
      ("La suppression du besoin de reseau", False),
      ("L'elimination de tout test", False),
      ("Le ralentissement des deploiements", False)],
     "Le conteneur embarque l'application et ses dependances : meme comportement d'un environnement a l'autre."),

    ("DOFD-6", 3, 3, "single",
     "A quoi sert un outil de gestion de configuration (ex. type Ansible) ?",
     [("Amener et maintenir les systemes dans un etat cible de maniere automatisee et idempotente", True),
      ("Compiler le code source", False),
      ("Remplacer le controle de version du code", False),
      ("Gerer la paie", False)],
     "La gestion de configuration applique automatiquement un etat cible, idealement de façon idempotente."),

    ("DOFD-6", 3, 3, "single",
     "Que designe le pipeline « as code » ?",
     [("La definition du pipeline CI/CD dans des fichiers versionnes, au meme titre que le code", True),
      ("Un pipeline configure uniquement a la main", False),
      ("Un pipeline sans aucune etape de test", False),
      ("Un pipeline qui ne peut pas etre modifie", False)],
     "Decrire le pipeline 'as code' le rend versionne, revisable et reproductible, comme le reste du code."),

    ("DOFD-6", 3, 4, "truefalse",
     "Dans une infrastructure immuable, on modifie les serveurs existants en place a chaque changement.",
     [("Vrai", False), ("Faux", True)],
     "Faux : l'infrastructure immuable remplace les instances par de nouvelles plutot que de les modifier en place."),

    ("DOFD-6", 4, 4, "single",
     "Pourquoi l'idempotence est-elle souhaitable pour un script de provisioning ?",
     [("Reexecuter le script doit converger vers le meme etat sans effets de bord indesirables", True),
      ("Chaque execution doit produire un etat different", False),
      ("Cela empeche toute automatisation", False),
      ("Cela impose une execution unique", False)],
     "L'idempotence garantit qu'appliquer N fois le script aboutit au meme etat cible, condition d'une automatisation fiable."),

    ("DOFD-6", 4, 4, "single",
     "Quel composant fournit, a la demande, des ressources de calcul et de stockage virtualisees ?",
     [("Le cloud (IaaS)", True),
      ("Un depot d'artefacts", False),
      ("Un systeme de tickets", False),
      ("Un tableau Kanban", False)],
     "L'IaaS (cloud) fournit a la demande calcul, stockage et reseau virtualises, supports de l'elasticite."),

    ("DOFD-6", 4, 4, "multiple",
     "Lesquels sont des maillons typiques d'une chaine d'outils DevOps ?",
     [("Controle de version", True),
      ("Serveur d'integration continue", True),
      ("Outil de supervision/observabilite", True),
      ("Logiciel de comptabilite", False)],
     "Controle de version, CI et supervision sont des maillons types d'une toolchain ; la comptabilite n'en fait pas partie."),

    ("DOFD-6", 5, 4, "single",
     "Quel interet d'integrer la supervision et l'alerting des la conception d'un service ?",
     [("Detecter et diagnostiquer les problemes tot, et soutenir un retablissement rapide", True),
      ("Augmenter le couplage entre services", False),
      ("Eviter de mesurer la production", False),
      ("Empecher les deploiements", False)],
     "Concevoir l'observabilite des le depart accelere la detection et le diagnostic, donc le retablissement."),

    ("DOFD-6", 6, 5, "single",
     "Quel compromis accompagne le passage a une architecture microservices ?",
     [("Plus d'autonomie de deploiement, mais une complexite distribuee accrue (reseau, donnees, observabilite)", True),
      ("Aucune contrepartie", False),
      ("Moins de besoins d'automatisation", False),
      ("Une suppression du besoin de tests", False)],
     "Les microservices apportent l'autonomie de deploiement au prix d'une complexite distribuee a maitriser."),

    ("DOFD-6", 6, 5, "single",
     "Pourquoi automatiser les controles de securite dans le pipeline (DevSecOps) plutot qu'en fin de cycle ?",
     [("Pour detecter les vulnerabilites tot, a moindre cout, sans freiner le flux", True),
      ("Pour concentrer la securite juste avant la mise en production", False),
      ("Pour supprimer les controles", False),
      ("Pour confier la securite a une seule personne", False)],
     "Integrer et automatiser la securite tot (shift left) reduit cout et delai de correction tout en preservant le flux."),

    ("DOFD-6", 7, 5, "single",
     "Pour fiabiliser des deploiements frequents sur une infrastructure cloud, quelle combinaison est la plus robuste ?",
     [("IaC versionnee, infrastructure immuable, pipeline automatise et rollback rapide", True),
      ("Configuration manuelle et deploiements espaces", False),
      ("Absence de tests pour aller plus vite", False),
      ("Modifications directes en production sans tracabilite", False)],
     "IaC, immuabilite, pipeline automatise et rollback rapide forment une base robuste pour des deploiements frequents et surs."),

    # ----------------------------- DOFD-7 ---------------------------------- #
    ("DOFD-7", 2, 2, "single",
     "Combien de metriques cles le modele DORA definit-il ?",
     [("Quatre", True), ("Deux", False), ("Sept", False), ("Dix", False)],
     "DORA definit quatre metriques cles : frequence de deploiement, lead time, taux d'echec des changements, MTTR."),

    ("DOFD-7", 2, 2, "truefalse",
     "Le nombre d'heures travaillees est une bonne mesure de la productivite d'une equipe DevOps.",
     [("Vrai", False), ("Faux", True)],
     "Faux : c'est une vanity metric ; on prefere des mesures actionnables liees au flux et a la valeur (ex. DORA)."),

    ("DOFD-7", 3, 3, "single",
     "Que mesure la frequence de deploiement ?",
     [("A quelle cadence l'organisation met du code en production", True),
      ("La duree de reparation d'un incident", False),
      ("Le pourcentage de changements en echec", False),
      ("Le nombre d'employes", False)],
     "La frequence de deploiement indique la cadence des mises en production : une mesure de vitesse."),

    ("DOFD-7", 3, 3, "single",
     "Pourquoi suivre une metrique dans le temps plutot qu'a un instant donne ?",
     [("Pour observer la tendance et l'effet des ameliorations", True),
      ("Pour impressionner sans rien decider", False),
      ("Parce qu'une seule mesure suffit toujours", False),
      ("Pour eviter d'agir", False)],
     "Une tendance dans le temps revele si les actions d'amelioration produisent un effet, contrairement a une mesure isolee."),

    ("DOFD-7", 4, 4, "multiple",
     "Lesquelles font partie des quatre metriques DORA ?",
     [("Frequence de deploiement", True),
      ("Delai des changements (lead time)", True),
      ("Temps de retablissement (MTTR)", True),
      ("Nombre de lignes de code", False)],
     "Les quatre DORA : frequence de deploiement, lead time, taux d'echec des changements et temps de retablissement."),

    ("DOFD-7", 4, 4, "single",
     "Une metrique est detournee : l'equipe l'optimise au detriment du reste. Comment nomme-t-on ce phenomene ?",
     [("Le 'gaming' de la metrique (effet pervers)", True),
      ("Une amelioration continue saine", False),
      ("Une mesure actionnable", False),
      ("Un budget d'erreur", False)],
     "Optimiser une metrique pour elle-meme, au detriment du systeme, est un detournement ('gaming') a eviter."),

    ("DOFD-7", 4, 4, "single",
     "Quel lien entre les metriques DORA et la performance organisationnelle ?",
     [("De bonnes metriques DORA sont associees a une meilleure performance de livraison logicielle", True),
      ("Elles n'ont aucun lien avec la performance", False),
      ("Elles mesurent uniquement le cout des licences", False),
      ("Elles remplacent la strategie", False)],
     "Les recherches DORA relient de meilleures valeurs (vitesse + stabilite) a une meilleure performance de livraison."),

    ("DOFD-7", 5, 4, "single",
     "Pourquoi equilibrer metriques de vitesse et de stabilite ?",
     [("Pour eviter d'optimiser l'une en degradant l'autre, et refleter la vraie performance", True),
      ("Parce que seule la vitesse compte", False),
      ("Parce que seule la stabilite compte", False),
      ("Pour multiplier les vanity metrics", False)],
     "Vitesse et stabilite se lisent ensemble : les suivre conjointement evite les optimisations trompeuses."),

    ("DOFD-7", 5, 5, "single",
     "Sur 200 changements, 20 ont provoque une degradation necessitant correctif. Quel est le taux d'echec des changements ?",
     [("10 %", True), ("2 %", False), ("20 %", False), ("90 %", False)],
     "Change failure rate = 20 / 200 = 10 %."),

    ("DOFD-7", 6, 5, "single",
     "Une equipe affiche d'excellentes metriques DORA mais une forte rotation et un epuisement du personnel. Que conclure ?",
     [("La performance n'est pas durable : le bien-etre des equipes est aussi un facteur a suivre", True),
      ("Tout va bien, seules les metriques DORA comptent", False),
      ("Il faut accelerer encore au detriment des equipes", False),
      ("Le burnout ameliore la performance", False)],
     "Des metriques techniques solides ne suffisent pas : la soutenabilite (bien-etre, charge) conditionne la performance durable."),

    ("DOFD-7", 7, 5, "single",
     "Comment concevoir un tableau de bord de pilotage DevOps reellement utile ?",
     [("Peu d'indicateurs actionnables (ex. DORA), suivis dans le temps, relies a des decisions", True),
      ("Le plus grand nombre possible de vanity metrics", False),
      ("Des indicateurs qu'on ne regarde jamais", False),
      ("Une seule mesure ponctuelle annuelle", False)],
     "Un bon tableau de bord privilegie quelques indicateurs actionnables, suivis dans la duree et relies a des decisions."),

    # ----------------------------- DOFD-8 ---------------------------------- #
    ("DOFD-8", 2, 2, "truefalse",
     "Concentrer une connaissance critique sur une seule personne est une bonne pratique de partage.",
     [("Vrai", False), ("Faux", True)],
     "Faux : un 'bus factor' de 1 est un risque ; on diffuse le savoir (binomage, documentation, communautes)."),

    ("DOFD-8", 2, 2, "single",
     "Que designe une communaute de pratique ?",
     [("Un groupe transverse qui partage savoir-faire et standards autour d'un domaine", True),
      ("Un silo etanche supplementaire", False),
      ("Une equipe projet temporaire unique", False),
      ("Un outil de supervision", False)],
     "La communaute de pratique reunit des personnes de plusieurs equipes pour partager et faire progresser un savoir-faire."),

    ("DOFD-8", 3, 3, "single",
     "Quel est l'interet principal d'un post-mortem partage a l'echelle de l'organisation ?",
     [("Diffuser les apprentissages pour eviter que d'autres equipes repetent le meme incident", True),
      ("Designer un coupable a sanctionner", False),
      ("Garder l'incident secret", False),
      ("Eviter toute analyse", False)],
     "Partager les apprentissages d'un incident profite a toute l'organisation et previent les recidives ailleurs."),

    ("DOFD-8", 3, 3, "single",
     "Que favorise l'inner source au sein d'une entreprise ?",
     [("La contribution et la reutilisation de code entre equipes, a la maniere de l'open source", True),
      ("Le cloisonnement strict du code", False),
      ("La publication incontrolee a l'exterieur", False),
      ("La suppression du controle de version", False)],
     "L'inner source applique les pratiques open source en interne : partage, contribution et reutilisation entre equipes."),

    ("DOFD-8", 3, 4, "truefalse",
     "Le ChatOps permet de declencher et de tracer des operations depuis un canal de discussion partage.",
     [("Vrai", True), ("Faux", False)],
     "Vrai : le ChatOps integre conversation, outils et automatisation dans un canal partage et historise."),

    ("DOFD-8", 4, 4, "single",
     "Quel dispositif d'apprentissage immersif fait monter une equipe en competence par la pratique encadree ?",
     [("Le dojo DevOps", True),
      ("Un audit annuel", False),
      ("Un comite de pilotage", False),
      ("Un gel des deploiements", False)],
     "Le dojo immerge une equipe dans des pratiques nouvelles, accompagnee, pour un apprentissage transferable au quotidien."),

    ("DOFD-8", 4, 4, "multiple",
     "Lesquels sont des mecanismes de partage et de diffusion en DevOps ?",
     [("Communautes de pratique / guildes", True),
      ("Inner source", True),
      ("ChatOps et documentation partagee", True),
      ("Retention volontaire de l'information", False)],
     "Communautes/guildes, inner source, ChatOps et documentation diffusent le savoir ; la retention de l'information l'entrave."),

    ("DOFD-8", 4, 4, "single",
     "Pourquoi impliquer tot les parties prenantes metier dans une initiative DevOps ?",
     [("Parce qu'elles font partie du flux de valeur et alignent l'effort sur les besoins reels", True),
      ("Pour ralentir volontairement le projet", False),
      ("Pour les ecarter des decisions", False),
      ("Parce qu'elles n'ont aucun role", False)],
     "Les metiers font partie du flux de valeur ; les impliquer tot aligne l'effort sur les besoins reels."),

    ("DOFD-8", 5, 4, "single",
     "Quel est le role d'un sponsor executif dans la diffusion du DevOps a l'echelle ?",
     [("Donner le cap, lever les obstacles organisationnels et soutenir durablement le changement", True),
      ("Ecrire le code de production", False),
      ("Gerer les tickets de support", False),
      ("Interdire l'experimentation", False)],
     "Le sponsor executif porte la vision, debloque les obstacles et soutient le changement dans la duree."),

    ("DOFD-8", 6, 5, "single",
     "Une bonne pratique reussit dans une equipe pilote. Comment la diffuser sans la denaturer ?",
     [("La partager via communautes/plateforme en l'adaptant au contexte de chaque equipe", True),
      ("L'imposer a l'identique partout, sans adaptation", False),
      ("La garder secrete dans l'equipe pilote", False),
      ("Abandonner la mesure de ses effets", False)],
     "On diffuse en partageant et en adaptant au contexte (communautes, plateforme), plutot qu'en copiant aveuglement."),

    ("DOFD-8", 6, 5, "single",
     "Pourquoi l'amelioration continue est-elle indissociable du 'partage' en DevOps ?",
     [("Sans diffusion des apprentissages, les ameliorations restent locales et ne profitent pas a l'organisation", True),
      ("Parce que le partage remplace l'amelioration", False),
      ("Parce qu'il faut cesser de mesurer", False),
      ("Parce que l'amelioration doit rester secrete", False)],
     "Partager les apprentissages transforme des gains locaux en progres organisationnel : c'est le moteur de l'amelioration continue."),

    ("DOFD-8", 7, 5, "single",
     "Pour faire evoluer durablement une organisation DevOps, quelle combinaison est la plus solide ?",
     [("Communautes actives, plateforme commune, mesure partagee et cycles d'amelioration continue", True),
      ("Des silos renforces et une information retenue", False),
      ("Une transformation unique sans suivi", False),
      ("L'arret de toute experimentation une fois le pilote fini", False)],
     "L'evolution durable s'appuie sur le partage (communautes, plateforme), la mesure et des cycles d'amelioration continue."),
]

# --------------------------------------------------------------------------- #
# Base de donnees                                                             #
# --------------------------------------------------------------------------- #

SCHEMA = """
CREATE TABLE IF NOT EXISTS certification (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    pass_threshold  REAL NOT NULL,
    question_count  INTEGER NOT NULL,
    duration_min    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS domain (
    id               INTEGER PRIMARY KEY,
    certification_id INTEGER NOT NULL REFERENCES certification(id),
    code             TEXT NOT NULL,
    label            TEXT NOT NULL,
    weight           REAL NOT NULL,
    sort_order       INTEGER NOT NULL DEFAULT 0,
    UNIQUE(certification_id, code)
);
CREATE TABLE IF NOT EXISTS question (
    id           INTEGER PRIMARY KEY,
    domain_id    INTEGER NOT NULL REFERENCES domain(id),
    k_level      INTEGER NOT NULL,
    difficulty   INTEGER NOT NULL,
    qtype        TEXT NOT NULL,
    statement    TEXT NOT NULL,
    explanation  TEXT,
    status       TEXT NOT NULL DEFAULT 'published',
    content_hash TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS answer_option (
    id          INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES question(id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    is_correct  INTEGER NOT NULL DEFAULT 0,
    sort_order  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS app_user (
    id           INTEGER PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE,
    role         TEXT NOT NULL DEFAULT 'learner',
    locale       TEXT NOT NULL DEFAULT 'fr',
    target_score REAL NOT NULL DEFAULT 0.90,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS exam_session (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES app_user(id),
    mode        TEXT NOT NULL DEFAULT 'mock',
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    score       REAL,
    passed      INTEGER,
    status      TEXT NOT NULL DEFAULT 'in_progress'
);
CREATE TABLE IF NOT EXISTS exam_session_question (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES exam_session(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES question(id),
    position    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS attempt_log (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES app_user(id),
    question_id INTEGER NOT NULL REFERENCES question(id),
    domain_id   INTEGER NOT NULL REFERENCES domain(id),
    is_correct  INTEGER NOT NULL,
    context     TEXT,
    answered_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS mastery (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES app_user(id),
    domain_id INTEGER NOT NULL REFERENCES domain(id),
    score     REAL NOT NULL DEFAULT 0,
    attempts  INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, domain_id)
);
CREATE TABLE IF NOT EXISTS sr_card (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES app_user(id),
    question_id   INTEGER NOT NULL REFERENCES question(id),
    ease_factor   REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    due_date      TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE(user_id, question_id)
);
CREATE TABLE IF NOT EXISTS confidence_log (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES app_user(id),
    question_id INTEGER NOT NULL REFERENCES question(id),
    domain_id   INTEGER NOT NULL REFERENCES domain(id),
    context     TEXT,
    predicted   REAL NOT NULL,            -- probabilite de reussite predite (0..1)
    is_correct  INTEGER NOT NULL,         -- resultat observe (0/1)
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_question_domain ON question(domain_id, status);
CREATE INDEX IF NOT EXISTS idx_attempt_user ON attempt_log(user_id, domain_id);
CREATE INDEX IF NOT EXISTS idx_sr_due ON sr_card(user_id, due_date);
CREATE INDEX IF NOT EXISTS idx_esq_session ON exam_session_question(session_id);
CREATE INDEX IF NOT EXISTS idx_conf_user ON confidence_log(user_id, domain_id);
"""


def migrate(conn):
    """Ajoute de maniere idempotente les colonnes de la couche de second ordre,
    y compris sur une base existante (compatibilite ascendante)."""
    def cols(table):
        return {r["name"] for r in conn.execute("PRAGMA table_info(%s)" % table)}
    qcols = cols("question")
    if "theta_item" not in qcols:
        # Difficulte latente (echelle logit), initialisee depuis la difficulte editoriale.
        conn.execute("ALTER TABLE question ADD COLUMN theta_item REAL")
    # Initialise toute question encore sans difficulte latente (colonne neuve OU
    # nouvelles questions ajoutees par une mise a jour de la banque).
    conn.execute(
        "UPDATE question SET theta_item = (difficulty - 3) * ? WHERE theta_item IS NULL",
        (DIFF_LOGIT_SCALE,),
    )
    ucols = cols("app_user")
    if "second_order" not in ucols:
        conn.execute("ALTER TABLE app_user ADD COLUMN second_order INTEGER NOT NULL DEFAULT 0")
    if "theta_ability" not in ucols:
        conn.execute("ALTER TABLE app_user ADD COLUMN theta_ability REAL NOT NULL DEFAULT 0.0")
    conn.commit()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        migrate(conn)
        cur = conn.execute("SELECT id FROM certification WHERE code = ?", (CERT_CODE,))
        row = cur.fetchone()
        if row is None:
            cur = conn.execute(
                "INSERT INTO certification (code, label, pass_threshold, question_count, duration_min)"
                " VALUES (?, ?, ?, ?, ?)",
                (CERT_CODE, CERT_LABEL, PASS_THRESHOLD, QUESTION_COUNT, DURATION_MIN),
            )
            cert_id = cur.lastrowid
            for i, (code, label, weight) in enumerate(DOMAINS):
                conn.execute(
                    "INSERT INTO domain (certification_id, code, label, weight, sort_order)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (cert_id, code, label, weight, i),
                )
        # Domaines : map code -> id
        dom = {r["code"]: r["id"] for r in conn.execute("SELECT id, code FROM domain")}
        # Questions
        for (dcode, k, diff, qtype, stmt, options, expl) in QUESTIONS:
            h = hashlib.sha256(stmt.encode("utf-8")).hexdigest()
            exists = conn.execute(
                "SELECT id FROM question WHERE content_hash = ?", (h,)
            ).fetchone()
            if exists:
                continue
            cur = conn.execute(
                "INSERT INTO question (domain_id, k_level, difficulty, qtype, statement, explanation, status, content_hash, theta_item)"
                " VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?)",
                (dom[dcode], k, diff, qtype, stmt, expl, h, (diff - 3) * DIFF_LOGIT_SCALE),
            )
            qid = cur.lastrowid
            for j, (otext, ok) in enumerate(options):
                conn.execute(
                    "INSERT INTO answer_option (question_id, label, is_correct, sort_order)"
                    " VALUES (?, ?, ?, ?)",
                    (qid, otext, 1 if ok else 0, j),
                )
        # Utilisateur par defaut (outil local mono-utilisateur ; multi-utilisateur = extensible)
        u = conn.execute("SELECT id FROM app_user WHERE id = 1").fetchone()
        if u is None:
            conn.execute(
                "INSERT INTO app_user (id, username, role, locale, target_score, second_order)"
                " VALUES (1, 'apprenant', 'learner', 'fr', ?, ?)",
                (TARGET_DEFAULT, 1 if SECOND_ORDER_DEFAULT else 0),
            )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Moteurs                                                                     #
# --------------------------------------------------------------------------- #

def compute_quotas(domains, count):
    """Repartit `count` questions selon les ponderations (methode du plus grand reste)."""
    raw = [(d["id"], d["weight"] * count) for d in domains]
    quotas = {did: int(math.floor(val)) for did, val in raw}
    assigned = sum(quotas.values())
    remainder = count - assigned
    fracs = sorted(((val - math.floor(val), did) for did, val in raw), reverse=True)
    idx = 0
    while remainder > 0 and fracs:
        _, did = fracs[idx % len(fracs)]
        quotas[did] += 1
        remainder -= 1
        idx += 1
    return quotas


# Bandes de difficulte pour la generation d'examens par niveau.
LEVEL_BANDS = {
    "moyen": {2, 3},
    "difficile": {3, 4},
    "tres_difficile": {4, 5},
}
LEVEL_LABEL = {
    "moyen": "Moyen",
    "difficile": "Difficile",
    "tres_difficile": "Tres difficile",
}

# 12 examens blancs reproductibles, classes par niveau (seed deterministe).
EXAM_PRESETS = [
    {"id": 1, "level": "moyen"},
    {"id": 2, "level": "moyen"},
    {"id": 3, "level": "moyen"},
    {"id": 4, "level": "moyen"},
    {"id": 5, "level": "difficile"},
    {"id": 6, "level": "difficile"},
    {"id": 7, "level": "difficile"},
    {"id": 8, "level": "difficile"},
    {"id": 9, "level": "tres_difficile"},
    {"id": 10, "level": "tres_difficile"},
    {"id": 11, "level": "tres_difficile"},
    {"id": 12, "level": "tres_difficile"},
]


def preset_info(p):
    return {
        "id": p["id"],
        "level": p["level"],
        "level_label": LEVEL_LABEL[p["level"]],
        "name": "Examen blanc %d" % p["id"],
        "seed": 4100 + p["id"],
    }


def generate_exam(conn, user_id, mode="mock", level=None, seed=None):
    """Genere un examen respectant STRICTEMENT la ponderation des domaines.
    Si `level` (moyen/difficile/tres_difficile) est fourni, la difficulte est
    biaisee vers la bande correspondante, avec repli sur les autres difficultes
    du meme domaine si necessaire (la ponderation reste toujours exacte).
    Un `seed` fixe rend l'examen reproductible (examens blancs presets)."""
    rng = random.Random(seed) if seed is not None else random
    cert = conn.execute("SELECT * FROM certification WHERE code = ?", (CERT_CODE,)).fetchone()
    count = cert["question_count"]
    domains = conn.execute(
        "SELECT * FROM domain WHERE certification_id = ? ORDER BY sort_order", (cert["id"],)
    ).fetchall()
    quotas = compute_quotas(domains, count)
    band = LEVEL_BANDS.get(level) if level else None

    chosen = []
    used = set()
    for d in domains:
        rows = conn.execute(
            "SELECT id, difficulty FROM question WHERE domain_id = ? AND status = 'published'",
            (d["id"],),
        ).fetchall()
        if band is not None:
            in_band = [r["id"] for r in rows if r["difficulty"] in band]
            out_band = [r["id"] for r in rows if r["difficulty"] not in band]
            rng.shuffle(in_band)
            rng.shuffle(out_band)
            ordered = in_band + out_band          # priorite a la bande, repli ensuite
        elif mode == "intensive":
            ordered = [r["id"] for r in sorted(rows, key=lambda r: (-r["difficulty"], rng.random()))]
        else:
            ordered = [r["id"] for r in rows]
            rng.shuffle(ordered)
        take = min(quotas[d["id"]], len(ordered))
        for qid in ordered[:take]:
            chosen.append(qid)
            used.add(qid)

    # Complement global si un domaine etait sous-fourni (robustesse).
    if len(chosen) < count:
        pool = [r["id"] for r in conn.execute(
            "SELECT id FROM question WHERE status = 'published'"
        ) if r["id"] not in used]
        rng.shuffle(pool)
        for qid in pool:
            if len(chosen) >= count:
                break
            chosen.append(qid)
            used.add(qid)

    rng.shuffle(chosen)
    session_id = persist_exam_session(conn, user_id, chosen, level if level else mode)
    return session_id, chosen


def persist_exam_session(conn, user_id, qids, mode):
    """Cree une session d'examen et y rattache les questions dans l'ordre donne."""
    cur = conn.execute(
        "INSERT INTO exam_session (user_id, mode, status) VALUES (?, ?, 'in_progress')",
        (user_id, mode),
    )
    session_id = cur.lastrowid
    for pos, qid in enumerate(qids):
        conn.execute(
            "INSERT INTO exam_session_question (session_id, question_id, position)"
            " VALUES (?, ?, ?)",
            (session_id, qid, pos),
        )
    conn.commit()
    return session_id


# Graine maitre par niveau : rend les 12 examens blancs reproductibles.
PRESET_BAND_SEED = {"moyen": 70001, "difficile": 70002, "tres_difficile": 70003}


def build_band_exams(conn, level, n_exams=4):
    """Construit DE FAÇON DETERMINISTE les n examens d'un meme niveau en se
    partageant les questions (distribution « par donne ») afin de MINIMISER le
    recouvrement entre examens, tout en respectant exactement la ponderation par
    domaine. Si le vivier en-bande d'un domaine est insuffisant, on complete avec
    les autres difficultes du meme domaine (ponderation toujours exacte)."""
    cert = conn.execute("SELECT * FROM certification WHERE code = ?", (CERT_CODE,)).fetchone()
    count = cert["question_count"]
    domains = conn.execute(
        "SELECT * FROM domain WHERE certification_id = ? ORDER BY sort_order", (cert["id"],)
    ).fetchall()
    quotas = compute_quotas(domains, count)
    band = LEVEL_BANDS[level]
    base = PRESET_BAND_SEED[level]
    exams = [[] for _ in range(n_exams)]
    for di, d in enumerate(domains):
        rows = conn.execute(
            "SELECT id, difficulty FROM question WHERE domain_id = ? AND status = 'published'",
            (d["id"],),
        ).fetchall()
        in_band = [r["id"] for r in rows if r["difficulty"] in band]
        out_band = [r["id"] for r in rows if r["difficulty"] not in band]
        rng = random.Random(base * 1000 + di)
        rng.shuffle(in_band)
        rng.shuffle(out_band)
        seq = in_band + out_band            # priorite a la bande, repli ensuite
        q = quotas[d["id"]]
        need = q * n_exams
        # On complete si le domaine a moins de questions que necessaire (rare).
        while len(seq) < need:
            extra = in_band + out_band
            rng.shuffle(extra)
            seq = seq + extra
        # Distribution en alternance : on repartit d'abord les questions en-bande
        # sur TOUS les examens, puis le repli — chaque examen recoit exactement q
        # questions du domaine, et la difficulte est equilibree entre examens.
        for k in range(need):
            exams[k % n_exams].append(seq[k])
    for e in range(n_exams):
        random.Random(base + 7 * e).shuffle(exams[e])   # ordre des questions, deterministe
    return exams


def serialize_question(conn, qid, include_correct=False):
    q = conn.execute("SELECT * FROM question WHERE id = ?", (qid,)).fetchone()
    d = conn.execute("SELECT code FROM domain WHERE id = ?", (q["domain_id"],)).fetchone()
    opts = conn.execute(
        "SELECT * FROM answer_option WHERE question_id = ? ORDER BY sort_order", (qid,)
    ).fetchall()
    data = {
        "id": q["id"],
        "domain": d["code"],
        "k_level": q["k_level"],
        "difficulty": q["difficulty"],
        "qtype": q["qtype"],
        "statement": q["statement"],
        "options": [{"id": o["id"], "label": o["label"]} for o in opts],
    }
    if include_correct:
        data["explanation"] = q["explanation"]
        data["correct_option_ids"] = [o["id"] for o in opts if o["is_correct"]]
    return data


def update_mastery(conn, user_id, domain_id, is_correct):
    row = conn.execute(
        "SELECT score, attempts FROM mastery WHERE user_id = ? AND domain_id = ?",
        (user_id, domain_id),
    ).fetchone()
    alpha = 0.2
    if row is None:
        score = 1.0 if is_correct else 0.0
        conn.execute(
            "INSERT INTO mastery (user_id, domain_id, score, attempts) VALUES (?, ?, ?, 1)",
            (user_id, domain_id, score),
        )
    else:
        new = row["score"] * (1 - alpha) + (1.0 if is_correct else 0.0) * alpha
        conn.execute(
            "UPDATE mastery SET score = ?, attempts = attempts + 1"
            " WHERE user_id = ? AND domain_id = ?",
            (new, user_id, domain_id),
        )


def sm2_review(conn, user_id, qid, quality):
    """Met a jour une carte de revision espacee (SM-2 simplifie). quality 0..5."""
    row = conn.execute(
        "SELECT * FROM sr_card WHERE user_id = ? AND question_id = ?", (user_id, qid)
    ).fetchone()
    ef = row["ease_factor"] if row else 2.5
    reps = row["repetitions"] if row else 0
    interval = row["interval_days"] if row else 0
    if quality < 3:
        reps = 0
        interval = 1
    else:
        reps += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = int(round(interval * ef))
        ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    due = (date.today() + timedelta(days=interval)).isoformat()
    if row:
        conn.execute(
            "UPDATE sr_card SET ease_factor = ?, interval_days = ?, repetitions = ?, due_date = ?"
            " WHERE id = ?",
            (ef, interval, reps, due, row["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO sr_card (user_id, question_id, ease_factor, interval_days, repetitions, due_date)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, qid, ef, interval, reps, due),
        )


def _logistic(x):
    if x <= -60:
        return 0.0
    if x >= 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def second_order_update_item(conn, user_id, qid, is_correct):
    """Mise a jour MUTUELLE aptitude <-> difficulte (Elo leger sur echelle logit).
    Le systeme re-modele ses propres items a la lumiere des reponses : succes =>
    aptitude up / difficulte down, et inversement. La difficulte EDITORIALE
    (1..5, qui pilote les bandes et le recouvrement nul) reste INCHANGEE ; seule
    la difficulte LATENTE observee evolue (reporting + facteur de confiance)."""
    u = conn.execute("SELECT theta_ability FROM app_user WHERE id = ?", (user_id,)).fetchone()
    q = conn.execute("SELECT theta_item FROM question WHERE id = ?", (qid,)).fetchone()
    if u is None or q is None:
        return
    ability = u["theta_ability"] if u["theta_ability"] is not None else 0.0
    diff = q["theta_item"] if q["theta_item"] is not None else 0.0
    p = _logistic(ability - diff)            # probabilite attendue de reussite
    y = 1.0 if is_correct else 0.0
    delta = ELO_K * (y - p)                   # gain amorti
    ability = max(-4.0, min(4.0, ability + delta))
    diff = max(-4.0, min(4.0, diff - delta))
    conn.execute("UPDATE app_user SET theta_ability = ? WHERE id = ?", (ability, user_id))
    conn.execute("UPDATE question SET theta_item = ? WHERE id = ?", (diff, qid))


def log_confidence(conn, user_id, qid, domain_id, context, predicted, is_correct):
    """Journalise une prediction de confiance (probabilite de reussite) et son
    resultat reel : matiere premiere de la boucle metacognitive."""
    predicted = max(0.0, min(1.0, float(predicted)))
    conn.execute(
        "INSERT INTO confidence_log (user_id, question_id, domain_id, context, predicted, is_correct)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, qid, domain_id, context, predicted, 1 if is_correct else 0),
    )


def compute_brier_trend(conn, user_id, max_buckets=8, min_bucket=5):
    """Tendance temporelle du score de Brier : decoupe les predictions de
    confiance par ordre chronologique en tranches successives et calcule le
    Brier de chacune (plus bas = mieux calibre). Renvoie aussi un verdict
    (amelioration / degradation / stable) en comparant la 1re et la 2de moitie."""
    rows = conn.execute(
        "SELECT predicted, is_correct FROM confidence_log WHERE user_id = ? ORDER BY created_at, id",
        (user_id,),
    ).fetchall()
    n = len(rows)
    if n < 2 * min_bucket:
        return {"available": False, "n": n, "buckets": [], "direction": None}

    def brier(seq):
        return sum((r["predicted"] - r["is_correct"]) ** 2 for r in seq) / len(seq)

    nb = min(max_buckets, max(2, n // min_bucket))
    base, rem, idx, buckets = n // nb, n % nb, 0, []
    for k in range(nb):
        size = base + (1 if k < rem else 0)
        chunk = rows[idx:idx + size]
        idx += size
        buckets.append({"i": k + 1, "n": len(chunk), "brier": round(brier(chunk), 4)})
    half = n // 2
    bf, bs = brier(rows[:half]), brier(rows[half:])
    delta = bs - bf                       # negatif = le Brier baisse = amelioration
    direction = "amelioration" if delta < -0.02 else ("degradation" if delta > 0.02 else "stable")
    return {
        "available": True, "n": n,
        "buckets": buckets,
        "first_half_brier": round(bf, 4),
        "second_half_brier": round(bs, 4),
        "delta": round(delta, 4),
        "direction": direction,
    }


def compute_calibration(conn, user_id):
    """Calibration metacognitive : compare confiance predite et reussite reelle.
    Renvoie Brier, ecart de calibration (ECE), biais signe (sur/sous-confiance),
    courbe de fiabilite par tranches, detail par domaine, et un FACTEUR DE
    CALIBRATION (in [CALIB_FLOOR, 1]) qui n'influe qu'au-dela de CALIB_MIN_RECORDS."""
    rows = conn.execute(
        "SELECT c.predicted AS predicted, c.is_correct AS is_correct, d.code AS dcode "
        "FROM confidence_log c JOIN domain d ON c.domain_id = d.id WHERE c.user_id = ?",
        (user_id,),
    ).fetchall()
    n = len(rows)
    if n == 0:
        return {"available": False, "n": 0, "calibration_factor": 1.0, "applies": False}
    brier = sum((r["predicted"] - r["is_correct"]) ** 2 for r in rows) / n
    mean_pred = sum(r["predicted"] for r in rows) / n
    mean_acc = sum(r["is_correct"] for r in rows) / n
    edges = [(0.0, 0.40, "<40 %"), (0.40, 0.60, "~50 %"),
             (0.60, 0.85, "~75 %"), (0.85, 1.01, "~95 %")]
    ece = 0.0
    bins = []
    for lo, hi, lab in edges:
        sub = [r for r in rows if lo <= r["predicted"] < hi]
        if sub:
            p = sum(x["predicted"] for x in sub) / len(sub)
            a = sum(x["is_correct"] for x in sub) / len(sub)
            ece += (len(sub) / n) * abs(p - a)
            bins.append({"label": lab, "n": len(sub),
                         "predicted": round(p, 4), "actual": round(a, 4)})
        else:
            bins.append({"label": lab, "n": 0, "predicted": None, "actual": None})
    per = {}
    for r in rows:
        agg = per.setdefault(r["dcode"], {"n": 0, "pred": 0.0, "acc": 0.0})
        agg["n"] += 1
        agg["pred"] += r["predicted"]
        agg["acc"] += r["is_correct"]
    per_domain = []
    for k, v in sorted(per.items()):
        mp, ma = v["pred"] / v["n"], v["acc"] / v["n"]
        per_domain.append({"domain": k, "n": v["n"], "predicted": round(mp, 4),
                           "actual": round(ma, 4), "gap": round(mp - ma, 4)})
    applies = n >= CALIB_MIN_RECORDS
    factor = max(CALIB_FLOOR, 1.0 - ece) if applies else 1.0
    return {
        "available": True, "n": n,
        "brier": round(brier, 4),
        "mean_predicted": round(mean_pred, 4),
        "mean_actual": round(mean_acc, 4),
        "gap": round(mean_pred - mean_acc, 4),
        "ece": round(ece, 4),
        "calibration_factor": round(factor, 4),
        "applies": applies,
        "min_records": CALIB_MIN_RECORDS,
        "bins": bins,
        "per_domain": per_domain,
        "trend": compute_brier_trend(conn, user_id),
    }


def grade_answers(conn, user_id, answers, context="exam"):
    """answers : liste de {question_id, selected_option_ids:[...]}. Retourne le detail."""
    review = []
    by_domain = {}
    correct_count = 0
    for ans in answers:
        qid = ans.get("question_id")
        selected = set(ans.get("selected_option_ids") or [])
        q = conn.execute("SELECT * FROM question WHERE id = ?", (qid,)).fetchone()
        if not q:
            continue
        opts = conn.execute(
            "SELECT id, is_correct FROM answer_option WHERE question_id = ?", (qid,)
        ).fetchall()
        correct_ids = set(o["id"] for o in opts if o["is_correct"])
        is_correct = (selected == correct_ids) and len(selected) > 0
        if is_correct:
            correct_count += 1
        dcode = conn.execute("SELECT code FROM domain WHERE id = ?", (q["domain_id"],)).fetchone()["code"]
        agg = by_domain.setdefault(dcode, {"correct": 0, "total": 0})
        agg["total"] += 1
        if is_correct:
            agg["correct"] += 1
        # Journalisation + maitrise + revision espacee
        conn.execute(
            "INSERT INTO attempt_log (user_id, question_id, domain_id, is_correct, context)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, qid, q["domain_id"], 1 if is_correct else 0, context),
        )
        update_mastery(conn, user_id, q["domain_id"], is_correct)
        sm2_review(conn, user_id, qid, 5 if is_correct else 2)
        review.append({
            "question_id": qid,
            "is_correct": is_correct,
            "selected_option_ids": sorted(selected),
            "correct_option_ids": sorted(correct_ids),
            "explanation": q["explanation"],
        })
    total = len(review)
    score = (correct_count / total) if total else 0.0
    conn.commit()
    return {
        "score": round(score, 4),
        "correct": correct_count,
        "total": total,
        "by_domain": [
            {"domain": k, "correct": v["correct"], "total": v["total"],
             "rate": round(v["correct"] / v["total"], 4) if v["total"] else 0.0}
            for k, v in sorted(by_domain.items())
        ],
        "review": review,
    }


def compute_readiness(conn, user_id, second_order=False):
    cert = conn.execute("SELECT * FROM certification WHERE code = ?", (CERT_CODE,)).fetchone()
    domains = conn.execute(
        "SELECT * FROM domain WHERE certification_id = ? ORDER BY sort_order", (cert["id"],)
    ).fetchall()
    mastery_rows = {r["domain_id"]: r for r in conn.execute(
        "SELECT * FROM mastery WHERE user_id = ?", (user_id,)
    )}
    per_domain = []
    weighted = 0.0
    weak = []
    for d in domains:
        m = mastery_rows.get(d["id"])
        mscore = m["score"] if m else 0.0
        weighted += mscore * d["weight"]
        per_domain.append({
            "code": d["code"], "label": d["label"],
            "weight": round(d["weight"], 4),
            "mastery": round(mscore, 4),
            "attempts": m["attempts"] if m else 0,
        })
        if mscore < DOMAIN_FLOOR:
            weak.append(d["code"])
    total_attempts = conn.execute(
        "SELECT COUNT(*) c FROM attempt_log WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    data_confidence = min(1.0, total_attempts / DATA_CONFIDENCE_THRESHOLD)
    readiness_raw = weighted * data_confidence
    # Second ordre : la confiance de l'estimateur depend aussi de la qualite de
    # calibration de l'apprenant (amortie, plancher CALIB_FLOOR). La preparation
    # BRUTE est toujours conservee et exposee a cote.
    calibration_factor = 1.0
    if second_order:
        calibration_factor = compute_calibration(conn, user_id)["calibration_factor"]
    readiness = readiness_raw * calibration_factor
    return {
        "readiness": round(readiness, 4),
        "readiness_raw": round(readiness_raw, 4),
        "raw_mastery": round(weighted, 4),
        "confidence": round(data_confidence, 4),
        "calibration_factor": round(calibration_factor, 4),
        "second_order": bool(second_order),
        "total_attempts": total_attempts,
        "per_domain": per_domain,
        "weak_domains": weak,
    }


def build_recommendations(readiness, target):
    recs = []
    weak = readiness["weak_domains"]
    if readiness["total_attempts"] < 20:
        recs.append("Commencez par quelques sessions d'entrainement pour fiabiliser l'estimation de preparation.")
    for code in weak:
        recs.append("Renforcez le domaine " + code + " (maitrise sous le seuil de 65 %).")
    if readiness["readiness"] >= target and not weak:
        recs.append("Objectif atteint : vous etes pret. Enchainez un examen blanc en conditions reelles pour confirmer.")
    elif not weak and readiness["readiness"] < target:
        recs.append("Vous etes au-dessus du seuil de passage sur tous les domaines : poussez vers votre cible avec le mode Expert intensif.")
    if not recs:
        recs.append("Poursuivez l'entrainement regulier et planifiez un examen blanc.")
    return recs


def get_user(conn, user_id=1):
    return conn.execute("SELECT * FROM app_user WHERE id = ?", (user_id,)).fetchone()


# --------------------------------------------------------------------------- #
# Interface (SPA embarquee)                                                   #
# --------------------------------------------------------------------------- #

HTML_PAGE = """<!DOCTYPE html>
<html lang='fr'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>DOF-PREP — Preparation DevOps Foundation</title>
<style>
  :root{
    --paper:#f6f3ec; --ink:#1f2a30; --muted:#5c6b73; --line:#ddd6c8;
    --teal:#0f6e6e; --teal-dark:#0a4f4f; --amber:#c8851f; --amber-soft:#f0e2c4;
    --green:#2f7d4f; --red:#b1442f; --card:#fffdf8;
    --shadow:0 1px 2px rgba(31,42,48,.06),0 8px 24px rgba(31,42,48,.06);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);
    font-family:'Iowan Old Style','Palatino Linotype',Palatino,'Book Antiqua',Georgia,serif;
    line-height:1.5;}
  .sans{font-family:'Avenir Next','Segoe UI',Helvetica,Arial,sans-serif;}
  header{background:var(--teal-dark);color:#f6f3ec;padding:14px 22px;
    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
  header .brand{font-size:20px;letter-spacing:.5px;font-weight:600;}
  header .brand small{display:block;font-size:11px;opacity:.8;letter-spacing:1px;
    font-family:'Avenir Next','Segoe UI',sans-serif;text-transform:uppercase;}
  nav{display:flex;gap:6px;flex-wrap:wrap;}
  nav button{font-family:'Avenir Next','Segoe UI',sans-serif;font-size:13px;
    background:transparent;color:#e8e1d2;border:1px solid rgba(255,255,255,.2);
    padding:8px 14px;border-radius:999px;cursor:pointer;transition:.15s;}
  nav button:hover{background:rgba(255,255,255,.12);}
  nav button.active{background:var(--amber);color:#2a1c05;border-color:var(--amber);font-weight:600;}
  main{max-width:980px;margin:0 auto;padding:26px 18px 60px;}
  h1{font-size:30px;margin:.2em 0 .1em;font-weight:600;}
  h2{font-size:21px;margin:1.4em 0 .5em;border-bottom:2px solid var(--line);padding-bottom:6px;}
  .lead{color:var(--muted);font-size:15px;margin:.2em 0 1.2em;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;
    padding:20px 22px;box-shadow:var(--shadow);margin-bottom:18px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
  @media(max-width:720px){.grid2{grid-template-columns:1fr}}
  button.primary{font-family:'Avenir Next','Segoe UI',sans-serif;background:var(--teal);
    color:#fff;border:none;padding:11px 20px;border-radius:8px;font-size:14px;
    cursor:pointer;font-weight:600;transition:.15s;}
  button.primary:hover{background:var(--teal-dark);}
  button.ghost{font-family:'Avenir Next','Segoe UI',sans-serif;background:transparent;
    color:var(--teal);border:1px solid var(--teal);padding:9px 16px;border-radius:8px;
    font-size:13px;cursor:pointer;}
  button:disabled{opacity:.45;cursor:not-allowed;}
  .gauge-wrap{display:flex;align-items:center;gap:22px;flex-wrap:wrap;}
  .ring{position:relative;width:150px;height:150px;flex:0 0 auto;}
  .ring svg{transform:rotate(-90deg);}
  .ring .val{position:absolute;inset:0;display:flex;flex-direction:column;
    align-items:center;justify-content:center;}
  .ring .val b{font-size:32px;}
  .ring .val span{font-size:11px;color:var(--muted);
    font-family:'Avenir Next','Segoe UI',sans-serif;text-transform:uppercase;letter-spacing:1px;}
  .badge{display:inline-block;font-family:'Avenir Next','Segoe UI',sans-serif;font-size:12px;
    font-weight:700;padding:5px 12px;border-radius:999px;letter-spacing:.5px;}
  .badge.ok{background:#dff0e4;color:var(--green);}
  .badge.no{background:#f6e2dd;color:var(--red);}
  .slider-block{margin-top:6px;}
  .slider-head{display:flex;justify-content:space-between;align-items:baseline;
    font-family:'Avenir Next','Segoe UI',sans-serif;font-size:13px;color:var(--muted);}
  .slider-head .cur{font-size:26px;color:var(--amber);font-weight:700;
    font-family:'Iowan Old Style',Georgia,serif;}
  input[type=range]{width:100%;accent-color:var(--amber);height:6px;margin:10px 0 2px;}
  .ticks{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);
    font-family:'Avenir Next','Segoe UI',sans-serif;}
  .bar-row{display:flex;align-items:center;gap:10px;margin:9px 0;
    font-family:'Avenir Next','Segoe UI',sans-serif;font-size:13px;}
  .bar-row .code{flex:0 0 64px;color:var(--muted);font-weight:600;}
  .bar-row .track{flex:1;background:#eee7d8;height:14px;border-radius:7px;overflow:hidden;position:relative;}
  .bar-row .fill{height:100%;background:var(--teal);border-radius:7px;}
  .bar-row .fill.weak{background:var(--amber);}
  .bar-row .pct{flex:0 0 46px;text-align:right;}
  ul.recs{list-style:none;padding:0;margin:0;font-family:'Avenir Next','Segoe UI',sans-serif;font-size:14px;}
  ul.recs li{padding:9px 12px;background:var(--amber-soft);border-radius:8px;margin-bottom:8px;}
  .q-meta{font-family:'Avenir Next','Segoe UI',sans-serif;font-size:12px;color:var(--muted);
    text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}
  .q-text{font-size:18px;margin-bottom:14px;}
  .opt{display:block;border:1px solid var(--line);border-radius:9px;padding:12px 14px;
    margin-bottom:9px;cursor:pointer;background:#fff;transition:.12s;
    font-family:'Avenir Next','Segoe UI',sans-serif;font-size:14px;}
  .opt:hover{border-color:var(--teal);}
  .opt.sel{border-color:var(--teal);background:#e9f3f3;}
  .opt.correct{border-color:var(--green);background:#e4f2e9;}
  .opt.wrong{border-color:var(--red);background:#f7e6e2;}
  .opt input{margin-right:10px;}
  .timer{font-family:'Avenir Next','Segoe UI',sans-serif;font-weight:700;font-size:16px;
    background:var(--ink);color:#fff;padding:6px 14px;border-radius:8px;}
  .timer.warn{background:var(--red);}
  .exam-top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px;}
  .navgrid{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0;}
  .navgrid button{width:34px;height:34px;border-radius:7px;border:1px solid var(--line);
    background:#fff;cursor:pointer;font-family:'Avenir Next','Segoe UI',sans-serif;font-size:12px;}
  .navgrid button.answered{background:var(--teal);color:#fff;border-color:var(--teal);}
  .navgrid button.current{outline:3px solid var(--amber);}
  table.res{width:100%;border-collapse:collapse;font-family:'Avenir Next','Segoe UI',sans-serif;font-size:13px;}
  table.res th,table.res td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);}
  .feedback{font-family:'Avenir Next','Segoe UI',sans-serif;font-size:13px;padding:10px 12px;
    border-radius:8px;margin-top:6px;}
  .feedback.ok{background:#e4f2e9;color:#1d5635;}
  .feedback.no{background:#f7e6e2;color:#7a2a1c;}
  select{font-family:'Avenir Next','Segoe UI',sans-serif;font-size:14px;padding:8px 10px;
    border:1px solid var(--line);border-radius:8px;background:#fff;}
  .pill{font-family:'Avenir Next','Segoe UI',sans-serif;font-size:11px;color:var(--muted);}
  .center{text-align:center;}
  .scorebig{font-size:46px;font-weight:700;}
  .note{font-size:12px;color:var(--muted);font-family:'Avenir Next','Segoe UI',sans-serif;margin-top:14px;}
</style>
</head>
<body>
<header>
  <div class='brand'>DOF&#8209;PREP <small>Preparation DevOps Foundation</small></div>
  <nav id='nav'></nav>
</header>
<main id='view'></main>

<script>
const API = '/api/v1';
let STATE = {user:null, cert:null, domains:[]};
let EXAM = null;

function el(html){const t=document.createElement('template');t.innerHTML=html.trim();return t.content.firstChild;}
function pct(x){return Math.round((x||0)*100)+'%';}
async function api(method, path, body){
  const opt={method, headers:{'Content-Type':'application/json'}};
  if(body!==undefined) opt.body=JSON.stringify(body);
  const r=await fetch(API+path, opt);
  if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error((e.error&&e.error.message)||('Erreur '+r.status));}
  return r.json();
}

let CURRENT='dashboard';
function currentViews(){
  const base=[['dashboard','Tableau de bord'],['exam','Examen blanc'],['training','Entrainement'],['review','Revision']];
  if(STATE.user && STATE.user.second_order) base.push(['calibration','Calibration']);
  return base;
}
function renderNav(){
  const n=document.getElementById('nav');n.innerHTML='';
  currentViews().forEach(([k,label])=>{
    const b=el(`<button class='${k===CURRENT?'active':''}'>${label}</button>`);
    b.onclick=()=>{CURRENT=k;route();};
    n.appendChild(b);
  });
}
function route(){
  if(CURRENT==='calibration' && !(STATE.user && STATE.user.second_order)) CURRENT='dashboard';
  renderNav();
  if(CURRENT==='dashboard') viewDashboard();
  else if(CURRENT==='exam') viewExamStart();
  else if(CURRENT==='training') viewTraining();
  else if(CURRENT==='review') viewReview();
  else if(CURRENT==='calibration') viewCalibration();
}

/* ---------------------------- Tableau de bord --------------------------- */
async function viewDashboard(){
  const v=document.getElementById('view');
  v.innerHTML="<h1>Tableau de bord</h1><p class='lead'>Chargement...</p>";
  const d=await api('GET','/dashboard');
  const target=d.user.target_score;
  const ready=d.readiness.readiness;
  const ring=gaugeSVG(ready, target);
  v.innerHTML='';
  v.appendChild(el("<h1>Tableau de bord</h1>"));
  v.appendChild(el(`<p class='lead'>${STATE.cert.label}</p>`));

  const top=el("<div class='card'></div>");
  const wrap=el("<div class='gauge-wrap'></div>");
  const ringEl=el("<div class='ring'></div>");ringEl.innerHTML=ring+`<div class='val'><b>${pct(ready)}</b><span>preparation</span></div>`;
  wrap.appendChild(ringEl);

  const right=el("<div style='flex:1;min-width:240px'></div>");
  const badge = d.ready_for_exam
     ? "<span class='badge ok'>&#10003; Pret pour l'examen</span>"
     : "<span class='badge no'>Pas encore pret</span>";
  right.appendChild(el(`<div style='margin-bottom:10px'>${badge}</div>`));
  right.appendChild(el(`<div class='pill'>Seuil officiel de reussite : ${pct(STATE.cert.pass_threshold)} &nbsp;&middot;&nbsp; Confiance des donnees : ${pct(d.readiness.confidence)} (${d.readiness.total_attempts} reponses)</div>`));
  if(d.user.second_order){
    right.appendChild(el(`<div class='pill'>Preparation brute : ${pct(d.readiness.readiness_raw)} &nbsp;&middot;&nbsp; facteur de calibration : ${pct(d.readiness.calibration_factor)} &nbsp;&middot;&nbsp; preparation calibree : ${pct(d.readiness.readiness)}</div>`));
  }
  const soWrap=el("<div style='margin:12px 0 2px'></div>");
  soWrap.innerHTML="<label style='display:inline-flex;align-items:center;gap:8px;font-family:Avenir Next,Segoe UI,sans-serif;font-size:14px;cursor:pointer'><input type='checkbox' id='so'"+(d.user.second_order?" checked":"")+"> <b>Couche de second ordre</b> (calibration metacognitive)</label>";
  right.appendChild(soWrap);
  right.appendChild(el("<div class='note' style='margin-top:2px'>"+(d.user.second_order
     ? "Active : l'anneau ci-dessus est la preparation <em>calibree</em> (score brut conserve a cote). Une invite de confiance apparait pendant examens et entrainement ; voir l'onglet Calibration."
     : "Optionnel : invite de confiance + tableau de bord de calibration, et auto-calibration de l'instrument de mesure. Le seuil officiel de 65 % reste inchange.")+"</div>"));

  // Curseur de cible
  const sb=el("<div class='slider-block'></div>");
  sb.innerHTML=`<div class='slider-head'><span>Cible de reussite</span><span class='cur' id='tgtval'>${pct(target)}</span></div>
    <input type='range' id='tgt' min='65' max='90' step='1' value='${Math.round(target*100)}'>
    <div class='ticks'><span>65 % &middot; seuil officiel</span><span>90 % &middot; confiance</span></div>`;
  right.appendChild(sb);
  wrap.appendChild(right);
  top.appendChild(wrap);
  v.appendChild(top);

  // Domaines
  const dom=el("<div class='card'></div>");
  dom.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Maitrise par domaine</h2>"));
  d.readiness.per_domain.forEach(p=>{
    const weak=p.mastery<0.65?'weak':'';
    dom.appendChild(el(`<div class='bar-row'><span class='code' title='${p.label}'>${p.code}</span>
      <span class='track'><span class='fill ${weak}' style='width:${Math.round(p.mastery*100)}%'></span></span>
      <span class='pct'>${pct(p.mastery)}</span></div>`));
  });
  v.appendChild(dom);

  // Recommandations
  const rec=el("<div class='card'></div>");
  rec.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Recommandations</h2>"));
  const ul=el("<ul class='recs'></ul>");
  d.recommendations.forEach(r=>ul.appendChild(el(`<li>${r}</li>`)));
  rec.appendChild(ul);
  const go=el("<button class='primary' style='margin-top:14px'>Demarrer un examen blanc</button>");
  go.onclick=()=>{CURRENT='exam';route();};
  rec.appendChild(go);
  v.appendChild(rec);

  // Slider behaviour
  const slider=document.getElementById('tgt');
  const label=document.getElementById('tgtval');
  slider.addEventListener('input',()=>{label.textContent=slider.value+' %';});
  slider.addEventListener('change',async()=>{
    const val=parseInt(slider.value,10)/100;
    try{
      const res=await api('PATCH','/me/preferences',{target_score:val});
      STATE.user.target_score=res.target_score;
      viewDashboard();
    }catch(e){alert(e.message);}
  });
  const so=document.getElementById('so');
  if(so){
    so.addEventListener('change',async()=>{
      try{
        const res=await api('PATCH','/me/preferences',{second_order:so.checked});
        STATE.user.second_order=res.second_order;
        route();
      }catch(e){alert(e.message);}
    });
  }
}

function gaugeSVG(value, target){
  const r=64, c=2*Math.PI*r;
  const off=c*(1-Math.max(0,Math.min(1,value)));
  const tAng=Math.max(0,Math.min(1,target));
  // position du repere de cible sur l'arc
  const ang=(tAng*360-90)*Math.PI/180;
  const cx=75+r*Math.cos(ang), cy=75+r*Math.sin(ang);
  return `<svg width='150' height='150' viewBox='0 0 150 150'>
    <circle cx='75' cy='75' r='${r}' fill='none' stroke='#eee7d8' stroke-width='13'/>
    <circle cx='75' cy='75' r='${r}' fill='none' stroke='#0f6e6e' stroke-width='13'
       stroke-linecap='round' stroke-dasharray='${c}' stroke-dashoffset='${off}'/>
    <circle cx='${cx}' cy='${cy}' r='6' fill='#c8851f' stroke='#fffdf8' stroke-width='2'/>
  </svg>`;
}

/* ------------------------------- Examen --------------------------------- */
async function viewExamStart(){
  const v=document.getElementById('view');
  v.innerHTML="<h1>Examen blanc</h1>";
  v.appendChild(el(`<p class='lead'>${STATE.cert.question_count} questions &middot; ${STATE.cert.duration_min} minutes &middot; seuil ${pct(STATE.cert.pass_threshold)} &middot; sans penalite &middot; repartition par domaine respectee.</p>`));

  /* Les 12 examens blancs, classes par niveau de difficulte */
  let presets=[];
  try{ const data=await api('GET','/exams/presets'); presets=data.presets||[]; }catch(e){ presets=[]; }
  const groups=[
    ['moyen','Moyen','Difficulte moyenne, proche du niveau reel de certification.'],
    ['difficile','Difficile','Au-dessus du niveau reel : application et analyse.'],
    ['tres_difficile','Tres difficile','Tres au-dessus du reel : analyse, evaluation et synthese (K6-K7).']
  ];
  const wrap=el("<div class='card'></div>");
  wrap.appendChild(el("<h2 style='margin-top:0'>Les 12 examens blancs</h2>"));
  wrap.appendChild(el("<p style='font-family:Avenir Next,Segoe UI,sans-serif;font-size:14px'>Chaque examen est reproductible (meme composition a chaque lancement) et respecte la ponderation officielle des 8 domaines. Ils sont classes par niveau de difficulte.</p>"));
  groups.forEach(g=>{
    const list=presets.filter(p=>p.level===g[0]);
    if(!list.length) return;
    wrap.appendChild(el(`<div style='font-family:Avenir Next,Segoe UI,sans-serif;font-weight:700;margin-top:14px;color:#0f6e6e'>${g[1]}</div>`));
    wrap.appendChild(el(`<div class='note' style='margin-top:2px'>${g[2]}</div>`));
    const row=el("<div style='display:flex;flex-wrap:wrap;gap:8px;margin:8px 0'></div>");
    list.forEach(p=>{
      const btn=el(`<button class='ghost' style='flex:0 0 auto'>${escapeHtml(p.name)}</button>`);
      btn.onclick=()=>startExam({preset_id:p.id, label:p.name+" - "+p.level_label});
      row.appendChild(btn);
    });
    wrap.appendChild(row);
  });
  v.appendChild(wrap);

  /* Examen libre, avec choix du niveau */
  const c=el("<div class='card'></div>");
  c.appendChild(el("<h2 style='margin-top:0'>Examen libre</h2>"));
  c.appendChild(el("<p style='font-family:Avenir Next,Segoe UI,sans-serif;font-size:14px'>Genere un examen a la volee. Choisissez un niveau de difficulte (optionnel) : la repartition par domaine reste garantie. Le minuteur demarre des le lancement ; a 0 l'examen est soumis automatiquement.</p>"));
  const selWrap=el("<div style='margin-bottom:12px'></div>");
  selWrap.appendChild(el("<label class='note' style='margin:0 8px 0 0'>Niveau :</label>"));
  const sel=el("<select id='freelevel' style='font-family:inherit;padding:6px 8px;border-radius:8px;border:1px solid #d8cfbb;background:#fffdf8'><option value=''>Aleatoire (tous niveaux)</option><option value='moyen'>Moyen</option><option value='difficile'>Difficile</option><option value='tres_difficile'>Tres difficile</option></select>");
  selWrap.appendChild(sel);
  c.appendChild(selWrap);
  const b1=el("<button class='primary'>Lancer un examen blanc</button>");
  b1.onclick=()=>{
    const lv=document.getElementById('freelevel').value;
    const lbls={moyen:'Moyen',difficile:'Difficile',tres_difficile:'Tres difficile'};
    startExam({level:lv||null, mode:'mock', label:lv?('Examen libre - '+lbls[lv]):'Examen libre'});
  };
  const b2=el("<button class='ghost' style='margin-left:10px'>Mode Expert intensif</button>");
  b2.onclick=()=>startExam({mode:'intensive', label:'Mode Expert intensif'});
  c.appendChild(b1);c.appendChild(b2);
  c.appendChild(el("<div class='note'>Mode Expert intensif : priorite aux questions les plus difficiles, toutes sections confondues.</div>"));
  v.appendChild(c);
}

async function startExam(opts){
  opts=opts||{};
  const payload={};
  if(opts.preset_id) payload.preset_id=opts.preset_id;
  if(opts.level) payload.level=opts.level;
  if(opts.mode) payload.mode=opts.mode;
  const d=await api('POST','/exams/generate',payload);
  EXAM={session_id:d.session_id, questions:d.questions, answers:{}, confidence:{}, idx:0,
        remaining:d.duration_min*60, mode:d.mode||opts.mode||'mock',
        label:opts.label||d.exam_name||(d.level_label?('Niveau '+d.level_label):'Examen blanc'),
        timer:null};
  renderExam();
  EXAM.timer=setInterval(()=>{
    EXAM.remaining--;
    const t=document.getElementById('timer');
    if(t){t.textContent=fmtTime(EXAM.remaining);t.classList.toggle('warn',EXAM.remaining<=120);}
    if(EXAM.remaining<=0){clearInterval(EXAM.timer);submitExam();}
  },1000);
}

function fmtTime(s){const m=Math.floor(s/60),x=s%60;return (m<10?'0':'')+m+':'+(x<10?'0':'')+x;}

function renderExam(){
  const v=document.getElementById('view');
  const q=EXAM.questions[EXAM.idx];
  v.innerHTML='';
  const top=el("<div class='exam-top'></div>");
  top.appendChild(el(`<div style='font-family:Avenir Next,Segoe UI,sans-serif;font-weight:600'>${EXAM.label?escapeHtml(EXAM.label)+" &middot; ":""}Question ${EXAM.idx+1} / ${EXAM.questions.length}</div>`));
  top.appendChild(el(`<div class='timer' id='timer'>${fmtTime(EXAM.remaining)}</div>`));
  v.appendChild(top);

  const card=el("<div class='card'></div>");
  card.appendChild(el(`<div class='q-meta'>${q.domain} &middot; niveau K${q.k_level} &middot; ${q.qtype==='multiple'?'plusieurs reponses':'une reponse'}</div>`));
  card.appendChild(el(`<div class='q-text'>${escapeHtml(q.statement)}</div>`));
  const multi=q.qtype==='multiple';
  const sel=EXAM.answers[q.id]||[];
  q.options.forEach(o=>{
    const checked=sel.includes(o.id);
    const opt=el(`<label class='opt ${checked?'sel':''}'>
      <input type='${multi?'checkbox':'radio'}' name='q' ${checked?'checked':''}> ${escapeHtml(o.label)}</label>`);
    opt.querySelector('input').onchange=(ev)=>{
      let cur=EXAM.answers[q.id]||[];
      if(multi){
        if(ev.target.checked) cur=[...cur,o.id]; else cur=cur.filter(x=>x!==o.id);
      } else { cur=[o.id]; }
      EXAM.answers[q.id]=cur;
      renderExam();
    };
    card.appendChild(opt);
  });
  if(STATE.user && STATE.user.second_order){
    const choices=(STATE.second && STATE.second.confidence_choices) || [25,50,75,95];
    const conf=EXAM.confidence?EXAM.confidence[q.id]:undefined;
    const cwrap=el("<div style='margin-top:12px;border-top:1px dashed var(--line);padding-top:10px'></div>");
    cwrap.appendChild(el("<div class='q-meta' style='margin-bottom:6px'>Quelle est votre confiance dans cette reponse ?</div>"));
    const row=el("<div style='display:flex;flex-wrap:wrap;gap:8px'></div>");
    choices.forEach(p=>{
      const styl="flex:0 0 auto"+(conf===p?";border-color:var(--teal);color:var(--teal);font-weight:700":"");
      const b=el(`<button class='ghost' style='${styl}'>${p} %</button>`);
      b.onclick=()=>{ if(!EXAM.confidence)EXAM.confidence={}; EXAM.confidence[q.id]=p; renderExam(); };
      row.appendChild(b);
    });
    cwrap.appendChild(row);
    card.appendChild(cwrap);
  }
  v.appendChild(card);

  const nav=el("<div class='navgrid'></div>");
  EXAM.questions.forEach((qq,i)=>{
    const answered=(EXAM.answers[qq.id]||[]).length>0;
    const b=el(`<button class='${answered?'answered':''} ${i===EXAM.idx?'current':''}'>${i+1}</button>`);
    b.onclick=()=>{EXAM.idx=i;renderExam();};
    nav.appendChild(b);
  });
  v.appendChild(nav);

  const ctr=el("<div></div>");
  const prev=el("<button class='ghost'>Precedent</button>");prev.disabled=EXAM.idx===0;prev.onclick=()=>{EXAM.idx--;renderExam();};
  const next=el("<button class='ghost' style='margin-left:8px'>Suivant</button>");next.disabled=EXAM.idx>=EXAM.questions.length-1;next.onclick=()=>{EXAM.idx++;renderExam();};
  const fin=el("<button class='primary' style='margin-left:8px'>Terminer et corriger</button>");fin.onclick=submitExam;
  ctr.appendChild(prev);ctr.appendChild(next);ctr.appendChild(fin);
  v.appendChild(ctr);
}

async function submitExam(){
  if(EXAM.timer) clearInterval(EXAM.timer);
  const answers=EXAM.questions.map(q=>{
    const a={question_id:q.id, selected_option_ids:EXAM.answers[q.id]||[]};
    if(EXAM.confidence && EXAM.confidence[q.id]!==undefined) a.confidence=EXAM.confidence[q.id];
    return a;
  });
  const res=await api('POST','/exams/sessions/'+EXAM.session_id+'/submit',{answers});
  renderResults(res);
}

function renderResults(res){
  const v=document.getElementById('view');
  v.innerHTML="<h1>Resultats de l'examen blanc</h1>";
  const pass=res.passed;
  const c=el("<div class='card center'></div>");
  c.appendChild(el(`<div class='scorebig' style='color:${pass?'#2f7d4f':'#b1442f'}'>${pct(res.score)}</div>`));
  c.appendChild(el(`<div>${res.correct} / ${res.total} &middot; seuil de reussite ${pct(STATE.cert.pass_threshold)}</div>`));
  c.appendChild(el(`<div style='margin-top:10px'>${pass?"<span class='badge ok'>Reussi</span>":"<span class='badge no'>En dessous du seuil</span>"}</div>`));
  if(res.ready_for_exam!==undefined){
    let line=`Cible personnelle : ${pct(res.target_score)} &middot; preparation globale : ${pct(res.readiness)}`;
    if(res.readiness_raw!==undefined && res.calibration && res.calibration.available){
      line+=` &middot; brute ${pct(res.readiness_raw)} &middot; facteur calibration ${pct(res.calibration.calibration_factor)}`;
    }
    c.appendChild(el(`<div style='margin-top:10px' class='pill'>${line}</div>`));
  }
  v.appendChild(c);

  const t=el("<div class='card'></div>");
  t.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Detail par domaine</h2>"));
  const tab=el("<table class='res'><thead><tr><th>Domaine</th><th>Reussite</th><th>Score</th></tr></thead><tbody></tbody></table>");
  const tb=tab.querySelector('tbody');
  res.by_domain.forEach(d=>{
    tb.appendChild(el(`<tr><td>${d.domain}</td><td>${d.correct}/${d.total}</td><td>${pct(d.rate)}</td></tr>`));
  });
  t.appendChild(tab);
  v.appendChild(t);

  const r=el("<div class='card'></div>");
  r.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Correction detaillee</h2>"));
  EXAM.questions.forEach((q,i)=>{
    const rv=res.review.find(x=>x.question_id===q.id)||{};
    const block=el("<div style='margin-bottom:18px'></div>");
    block.appendChild(el(`<div class='q-meta'>${q.domain} &middot; question ${i+1}</div>`));
    block.appendChild(el(`<div style='font-family:Avenir Next,Segoe UI,sans-serif;font-weight:600;margin-bottom:6px'>${escapeHtml(q.statement)}</div>`));
    q.options.forEach(o=>{
      const isCorrect=(rv.correct_option_ids||[]).includes(o.id);
      const isSel=(rv.selected_option_ids||[]).includes(o.id);
      let cls='opt';if(isCorrect)cls+=' correct';else if(isSel)cls+=' wrong';
      block.appendChild(el(`<div class='${cls}'>${isCorrect?'&#10003; ':(isSel?'&#10007; ':'')}${escapeHtml(o.label)}</div>`));
    });
    block.appendChild(el(`<div class='feedback ${rv.is_correct?'ok':'no'}'>${rv.is_correct?'Correct.':'A revoir.'} ${escapeHtml(rv.explanation||'')}</div>`));
    r.appendChild(block);
  });
  v.appendChild(r);

  const back=el("<button class='primary'>Retour au tableau de bord</button>");
  back.onclick=()=>{CURRENT='dashboard';route();};
  v.appendChild(back);
}

/* ----------------------------- Entrainement ----------------------------- */
let TR=null;
async function viewTraining(){
  const v=document.getElementById('view');
  v.innerHTML="<h1>Entrainement cible</h1><p class='lead'>Choisissez un domaine et entrainez-vous avec correction immediate.</p>";
  const c=el("<div class='card'></div>");
  const sel=el("<select id='dom'></select>");
  sel.appendChild(el("<option value=''>Tous les domaines</option>"));
  STATE.domains.forEach(d=>sel.appendChild(el(`<option value='${d.code}'>${d.code} — ${escapeHtml(d.label)}</option>`)));
  c.appendChild(el("<label style='font-family:Avenir Next,Segoe UI,sans-serif;font-size:13px;display:block;margin-bottom:6px'>Domaine</label>"));
  c.appendChild(sel);
  const cnt=el("<select id='cnt' style='margin-left:10px'><option>5</option><option selected>10</option><option>15</option></select>");
  c.appendChild(el("<label style='font-family:Avenir Next,Segoe UI,sans-serif;font-size:13px;display:inline-block;margin:0 6px 0 16px'>Questions</label>"));
  c.appendChild(cnt);
  const go=el("<button class='primary' style='margin-left:14px'>Commencer</button>");
  go.onclick=async()=>{
    const domain=document.getElementById('dom').value;
    const count=parseInt(document.getElementById('cnt').value,10);
    const d=await api('POST','/training/start',{domain:domain||null,count});
    if(!d.questions.length){alert('Aucune question disponible pour ce domaine.');return;}
    TR={questions:d.questions, idx:0, correct:0, answered:false};
    renderTraining();
  };
  c.appendChild(go);
  v.appendChild(c);
}

function renderTraining(){
  const v=document.getElementById('view');
  const q=TR.questions[TR.idx];
  v.innerHTML='';
  v.appendChild(el(`<div style='font-family:Avenir Next,Segoe UI,sans-serif;font-weight:600;margin-bottom:10px'>Entrainement &middot; ${TR.idx+1} / ${TR.questions.length} &middot; score ${TR.correct}/${TR.idx+(TR.answered?1:0)}</div>`));
  const card=el("<div class='card'></div>");
  card.appendChild(el(`<div class='q-meta'>${q.domain} &middot; niveau K${q.k_level} &middot; ${q.qtype==='multiple'?'plusieurs reponses':'une reponse'}</div>`));
  card.appendChild(el(`<div class='q-text'>${escapeHtml(q.statement)}</div>`));
  const multi=q.qtype==='multiple';
  TR.sel=TR.sel||[];
  q.options.forEach(o=>{
    let cls='opt';
    if(TR.answered){
      if((TR.correctIds||[]).includes(o.id))cls+=' correct';
      else if(TR.sel.includes(o.id))cls+=' wrong';
    } else if(TR.sel.includes(o.id)) cls+=' sel';
    const opt=el(`<label class='${cls}'><input type='${multi?'checkbox':'radio'}' name='t' ${TR.sel.includes(o.id)?'checked':''} ${TR.answered?'disabled':''}> ${escapeHtml(o.label)}</label>`);
    if(!TR.answered){
      opt.querySelector('input').onchange=(ev)=>{
        if(multi){if(ev.target.checked)TR.sel=[...TR.sel,o.id];else TR.sel=TR.sel.filter(x=>x!==o.id);}
        else TR.sel=[o.id];
        renderTraining();
      };
    }
    card.appendChild(opt);
  });
  v.appendChild(card);

  if(!TR.answered){
    if(STATE.user && STATE.user.second_order){
      const choices=(STATE.second && STATE.second.confidence_choices) || [25,50,75,95];
      const cwrap=el("<div class='card' style='margin-top:0'></div>");
      cwrap.appendChild(el("<div class='q-meta' style='margin-bottom:6px'>Votre confiance avant validation ?</div>"));
      const row=el("<div style='display:flex;flex-wrap:wrap;gap:8px'></div>");
      choices.forEach(p=>{
        const styl="flex:0 0 auto"+(TR.confidence===p?";border-color:var(--teal);color:var(--teal);font-weight:700":"");
        const b=el(`<button class='ghost' style='${styl}'>${p} %</button>`);
        b.onclick=()=>{TR.confidence=p;renderTraining();};
        row.appendChild(b);
      });
      cwrap.appendChild(row);
      v.appendChild(cwrap);
    }
    const b=el("<button class='primary'>Valider</button>");
    b.disabled=TR.sel.length===0;
    b.onclick=async()=>{
      const payload={question_id:q.id, selected_option_ids:TR.sel};
      if(TR.confidence!==undefined) payload.confidence=TR.confidence;
      const res=await api('POST','/training/answer',payload);
      TR.answered=true;TR.correctIds=res.correct_option_ids;TR.expl=res.explanation;TR.lastOk=res.is_correct;
      if(res.is_correct)TR.correct++;
      renderTraining();
    };
    v.appendChild(b);
  } else {
    v.appendChild(el(`<div class='feedback ${TR.lastOk?'ok':'no'}'>${TR.lastOk?'Correct !':'Pas tout a fait.'} ${escapeHtml(TR.expl||'')}</div>`));
    const more=TR.idx<TR.questions.length-1;
    const b=el(`<button class='primary' style='margin-top:12px'>${more?'Question suivante':'Voir le bilan'}</button>`);
    b.onclick=()=>{
      if(more){TR.idx++;TR.sel=[];TR.answered=false;TR.correctIds=null;TR.confidence=undefined;renderTraining();}
      else{
        v.innerHTML=`<h1>Bilan de l'entrainement</h1><div class='card center'><div class='scorebig'>${pct(TR.correct/TR.questions.length)}</div><div>${TR.correct} / ${TR.questions.length} bonnes reponses</div></div>`;
        const back=el("<button class='primary'>Nouvel entrainement</button>");back.onclick=()=>{CURRENT='training';route();};
        v.appendChild(back);
      }
    };
    v.appendChild(b);
  }
}

/* ------------------------------- Revision -------------------------------- */
async function viewReview(){
  const v=document.getElementById('view');
  v.innerHTML="<h1>Revision espacee</h1><p class='lead'>Cartes a revoir aujourd'hui (algorithme SM-2).</p>";
  const d=await api('GET','/review/due');
  if(!d.questions.length){
    v.appendChild(el("<div class='card'><p style='font-family:Avenir Next,Segoe UI,sans-serif'>Aucune carte a revoir pour l'instant. Repondez a des questions en entrainement ou en examen pour alimenter la file de revision.</p></div>"));
    return;
  }
  TR={questions:d.questions, idx:0, correct:0, answered:false, sel:[], review:true};
  renderTraining();
}

/* ------------------------------- Utils ----------------------------------- */
function escapeHtml(s){return (s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

async function viewCalibration(){
  const v=document.getElementById('view');
  v.innerHTML="<h1>Calibration metacognitive</h1><p class='lead'>Chargement...</p>";
  const d=await api('GET','/calibration');
  v.innerHTML='';
  v.appendChild(el("<h1>Calibration metacognitive</h1>"));
  v.appendChild(el("<p class='lead'>Le systeme observe sa propre observation : il confronte la confiance que vous annoncez a votre reussite reelle.</p>"));
  if(!d.available){
    v.appendChild(el("<div class='card'><p style='font-family:Avenir Next,Segoe UI,sans-serif'>Pas encore de donnees de confiance. Lancez un examen blanc ou un entrainement et indiquez votre confiance a chaque question : votre courbe de calibration apparaitra ici.</p></div>"));
    return;
  }
  const gap=d.gap; let verdict, col;
  if(gap>0.05){verdict="Surconfiance : vous vous surestimez d'environ "+Math.round(gap*100)+" points";col="#b1442f";}
  else if(gap<-0.05){verdict="Sous-confiance : vous vous sous-estimez d'environ "+Math.round(-gap*100)+" points";col="#c8851f";}
  else{verdict="Bonne calibration : confiance predite proche du reel";col="#2f7d4f";}
  const top=el("<div class='card'></div>");
  top.appendChild(el(`<div style='font-family:Avenir Next,Segoe UI,sans-serif;font-weight:700;color:${col};margin-bottom:8px'>${verdict}</div>`));
  top.appendChild(el(`<div class='pill'>Predictions : ${d.n} &nbsp;&middot;&nbsp; confiance moyenne ${pct(d.mean_predicted)} &nbsp;&middot;&nbsp; reussite reelle ${pct(d.mean_actual)}</div>`));
  top.appendChild(el(`<div class='pill'>Score de Brier : ${d.brier.toFixed(3)} (0 = parfait) &nbsp;&middot;&nbsp; erreur de calibration : ${pct(d.ece)}</div>`));
  const applies = d.applies
     ? "Le facteur de calibration <b>"+pct(d.calibration_factor)+"</b> module la preparation affichee."
     : "Au moins "+d.min_records+" predictions sont necessaires avant que la calibration n'influe sur la preparation (actuellement "+d.n+").";
  top.appendChild(el(`<div class='note' style='margin-top:8px'>${applies} Le seuil officiel de 65 % reste inchange ; la preparation brute reste affichee au tableau de bord.</div>`));
  v.appendChild(top);

  const rc=el("<div class='card'></div>");
  rc.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Courbe de fiabilite (predit vs reel)</h2>"));
  let any=false;
  d.bins.forEach(b=>{
    if(!b.n){return;}
    any=true;
    const row=el("<div style='margin:12px 0'></div>");
    row.appendChild(el(`<div class='q-meta' style='margin-bottom:4px'>Confiance annoncee ${b.label} &middot; ${b.n} reponse(s)</div>`));
    row.appendChild(el(`<div class='bar-row'><span class='code'>predit</span><span class='track'><span class='fill' style='width:${Math.round(b.predicted*100)}%'></span></span><span class='pct'>${pct(b.predicted)}</span></div>`));
    const weak=(b.actual<b.predicted-0.1)?'weak':'';
    row.appendChild(el(`<div class='bar-row'><span class='code'>reel</span><span class='track'><span class='fill ${weak}' style='width:${Math.round(b.actual*100)}%'></span></span><span class='pct'>${pct(b.actual)}</span></div>`));
    rc.appendChild(row);
  });
  if(!any) rc.appendChild(el("<div class='note'>Pas assez de variete dans les niveaux de confiance pour tracer la courbe.</div>"));
  v.appendChild(rc);

  if(d.trend && d.trend.available){
    const tr=el("<div class='card'></div>");
    tr.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Tendance du score de Brier</h2>"));
    const dir=d.trend.direction; let txt,col;
    if(dir==='amelioration'){txt="Calibration en amelioration : le score de Brier baisse au fil des sessions";col="#2f7d4f";}
    else if(dir==='degradation'){txt="Calibration en recul : le score de Brier augmente";col="#b1442f";}
    else{txt="Calibration stable au fil des sessions";col="#5c6b73";}
    tr.appendChild(el(`<div style='font-family:Avenir Next,Segoe UI,sans-serif;font-weight:700;color:${col};margin-bottom:6px'>${txt}</div>`));
    tr.appendChild(el(`<div class='note' style='margin-top:0'>1re moitie : Brier ${d.trend.first_half_brier.toFixed(3)} &middot; 2de moitie : ${d.trend.second_half_brier.toFixed(3)} (plus bas = mieux) &middot; ${d.trend.n} predictions reparties en tranches chronologiques.</div>`));
    const row=el("<div style='display:flex;align-items:flex-end;gap:8px;height:130px;margin-top:12px'></div>");
    d.trend.buckets.forEach(b=>{
      const quality=Math.max(0,Math.min(1,1-b.brier));
      const h=Math.round(8+quality*100);
      const bar=el("<div style='flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%'></div>");
      bar.appendChild(el(`<div style='font-size:11px;color:var(--muted);margin-bottom:4px'>${b.brier.toFixed(2)}</div>`));
      bar.appendChild(el(`<div title='tranche ${b.i} — ${b.n} reponses — Brier ${b.brier.toFixed(3)}' style='width:100%;background:var(--teal);border-radius:6px 6px 0 0;height:${h}px'></div>`));
      bar.appendChild(el(`<div style='font-size:11px;color:var(--muted);margin-top:4px'>${b.i}</div>`));
      row.appendChild(bar);
    });
    tr.appendChild(row);
    tr.appendChild(el("<div class='note' style='margin-top:6px'>Chaque barre = une tranche chronologique de predictions ; hauteur proportionnelle a la qualite de calibration (1 - Brier).</div>"));
    v.appendChild(tr);
  }

  if(d.per_domain && d.per_domain.length){
    const t=el("<div class='card'></div>");
    t.appendChild(el("<h2 style='margin-top:0;border:0;padding:0;font-size:18px'>Calibration par domaine</h2>"));
    const tab=el("<table class='res'><thead><tr><th>Domaine</th><th>n</th><th>Predit</th><th>Reel</th><th>Ecart</th></tr></thead><tbody></tbody></table>");
    const tb=tab.querySelector('tbody');
    d.per_domain.forEach(p=>{
      const sign=p.gap>0?'+':'';
      tb.appendChild(el(`<tr><td title='${escapeHtml(domLabel(p.domain))}'>${p.domain}</td><td>${p.n}</td><td>${pct(p.predicted)}</td><td>${pct(p.actual)}</td><td>${sign}${Math.round(p.gap*100)} pts</td></tr>`));
    });
    t.appendChild(tab);
    v.appendChild(t);
  }
}
function domLabel(code){const d=(STATE.domains||[]).find(x=>x.code===code);return d?d.label:code;}

async function boot(){
  const d=await api('GET','/bootstrap');
  STATE.user=d.user;STATE.cert=d.certification;STATE.domains=d.domains;STATE.second=d.second_order;
  route();
}
boot().catch(e=>{document.getElementById('view').innerHTML="<h1>Erreur</h1><p>"+e.message+"</p>";});
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Serveur HTTP                                                                #
# --------------------------------------------------------------------------- #

class Handler(BaseHTTPRequestHandler):
    server_version = "DOFPrep/1.0"

    def log_message(self, fmt, *args):
        pass  # silencieux

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, message, status=400):
        self._send_json({"error": {"code": code, "message": message}}, status)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ----------------------------- GET ----------------------------------- #
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            return self._send_html(HTML_PAGE)
        if path == "/health":
            return self._send_json({"status": "ok"})
        if path.startswith("/api/v1/"):
            return self._api_get(path[len("/api/v1"):])
        self._error("not_found", "Ressource introuvable.", 404)

    def _api_get(self, route):
        conn = get_db()
        try:
            user = get_user(conn)
            if route == "/bootstrap":
                cert = conn.execute("SELECT * FROM certification WHERE code = ?", (CERT_CODE,)).fetchone()
                domains = conn.execute(
                    "SELECT code, label, weight FROM domain WHERE certification_id = ? ORDER BY sort_order",
                    (cert["id"],),
                ).fetchall()
                so = bool(user["second_order"]) if "second_order" in user.keys() else False
                return self._send_json({
                    "user": {"id": user["id"], "username": user["username"],
                             "target_score": user["target_score"], "second_order": so},
                    "certification": {
                        "code": cert["code"], "label": cert["label"],
                        "pass_threshold": cert["pass_threshold"],
                        "question_count": cert["question_count"],
                        "duration_min": cert["duration_min"],
                    },
                    "domains": [{"code": d["code"], "label": d["label"], "weight": d["weight"]} for d in domains],
                    "second_order": {
                        "enabled": so,
                        "available": True,
                        "confidence_choices": CONFIDENCE_CHOICES,
                        "min_records": CALIB_MIN_RECORDS,
                        "calibration_floor": CALIB_FLOOR,
                    },
                })
            if route == "/dashboard":
                so = bool(user["second_order"]) if "second_order" in user.keys() else False
                readiness = compute_readiness(conn, user["id"], second_order=so)
                target = user["target_score"]
                ready = readiness["readiness"] >= target and not readiness["weak_domains"]
                payload = {
                    "user": {"target_score": target, "second_order": so},
                    "readiness": readiness,
                    "ready_for_exam": ready,
                    "recommendations": build_recommendations(readiness, target),
                }
                if so:
                    payload["calibration"] = compute_calibration(conn, user["id"])
                return self._send_json(payload)
            if route == "/calibration":
                return self._send_json(compute_calibration(conn, user["id"]))
            if route == "/review/due":
                today = date.today().isoformat()
                rows = conn.execute(
                    "SELECT question_id FROM sr_card WHERE user_id = ? AND due_date <= ? ORDER BY due_date LIMIT 20",
                    (user["id"], today),
                ).fetchall()
                qs = [serialize_question(conn, r["question_id"]) for r in rows]
                return self._send_json({"questions": qs})
            if route == "/exams/presets":
                return self._send_json({"presets": [preset_info(p) for p in EXAM_PRESETS]})
            return self._error("not_found", "Endpoint inconnu.", 404)
        finally:
            conn.close()

    # ----------------------------- POST ---------------------------------- #
    def do_POST(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/v1/"):
            return self._error("not_found", "Ressource introuvable.", 404)
        route = path[len("/api/v1"):]
        body = self._read_body()
        conn = get_db()
        try:
            user = get_user(conn)
            if route == "/exams/generate":
                preset_id = body.get("preset_id")
                if preset_id is not None:
                    preset = next((p for p in EXAM_PRESETS if p["id"] == preset_id), None)
                    if preset is None:
                        return self._error("bad_request", "Examen blanc inconnu.", 400)
                    level = preset["level"]
                    mode = "mock"
                    exam_name = "Examen blanc %d" % preset["id"]
                    # Les examens d'un meme niveau sont generes ensemble pour se
                    # partager les questions et minimiser le recouvrement.
                    same_level = [p for p in EXAM_PRESETS if p["level"] == level]
                    idx = same_level.index(preset)
                    exams = build_band_exams(conn, level, n_exams=len(same_level))
                    qids = exams[idx]
                    session_id = persist_exam_session(conn, user["id"], qids, level)
                else:
                    level = body.get("level")
                    if level is not None and level not in LEVEL_BANDS:
                        return self._error("bad_request", "Niveau de difficulte invalide.", 400)
                    mode = body.get("mode", "mock")
                    exam_name = None
                    session_id, qids = generate_exam(conn, user["id"], mode=mode, level=level, seed=None)
                cert = conn.execute("SELECT * FROM certification WHERE code = ?", (CERT_CODE,)).fetchone()
                qs = [serialize_question(conn, qid) for qid in qids]
                return self._send_json({
                    "session_id": session_id,
                    "duration_min": cert["duration_min"],
                    "question_count": len(qs),
                    "questions": qs,
                    "mode": mode,
                    "level": level,
                    "level_label": LEVEL_LABEL.get(level) if level else None,
                    "exam_name": exam_name,
                })
            if route.startswith("/exams/sessions/") and route.endswith("/submit"):
                try:
                    sid = int(route.split("/")[3])
                except (IndexError, ValueError):
                    return self._error("bad_request", "Session invalide.", 400)
                answers = body.get("answers", [])
                result = grade_answers(conn, user["id"], answers, context="exam")
                cert = conn.execute("SELECT * FROM certification WHERE code = ?", (CERT_CODE,)).fetchone()
                passed = result["score"] >= cert["pass_threshold"]
                conn.execute(
                    "UPDATE exam_session SET ended_at = datetime('now'), score = ?, passed = ?, status = 'submitted'"
                    " WHERE id = ?",
                    (result["score"], 1 if passed else 0, sid),
                )
                # Second ordre : journal de confiance + re-modelage des items.
                so = bool(user["second_order"]) if "second_order" in user.keys() else False
                if so:
                    correctness = {r["question_id"]: r["is_correct"] for r in result["review"]}
                    qdom = {}
                    for ans in answers:
                        qid = ans.get("question_id")
                        if qid is None or qid not in correctness:
                            continue
                        ok = correctness[qid]
                        if qid not in qdom:
                            row = conn.execute("SELECT domain_id FROM question WHERE id = ?", (qid,)).fetchone()
                            qdom[qid] = row["domain_id"] if row else None
                        conf = ans.get("confidence")
                        if conf is not None and qdom[qid] is not None:
                            log_confidence(conn, user["id"], qid, qdom[qid], "exam", conf / 100.0, ok)
                        second_order_update_item(conn, user["id"], qid, ok)
                conn.commit()
                readiness = compute_readiness(conn, user["id"], second_order=so)
                target = user["target_score"]
                result["passed"] = passed
                result["threshold"] = cert["pass_threshold"]
                result["target_score"] = target
                result["readiness"] = readiness["readiness"]
                result["readiness_raw"] = readiness["readiness_raw"]
                result["ready_for_exam"] = readiness["readiness"] >= target and not readiness["weak_domains"]
                if so:
                    result["calibration"] = compute_calibration(conn, user["id"])
                return self._send_json(result)
            if route == "/training/start":
                domain = body.get("domain")
                count = int(body.get("count", 10))
                if domain:
                    rows = conn.execute(
                        "SELECT q.id FROM question q JOIN domain d ON q.domain_id = d.id"
                        " WHERE d.code = ? AND q.status = 'published' ORDER BY RANDOM() LIMIT ?",
                        (domain, count),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT id FROM question WHERE status = 'published' ORDER BY RANDOM() LIMIT ?",
                        (count,),
                    ).fetchall()
                qs = [serialize_question(conn, r["id"]) for r in rows]
                return self._send_json({"questions": qs})
            if route == "/training/answer":
                qid = body.get("question_id")
                selected = set(body.get("selected_option_ids") or [])
                q = conn.execute("SELECT * FROM question WHERE id = ?", (qid,)).fetchone()
                if not q:
                    return self._error("not_found", "Question introuvable.", 404)
                opts = conn.execute("SELECT id, is_correct FROM answer_option WHERE question_id = ?", (qid,)).fetchall()
                correct_ids = set(o["id"] for o in opts if o["is_correct"])
                is_correct = (selected == correct_ids) and len(selected) > 0
                conn.execute(
                    "INSERT INTO attempt_log (user_id, question_id, domain_id, is_correct, context)"
                    " VALUES (?, ?, ?, ?, 'training')",
                    (user["id"], qid, q["domain_id"], 1 if is_correct else 0),
                )
                update_mastery(conn, user["id"], q["domain_id"], is_correct)
                sm2_review(conn, user["id"], qid, 5 if is_correct else 2)
                so = bool(user["second_order"]) if "second_order" in user.keys() else False
                if so:
                    conf = body.get("confidence")
                    if conf is not None:
                        log_confidence(conn, user["id"], qid, q["domain_id"], "training", conf / 100.0, is_correct)
                    second_order_update_item(conn, user["id"], qid, is_correct)
                conn.commit()
                return self._send_json({
                    "is_correct": is_correct,
                    "correct_option_ids": sorted(correct_ids),
                    "explanation": q["explanation"],
                })
            return self._error("not_found", "Endpoint inconnu.", 404)
        finally:
            conn.close()

    # ----------------------------- PATCH --------------------------------- #
    def do_PATCH(self):
        path = urlparse(self.path).path
        route = path[len("/api/v1"):] if path.startswith("/api/v1/") else ""
        if route != "/me/preferences":
            return self._error("not_found", "Ressource introuvable.", 404)
        body = self._read_body()
        target = body.get("target_score")
        second_order = body.get("second_order")
        if target is None and second_order is None:
            return self._error("validation", "Aucune preference fournie.", 422)
        if target is not None and (not isinstance(target, (int, float)) or target < TARGET_MIN or target > TARGET_MAX):
            return self._error(
                "validation",
                "La cible doit etre comprise entre %.0f %% et %.0f %%." % (TARGET_MIN * 100, TARGET_MAX * 100),
                422,
            )
        conn = get_db()
        try:
            if target is not None:
                conn.execute("UPDATE app_user SET target_score = ? WHERE id = 1", (float(target),))
            if second_order is not None:
                conn.execute("UPDATE app_user SET second_order = ? WHERE id = 1",
                             (1 if second_order else 0,))
            conn.commit()
            user = get_user(conn)
            so = bool(user["second_order"]) if "second_order" in user.keys() else False
            tgt = user["target_score"]
            readiness = compute_readiness(conn, 1, second_order=so)
            ready = readiness["readiness"] >= tgt and not readiness["weak_domains"]
            return self._send_json({
                "target_score": tgt,
                "second_order": so,
                "current_readiness": readiness["readiness"],
                "ready_for_exam": ready,
            })
        finally:
            conn.close()


# --------------------------------------------------------------------------- #
# Demarrage                                                                   #
# --------------------------------------------------------------------------- #

def main():
    init_db()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = "http://%s:%d/" % ("localhost" if HOST in ("0.0.0.0", "127.0.0.1") else HOST, PORT)
    print("=" * 60)
    print("  DOF-PREP — Preparation DevOps Foundation")
    print("  Serveur demarre : " + url)
    print("  Base de donnees : " + os.path.abspath(DB_PATH))
    print("  (Ctrl+C pour arreter)")
    print("=" * 60)
    if OPEN_BROWSER and HOST in ("127.0.0.1", "localhost"):
        try:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArret du serveur.")
        httpd.server_close()


if __name__ == "__main__":
    main()