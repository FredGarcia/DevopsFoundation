#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_tests.py — Jeu de DEX de test (vrais/faux positifs et négatifs) pour
dex_castin_common.process_dex(), avec calcul d'un pourcentage de réussite
par test et par "traitement" (règle métier).

USAGE :
    python run_tests.py            # génère les .docx de test (si absents) et exécute les vérifications
    python run_tests.py --rebuild  # régénère systématiquement les .docx de test

Chaque test décrit :
  - un DEX .docx synthétique (construit avec docx_builder.DocxBuilder) ;
  - une liste de VÉRIFICATIONS, chacune rattachée à une catégorie de
    "traitement" (règle 1 à 8 du prompt de reprise, liens DAP/ADU, champs
    composés, identification, informations supplémentaires) ;
  - le résultat attendu (ground truth métier), comparé au résultat réel de
    process_dex().

Certains tests sont volontairement des "faux positifs" / "faux négatifs"
connus de l'outil (ex: contenu légitime en italique/couleur exclu à tort,
section non détectée car titre non standard) : leur score < 100% quantifie
l'impact de la limitation, documentée dans README.md / DOSSIER_TECHNICO_FONCTIONNEL.md.

Sortie : rapport console + fichier tests/RAPPORT_TESTS.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
FIXTURES_DIR = THIS_DIR / "fixtures"

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(THIS_DIR))

import dex_castin_common as dex  # noqa: E402
from docx_builder import DocxBuilder  # noqa: E402


# --------------------------------------------------------------------------- #
# Construction des DEX de test                                                 #
# --------------------------------------------------------------------------- #

def build_complet() -> DocxBuilder:
    """Cas nominal : toutes les sections présentes, bien structurées."""
    b = DocxBuilder()
    b.para("Auteur : Alice Martin")
    b.para("Responsable : Bob Lefevre")

    b.heading("2.1 Description de la solution", 1)
    b.para("La solution permet la gestion des commandes clients en temps réel.")
    b.para(
        "Ce paragraphe est un texte d'aide explicatif, à ne pas reprendre dans CAST'IN.",
        italic=True,
        color="0070C0",
    )

    b.heading("2.2 Architecture fonctionnelle & applicative", 1)
    b.hyperlink_para("DAP1001", "https://archi.example.com/DAP1001")
    b.para("Schéma applicatif : ADU2002")

    b.heading("2.3 Données", 1)
    b.para("Base de données Oracle, schéma CMD_PROD.")

    b.heading("4.1 Architecture technique", 1)
    b.para("Solution hébergée sur Kubernetes (3 pods), exposée via une API REST.")

    b.heading("3.3 Plages de fonctionnement", 1)
    b.para("Disponible 24/7, fenêtre de maintenance le dimanche 02h00-04h00.")

    b.heading("6 Supervision", 1)
    b.para("Supervisée par Centreon, sondes HTTP toutes les 5 minutes.")
    b.heading("6.1 Alertes", 2)
    b.para("Alerte envoyée à l'équipe d'astreinte par email et SMS.")

    b.heading("9 Métrologie", 1)
    b.para("Tableaux de bord Grafana : taux d'erreur, latence, volumétrie.")

    b.heading("8.2 Diagnostique", 1)
    b.para("Logs centralisés dans ELK, niveau INFO par défaut.")

    b.heading("7 Sauvegarde", 1)
    b.para("Sauvegarde quotidienne de la base à 01h00, conservation 30 jours.")

    b.heading("11 Servitudes et ordonnancements", 1)
    b.para("Le job nocturne JOB_EXPORT doit s'exécuter après JOB_CONSOLIDATION.")

    b.heading("12.2 Compte de service", 1)
    b.table([
        ["Compte", "Usage"],
        ["svc_cmd_app", "Exécution de l'application"],
        ["svc_cmd_batch", "Exécution des traitements batch"],
    ])

    b.heading("12.3 Certificats", 1)
    b.table([["Certificat", "Échéance"], ["cmd.prod.example.com", "2027-01-15"]])

    b.heading("12.4 Liste blanche", 1)
    b.table([["Adresse IP", "Port", "Justification"], ["10.0.1.5", "443", "Appel API partenaire"]])

    b.heading("4.3 Flux et interdépendances", 1)
    b.table([
        ["Source", "Destination", "Protocole", "Port"],
        ["App CMD", "Base Oracle", "TCP", "1521"],
        ["App CMD", "API Partenaire", "HTTPS", "443"],
    ])

    b.heading("8.1 Matrice de responsabilité", 1)
    b.table([
        ["Activité", "Responsable"],
        ["Supervision N1", "Equipe Exploitation"],
        ["Correctif applicatif", "Equipe Dev CMD"],
    ])

    b.heading("10 Contrôle des opérations", 1)
    b.para("Toute opération de maintenance doit être validée via un ticket de changement CHG.")

    b.heading("5 Changements et MEP", 1)
    b.para("Les mises en production sont planifiées le mercredi soir, hors période de gel.")

    b.heading("5.1 Référentiel", 1)
    b.para("Code source disponible sur GitLab : groupe/cmd-app.")
    b.para("Les livraisons sont validées via Merge Request avant fusion sur la branche main.")

    b.heading("13.1 Restauration", 1)
    b.para("Restaurer la base depuis la dernière sauvegarde via le script restore_cmd.sh.")

    b.heading("13.2 Reconstruction", 1)
    b.para("Reconstruire l'environnement à partir du pipeline Terraform 'infra-cmd'.")

    b.heading("13.3 Resynchronisation", 1)
    b.para("Relancer le job de resynchronisation JOB_RESYNC_CMD en cas de désynchronisation.")

    b.heading("4.2.2 Assets mainframe", 1)
    b.para("Non applicable : la solution ne comporte pas de composants mainframe.")

    b.heading("14 Annexes", 1)
    b.para("Contact astreinte : astreinte-cmd@example.com.")

    return b


def build_sections_manquantes() -> DocxBuilder:
    """Seules deux sections sont présentes ; toutes les autres sont absentes
    -> doivent être marquées "Non concerné" + signalées."""
    b = DocxBuilder()
    b.para("Auteur : Claire Dubois")
    b.para("Responsable : David Nguyen")

    b.heading("2.1 Description de la solution", 1)
    b.para("Portail interne de suivi des incidents.")

    b.heading("4.1 Architecture technique", 1)
    b.para("Application monolithique Java déployée sur 2 serveurs Tomcat.")

    return b


def build_faux_positif_italique() -> DocxBuilder:
    """Faux positif : un paragraphe de contenu FONCTIONNEL légitime est
    entièrement en italique/couleur (mise en forme malheureuse de l'auteur du
    DEX) -> l'outil l'exclut à tort comme s'il s'agissait d'un texte d'aide."""
    b = DocxBuilder()
    b.para("Auteur : Eric Petit")
    b.para("Responsable : Fanny Roche")

    b.heading("2.1 Description de la solution", 1)
    b.para("La solution gère la facturation des abonnements.")
    # Contenu MÉTIER légitime, mais mis en forme comme le texte d'aide
    # (italique + couleur) -> sera exclu par l'heuristique de la règle 2.
    b.para(
        "Important : la facturation est suspendue automatiquement après 3 échecs de paiement.",
        italic=True,
        color="0070C0",
    )

    b.heading("4.1 Architecture technique", 1)
    b.para("Application Node.js sur conteneurs Docker.")

    return b


def build_faux_negatif_titre_non_standard() -> DocxBuilder:
    """Faux négatif : la section "Sauvegarde" existe et contient du contenu,
    mais son titre est mis en forme avec un style personnalisé non reconnu
    comme titre par l'outil (pas de "Heading/Titre N", pas d'outlineLvl)
    -> la section n'est pas détectée comme telle."""
    b = DocxBuilder()
    b.para("Auteur : Grace Tan")
    b.para("Responsable : Hugo Bernard")

    b.heading("2.1 Description de la solution", 1)
    b.para("Application de gestion des stocks.")

    b.heading("4.1 Architecture technique", 1)
    b.para("Base de données MySQL répliquée.")

    # Titre "visuel" (gras) mais NON reconnu comme titre par l'outil.
    b.heading_unstyled("7 Sauvegarde")
    b.para("Sauvegarde hebdomadaire complète + sauvegardes incrémentales quotidiennes.")

    return b


def build_numerotation_atypique() -> DocxBuilder:
    """Toutes les sections sont présentes mais numérotées très différemment
    des indications du prompt -> doivent être retrouvées par leur NOM
    (règle 1), pas par leur numéro."""
    b = DocxBuilder()
    b.para("Auteur : Ines Roussel")
    b.para("Responsable : Julien Caron")

    # "Description de la solution" en chapitre 9.4 au lieu de ~2.1
    b.heading("9.4 Description de la solution", 1)
    b.para("Plateforme de réservation de salles de réunion.")

    # "Architecture technique" en chapitre 2.1 au lieu de ~4.1
    b.heading("2.1 Architecture technique", 1)
    b.para("Application .NET hébergée sur IIS, base SQL Server.")

    # "Supervision" en Annexe B au lieu de ~6
    b.heading("Annexe B Supervision", 1)
    b.para("Supervision via Nagios, vérification toutes les 10 minutes.")

    return b


def build_liens_dap_adu_sections_separees() -> DocxBuilder:
    """Le lien DAP est dans "Architecture fonctionnelle & applicative", la
    référence ADU est citée dans "Description de la solution" (section
    différente) -> les deux champs doivent être correctement renseignés en
    agrégeant plusieurs sections candidates."""
    b = DocxBuilder()
    b.para("Auteur : Karim Haddad")
    b.para("Responsable : Léa Fontaine")

    b.heading("2.1 Description de la solution", 1)
    b.para("Application de gestion des congés. Voir schéma applicatif ADU3003.")

    b.heading("2.2 Architecture fonctionnelle & applicative", 1)
    b.hyperlink_para("DAP4004", "https://archi.example.com/DAP4004")
    b.para("Architecture en 3 tiers classique.")

    b.heading("4.1 Architecture technique", 1)
    b.para("Frontend Angular, backend Spring Boot, PostgreSQL.")

    return b


def build_servitudes_absentes() -> DocxBuilder:
    """La solution n'a légitimement AUCUNE servitude/ordonnancement : la
    section est absente -> "Non concerné" est la valeur CORRECTE (règle 4 /
    règle "si aucune -> Non concerné"), même si l'outil ne peut pas
    distinguer "absence légitime" de "section manquante par erreur" et la
    signale donc aussi dans les points à vérifier (signalement superflu mais
    sans impact, à confirmer par l'Équipier Ops)."""
    b = DocxBuilder()
    b.para("Auteur : Marc Olivier")
    b.para("Responsable : Nina Garcia")

    b.heading("2.1 Description de la solution", 1)
    b.para("Site web vitrine statique, sans traitement batch ni dépendance externe.")

    b.heading("4.1 Architecture technique", 1)
    b.para("Site statique hébergé sur un CDN.")

    return b


def build_identification_absente() -> DocxBuilder:
    """Aucune information d'identification (numéro de solution, auteur,
    responsable) n'est présente -> les trois doivent être signalées dans les
    points à vérifier."""
    b = DocxBuilder()
    b.heading("2.1 Description de la solution", 1)
    b.para("Outil interne sans fiche d'identification renseignée.")

    b.heading("4.1 Architecture technique", 1)
    b.para("Script Python exécuté par tâche planifiée.")

    return b


# --------------------------------------------------------------------------- #
# Définition des tests (DEX, vérifications par catégorie de traitement)       #
# --------------------------------------------------------------------------- #

def champ(result: dict, key: str) -> str:
    return result["champs"][key]["content"]


def points_text(result: dict) -> str:
    return "\n".join(result["points_a_verifier"])


TESTS = [
    {
        "name": "01_cas_nominal_complet",
        "filename": "DEX_S20001_Nominal.docx",
        "description": "Cas nominal : toutes les sections présentes, bien structurées (vrais positifs attendus).",
        "build": build_complet,
        "checks": [
            ("identification", "Numéro de solution extrait du nom de fichier",
             lambda r: r["identification"]["solution"] == "S20001"),
            ("identification", "Auteur extrait de la page de garde",
             lambda r: r["identification"]["auteur"] == "Alice Martin"),
            ("identification", "Responsable extrait",
             lambda r: r["identification"]["responsable"] == "Bob Lefevre"),
            ("regle1_reperage", "Description Fonctionnelle retrouvée (par nom)",
             lambda r: "gestion des commandes clients" in champ(r, "description_fonctionnelle")),
            ("regle2_exclusion", "Texte d'aide italique/coloré exclu de la Description Fonctionnelle",
             lambda r: "à ne pas reprendre" not in champ(r, "description_fonctionnelle")),
            ("liens_dap_adu", "Lien Dossier Archi (DAP) retrouvé",
             lambda r: "DAP1001" in champ(r, "lien_dossier_archi") and "https://" in champ(r, "lien_dossier_archi")),
            ("liens_dap_adu", "Schéma Applicatif (ADU) retrouvé",
             lambda r: "ADU2002" in champ(r, "schema_applicatif")),
            ("regle1_reperage", "Données de la solution retrouvées",
             lambda r: "Oracle" in champ(r, "donnees_solution")),
            ("regle5_principes", "Principes et décisions laissé vide",
             lambda r: champ(r, "principes_decisions") == ""),
            ("regle1_reperage", "Description Technique retrouvée",
             lambda r: "Kubernetes" in champ(r, "description_technique")),
            ("regle1_reperage", "Plage de fonctionnement retrouvée",
             lambda r: "24/7" in champ(r, "plage_fonctionnement")),
            ("regle1_reperage", "Supervision retrouvée (chapitre + sous-section)",
             lambda r: "Centreon" in champ(r, "supervision") and "astreinte" in champ(r, "supervision")),
            ("regle1_reperage", "Observabilité (Métrologie) retrouvée",
             lambda r: "Grafana" in champ(r, "observabilite")),
            ("regle1_reperage", "Log (Diagnostique) retrouvé",
             lambda r: "ELK" in champ(r, "log")),
            ("regle1_reperage", "Sauvegardes retrouvées",
             lambda r: "Sauvegarde quotidienne" in champ(r, "sauvegardes")),
            ("regle1_reperage", "Servitudes et ordonnancements retrouvées",
             lambda r: "JOB_EXPORT" in champ(r, "servitudes")),
            ("tableaux", "Comptes et services (tableau) retrouvés",
             lambda r: "svc_cmd_app" in champ(r, "comptes_services")),
            ("tableaux", "Certificats (tableau) retrouvés",
             lambda r: "cmd.prod.example.com" in champ(r, "certificats")),
            ("tableaux", "Liste blanche (tableau) retrouvée",
             lambda r: "10.0.1.5" in champ(r, "liste_blanche")),
            ("tableaux", "Flux (tableau) retrouvés",
             lambda r: "App CMD" in champ(r, "flux") and "1521" in champ(r, "flux")),
            ("tableaux", "Support (matrice RACI, tableau) retrouvé",
             lambda r: "Equipe Exploitation" in champ(r, "support")),
            ("champs_composes", "Changement et MEP agrège Contrôle des opérations + Changements et MEP",
             lambda r: "ticket de changement" in champ(r, "changement_mep")
             and "mises en production" in champ(r, "changement_mep")),
            ("champs_composes", "Matière (repo) agrège le référentiel + la mention 'Merge Request'",
             lambda r: "groupe/cmd-app" in champ(r, "matiere_repo") and "Merge Request" in champ(r, "matiere_repo")),
            ("regle1_reperage", "Procédure de restauration retrouvée",
             lambda r: "restore_cmd.sh" in champ(r, "procedure_restauration")),
            ("regle1_reperage", "Procédure de reconstruction retrouvée",
             lambda r: "infra-cmd" in champ(r, "procedure_reconstruction")),
            ("regle1_reperage", "Procédure de resynchronisation retrouvée",
             lambda r: "JOB_RESYNC_CMD" in champ(r, "procedure_resynchronisation")),
            ("informations_supplementaires", "Informations supplémentaires : Assets mainframe + annexe",
             lambda r: "mainframe" in champ(r, "informations_supplementaires").lower()
             and "astreinte-cmd" in champ(r, "informations_supplementaires")),
            ("regle8_points_a_verifier", "Aucun point critique inattendu (RAS ou points mineurs uniquement)",
             lambda r: len(r["points_a_verifier"]) <= 1),
        ],
    },
    {
        "name": "02_sections_manquantes",
        "filename": "DEX_S20002_Minimal.docx",
        "description": "Sections majoritairement absentes : doivent être marquées 'Non concerné' et signalées (vrais négatifs attendus).",
        "build": build_sections_manquantes,
        "checks": [
            ("regle1_reperage", "Description Fonctionnelle retrouvée",
             lambda r: "incidents" in champ(r, "description_fonctionnelle")),
            ("regle1_reperage", "Description Technique retrouvée",
             lambda r: "Tomcat" in champ(r, "description_technique")),
            ("regle4_non_concerne", "Supervision absente -> 'Non concerné'",
             lambda r: champ(r, "supervision") == "Non concerné"),
            ("regle4_non_concerne", "Sauvegardes absentes -> 'Non concerné'",
             lambda r: champ(r, "sauvegardes") == "Non concerné"),
            ("regle4_non_concerne", "Certificats absents -> 'Non concerné'",
             lambda r: champ(r, "certificats") == "Non concerné"),
            ("regle4_non_concerne", "Liste blanche absente -> 'Non concerné'",
             lambda r: champ(r, "liste_blanche") == "Non concerné"),
            ("regle8_points_a_verifier", "Sections absentes toutes signalées dans les points à vérifier",
             lambda r: all(
                 f"« {dex.CASTIN_FIELDS[i]['label']} »" in points_text(r)
                 for i, fd in enumerate(dex.CASTIN_FIELDS)
                 if fd["key"] in (
                     "supervision", "observabilite", "log", "sauvegardes", "servitudes",
                     "comptes_services", "certificats", "liste_blanche", "flux", "support",
                     "changement_mep", "matiere_repo", "procedure_restauration",
                     "procedure_reconstruction", "procedure_resynchronisation",
                 )
             )),
        ],
    },
    {
        "name": "03_faux_positif_italique_legitime",
        "filename": "DEX_S20003_FauxPositif.docx",
        "description": (
            "FAUX POSITIF connu : contenu fonctionnel légitime mis en forme en italique/couleur "
            "-> exclu à tort par l'heuristique de la règle 2 (score < 100% attendu : limite documentée)."
        ),
        "build": build_faux_positif_italique,
        "checks": [
            ("regle1_reperage", "Première phrase de la Description Fonctionnelle retrouvée",
             lambda r: "facturation des abonnements" in champ(r, "description_fonctionnelle")),
            ("regle2_exclusion", "[FAUX POSITIF ATTENDU] Le contenu métier en italique/couleur est CONSERVÉ",
             lambda r: "suspendue automatiquement après 3 échecs" in champ(r, "description_fonctionnelle")),
        ],
    },
    {
        "name": "04_faux_negatif_titre_non_standard",
        "filename": "DEX_S20004_FauxNegatif.docx",
        "description": (
            "FAUX NÉGATIF connu : section 'Sauvegarde' présente mais avec un titre dans un style non "
            "reconnu -> section non détectée, contenu non repris (score < 100% attendu : limite documentée)."
        ),
        "build": build_faux_negatif_titre_non_standard,
        "checks": [
            ("regle1_reperage", "Description Fonctionnelle retrouvée",
             lambda r: "gestion des stocks" in champ(r, "description_fonctionnelle")),
            ("regle1_reperage", "Description Technique retrouvée",
             lambda r: "MySQL" in champ(r, "description_technique")),
            ("regle1_reperage", "[FAUX NÉGATIF ATTENDU] Section Sauvegardes détectée malgré le titre non standard",
             lambda r: "Sauvegarde hebdomadaire" in champ(r, "sauvegardes")),
        ],
    },
    {
        "name": "05_numerotation_atypique",
        "filename": "DEX_S20005_Numerotation.docx",
        "description": "Sections numérotées très différemment des indications du prompt : doivent être retrouvées par leur NOM (règle 1).",
        "build": build_numerotation_atypique,
        "checks": [
            ("regle1_reperage", "Description Fonctionnelle retrouvée malgré la numérotation 9.4",
             lambda r: "réservation de salles" in champ(r, "description_fonctionnelle")),
            ("regle1_reperage", "Description Technique retrouvée malgré la numérotation 2.1",
             lambda r: "IIS" in champ(r, "description_technique")),
            ("regle1_reperage", "Supervision retrouvée malgré le placement en 'Annexe B'",
             lambda r: "Nagios" in champ(r, "supervision")),
        ],
    },
    {
        "name": "06_liens_dap_adu_sections_separees",
        "filename": "DEX_S20006_LiensSepares.docx",
        "description": "Lien DAP et référence ADU répartis sur deux sections différentes : agrégation multi-sections.",
        "build": build_liens_dap_adu_sections_separees,
        "checks": [
            ("liens_dap_adu", "Lien Dossier Archi (DAP) retrouvé dans 'Architecture fonctionnelle & applicative'",
             lambda r: "DAP4004" in champ(r, "lien_dossier_archi")
             and "https://archi.example.com/DAP4004" in champ(r, "lien_dossier_archi")),
            ("liens_dap_adu", "Schéma Applicatif (ADU) retrouvé dans 'Description de la solution'",
             lambda r: "ADU3003" in champ(r, "schema_applicatif")),
            ("regle2_exclusion", "Lien Dossier Archi ne contient PAS de texte hors-périmètre",
             lambda r: "3 tiers" not in champ(r, "lien_dossier_archi")),
        ],
    },
    {
        "name": "07_servitudes_absentes_non_concerne",
        "filename": "DEX_S20007_Servitudes.docx",
        "description": "Absence légitime de servitudes : 'Non concerné' est la valeur correcte (règle 4).",
        "build": build_servitudes_absentes,
        "checks": [
            ("regle4_non_concerne", "Servitudes et ordonnancements -> 'Non concerné'",
             lambda r: champ(r, "servitudes") == "Non concerné"),
            ("regle1_reperage", "Description Fonctionnelle retrouvée",
             lambda r: "vitrine statique" in champ(r, "description_fonctionnelle")),
        ],
    },
    {
        "name": "08_identification_absente",
        "filename": "DEX_sans_identification.docx",
        "description": "Aucune information d'identification présente : doit être signalé pour les 3 champs.",
        "build": build_identification_absente,
        "checks": [
            ("identification", "Numéro de solution absent -> signalé",
             lambda r: r["identification"]["solution"] is None and "Numéro de solution" in points_text(r)),
            ("identification", "Auteur absent -> signalé",
             lambda r: r["identification"]["auteur"] is None and "Auteur du DEX" in points_text(r)),
            ("identification", "Responsable absent -> signalé",
             lambda r: r["identification"]["responsable"] is None and "Responsable" in points_text(r)),
            ("regle1_reperage", "Description Fonctionnelle retrouvée malgré l'absence d'identification",
             lambda r: "fiche d'identification" in champ(r, "description_fonctionnelle")),
        ],
    },
]


CATEGORY_LABELS = {
    "identification": "Identification (Solution / Auteur / Responsable)",
    "regle1_reperage": "Règle 1 — Repérage des sections par leur nom",
    "regle2_exclusion": "Règle 2 — Exclusion du contenu non utile / explicatif",
    "regle4_non_concerne": "Règle 4 — Information absente -> 'Non concerné'",
    "regle5_principes": "Règle 5 — 'Principes et décisions' vide",
    "regle8_points_a_verifier": "Règle 8 — Signalement des doutes (points à vérifier)",
    "liens_dap_adu": "Liens DAP / ADU (champs 'lien uniquement')",
    "tableaux": "Extraction de contenu en tableaux",
    "champs_composes": "Champs composés (Changement et MEP / Matière (repo))",
    "informations_supplementaires": "Informations supplémentaires (annexe + Assets mainframe)",
}


# --------------------------------------------------------------------------- #
# Exécution                                                                     #
# --------------------------------------------------------------------------- #

def run(rebuild: bool) -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    report_lines: list[str] = []
    report_lines.append("# Rapport de tests — Reprise DEX -> CAST'IN\n")
    report_lines.append(
        "Ce rapport est généré par `tests/run_tests.py` à partir de DEX `.docx` "
        "synthétiques couvrant des cas nominaux, des absences attendues, et des "
        "FAUX POSITIFS / FAUX NÉGATIFS connus de l'outil.\n"
    )

    category_totals: dict[str, list[int]] = {}  # category -> [passed, total]
    overall = [0, 0]

    for test in TESTS:
        docx_path = FIXTURES_DIR / test["filename"]
        if rebuild or not docx_path.exists():
            builder: DocxBuilder = test["build"]()
            builder.write(str(docx_path))

        result = dex.process_dex(str(docx_path), filename=test["filename"])

        passed = 0
        total = len(test["checks"])
        details = []
        for category, description, predicate in test["checks"]:
            try:
                ok = bool(predicate(result))
            except Exception as exc:  # noqa: BLE001
                ok = False
                description = f"{description} (ERREUR : {exc})"
            passed += 1 if ok else 0
            overall[0] += 1 if ok else 0
            overall[1] += 1
            totals = category_totals.setdefault(category, [0, 0])
            totals[0] += 1 if ok else 0
            totals[1] += 1
            details.append((ok, description))

        pct = 100.0 * passed / total if total else 100.0

        print(f"\n[{test['name']}] {test['description']}")
        print(f"  Fichier : fixtures/{test['filename']}")
        print(f"  Score   : {passed}/{total} ({pct:.0f}%)")
        for ok, description in details:
            print(f"    [{'OK' if ok else 'KO'}] {description}")

        report_lines.append(f"## {test['name']}\n")
        report_lines.append(f"{test['description']}\n")
        report_lines.append(f"- Fichier : `fixtures/{test['filename']}`")
        report_lines.append(f"- **Score : {passed}/{total} ({pct:.0f}%)**\n")
        for ok, description in details:
            mark = "✅" if ok else "❌"
            report_lines.append(f"  - {mark} {description}")
        report_lines.append("")

    print("\n" + "=" * 70)
    print("RÉCAPITULATIF PAR TRAITEMENT (règle métier)")
    report_lines.append("## Récapitulatif par traitement (règle métier)\n")
    report_lines.append("| Traitement | Score | % |")
    report_lines.append("|---|---|---|")
    for category, (p, t) in sorted(category_totals.items()):
        pct = 100.0 * p / t if t else 100.0
        label = CATEGORY_LABELS.get(category, category)
        print(f"  {label:<55} {p}/{t} ({pct:.0f}%)")
        report_lines.append(f"| {label} | {p}/{t} | {pct:.0f}% |")

    overall_pct = 100.0 * overall[0] / overall[1] if overall[1] else 100.0
    print("\n" + "=" * 70)
    print(f"SCORE GLOBAL : {overall[0]}/{overall[1]} ({overall_pct:.0f}%)")
    report_lines.append(f"\n## Score global\n\n**{overall[0]}/{overall[1]} ({overall_pct:.0f}%)**\n")

    report_lines.append(
        "\n## Lecture des résultats\n\n"
        "- Les tests `03_faux_positif_italique_legitime` et "
        "`04_faux_negatif_titre_non_standard` contiennent des vérifications "
        "marquées **[FAUX POSITIF ATTENDU]** / **[FAUX NÉGATIF ATTENDU]** : "
        "leur échec (❌) est **normal** et quantifie une limite connue de "
        "l'outil (cf. README.md, section \"Limites connues\"). Un score de "
        "0% sur CES lignes précises ne signale pas une régression.\n"
        "- Pour tous les autres tests, un score < 100% indique une "
        "régression à analyser.\n"
    )

    (THIS_DIR / "RAPPORT_TESTS.md").write_text("\n".join(report_lines), encoding="utf-8")
    print("\nRapport détaillé écrit dans tests/RAPPORT_TESTS.md")

    # Code de retour : 0 même si des FAUX POSITIFS/NÉGATIFS connus échouent,
    # car ce sont des résultats ATTENDUS (documentés), pas des régressions.
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Régénère systématiquement les .docx de test.")
    args = parser.parse_args()
    return run(rebuild=args.rebuild)


if __name__ == "__main__":
    raise SystemExit(main())
