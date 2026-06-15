#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dex_castin_common.py — Cœur commun de la reprise DEX (Word) → CAST'IN.

Ce module est PARTAGE par les deux automatisations :
  - dex_castin_cli.py            (utilisation autonome en ligne de commande / DOS)
  - dex_castin_word_addin_server.py (utilisation depuis Word via un complement Office.js)

Il NE DEPEND QUE DE LA BIBLIOTHEQUE STANDARD de Python 3 (zipfile, xml.etree,
re, unicodedata...) : un fichier .docx est une archive ZIP contenant du XML
(OOXML), lisible sans installer "python-docx".

OBJECTIF
--------
Reprendre le contenu d'un DEX (.docx) et produire, pour chaque champ CAST'IN
défini dans CASTIN_FIELDS, le contenu "prêt à coller" — en respectant les
règles impératives du prompt de reprise :

  1. Repérage des sections par leur NOM (jamais par leur numéro de chapitre,
     qui varie d'un DEX à l'autre). Les numéros indiqués dans CASTIN_FIELDS
     ne sont que des INDICES, jamais un critère de recherche.
  2. Seul le contenu utile (texte, liens, références de schémas) est repris ;
     les titres de section et les paragraphes "explicatifs" (italique +
     couleur, typiquement en bleu) sont écartés.
  3. Les caractères spéciaux parasites (puces Wingdings, espaces
     insécables, caractères de contrôle...) sont nettoyés.
  4. Une information absente est remplacée par exactement : "Non concerné".
  5. Le champ "Principes et décisions" reste VIDE.
  6. Le champ "Informations supplémentaires" est optionnel.
  7. Le contenu n'est ni reformulé ni réécrit : uniquement nettoyé/réorganisé.
  8. Toute ambiguïté ou information critique manquante est reportée dans la
     liste "Points à vérifier auprès de l'Équipier Ops" — RIEN n'est deviné.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Espaces de noms OOXML (format .docx)                                        #
# --------------------------------------------------------------------------- #

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _q(tag: str) -> str:
    """Qualifie un nom de balise OOXML avec l'espace de noms 'w:' (ex: 'p' -> '{...}p')."""
    return f"{{{NS['w']}}}{tag}"


# --------------------------------------------------------------------------- #
# Modèle de données                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class Run:
    """Un morceau de texte avec sa mise en forme (utile pour repérer les
    paragraphes "explicatifs" en italique/couleur, et les hyperliens)."""

    text: str
    italic: bool = False
    color: Optional[str] = None          # couleur RRGGBB, ou None/"auto"
    hyperlink_target: Optional[str] = None


@dataclass
class Paragraph:
    """Un paragraphe du document, avec son éventuel niveau de titre."""

    runs: list[Run] = field(default_factory=list)
    heading_level: Optional[int] = None   # 1 = Titre 1 / Heading 1, etc. None = pas un titre

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def is_heading(self) -> bool:
        return self.heading_level is not None

    def is_explanatory(self) -> bool:
        """Heuristique de la règle 2 : un paragraphe purement "explicatif" est
        entièrement en italique ET dans une couleur non standard (souvent
        bleu dans les DEX). Un tel paragraphe est écarté du contenu repris."""
        non_empty = [r for r in self.runs if r.text.strip()]
        if not non_empty:
            return False
        if not all(r.italic for r in non_empty):
            return False
        has_color = any(r.color and r.color.lower() not in ("auto", "000000") for r in non_empty)
        return has_color


@dataclass
class Table:
    """Un tableau du document, représenté ligne par ligne / cellule par cellule."""

    rows: list[list[str]] = field(default_factory=list)

    def to_text(self) -> str:
        lines = []
        for row in self.rows:
            cells = [clean_text(c) for c in row]
            if any(cells):
                lines.append(" | ".join(cells))
        return "\n".join(lines)


# Un "item" de contenu est soit un Paragraph, soit une Table
ContentItem = "Paragraph | Table"


# --------------------------------------------------------------------------- #
# Lecture du fichier .docx (ZIP + XML)                                         #
# --------------------------------------------------------------------------- #

def _resolve_heading_levels(styles_xml: Optional[bytes]) -> dict[str, int]:
    """Construit la table styleId -> niveau de titre (1, 2, 3...) à partir de
    word/styles.xml. Couvre les styles "Heading N" et "Titre N" (Word FR),
    ainsi que les styles personnalisés basés sur ceux-ci (chaîne basedOn)."""

    levels: dict[str, int] = {}
    if not styles_xml:
        return levels

    root = ET.fromstring(styles_xml)
    raw: dict[str, dict] = {}
    for style in root.findall(_q("style")):
        style_id = style.get(_q("styleId"))
        if not style_id:
            continue
        name_el = style.find(_q("name"))
        name = name_el.get(_q("val")) if name_el is not None else ""
        based_on_el = style.find(_q("basedOn"))
        based_on = based_on_el.get(_q("val")) if based_on_el is not None else None
        outline = None
        ppr = style.find(_q("pPr"))
        if ppr is not None:
            outline_el = ppr.find(_q("outlineLvl"))
            if outline_el is not None:
                try:
                    outline = int(outline_el.get(_q("val")))
                except (TypeError, ValueError):
                    outline = None
        raw[style_id] = {"name": name or "", "based_on": based_on, "outline": outline}

    heading_name_re = re.compile(r"^(?:heading|titre)\s*([0-9]+)$", re.IGNORECASE)

    def resolve(style_id: str, seen: set[str]) -> Optional[int]:
        if style_id not in raw or style_id in seen:
            return None
        seen.add(style_id)
        info = raw[style_id]
        if info["outline"] is not None:
            return info["outline"] + 1
        m = heading_name_re.match(info["name"].strip())
        if m:
            return int(m.group(1))
        if info["based_on"]:
            return resolve(info["based_on"], seen)
        return None

    for style_id in raw:
        lvl = resolve(style_id, set())
        if lvl:
            levels[style_id] = lvl

    return levels


def _resolve_relationships(rels_xml: Optional[bytes]) -> dict[str, str]:
    """Construit la table Id -> Target des relations (word/_rels/document.xml.rels),
    nécessaire pour retrouver l'URL cible des hyperliens (w:hyperlink r:id=...)."""

    rels: dict[str, str] = {}
    if not rels_xml:
        return rels
    root = ET.fromstring(rels_xml)
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    for rel in root.findall(f"{{{rel_ns}}}Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            rels[rid] = target
    return rels


_HYPERLINK_INSTR_RE = re.compile(r'HYPERLINK\s+"([^"]+)"', re.IGNORECASE)


def _extract_runs(elem: ET.Element, rels: dict[str, str], hyperlink_target: Optional[str] = None) -> list[Run]:
    """Extrait récursivement les "runs" (w:r) de texte d'un élément (paragraphe,
    hyperlien, cellule de tableau...), en conservant l'italique, la couleur et
    la cible d'hyperlien éventuelle."""

    runs: list[Run] = []
    for child in elem:
        tag = child.tag

        if tag == _q("hyperlink"):
            rid = child.get(f"{{{NS['r']}}}id")
            target = rels.get(rid) if rid else None
            runs.extend(_extract_runs(child, rels, hyperlink_target=target))

        elif tag == _q("fldSimple"):
            instr = child.get(_q("instr"), "")
            m = _HYPERLINK_INSTR_RE.search(instr)
            target = m.group(1) if m else hyperlink_target
            runs.extend(_extract_runs(child, rels, hyperlink_target=target))

        elif tag == _q("r"):
            text_parts: list[str] = []
            italic = False
            color = None
            rpr = child.find(_q("rPr"))
            if rpr is not None:
                if rpr.find(_q("i")) is not None or rpr.find(_q("iCs")) is not None:
                    italic = True
                color_el = rpr.find(_q("color"))
                if color_el is not None:
                    color = color_el.get(_q("val"))
            for sub in child:
                if sub.tag == _q("t"):
                    text_parts.append(sub.text or "")
                elif sub.tag == _q("tab"):
                    text_parts.append("\t")
                elif sub.tag in (_q("br"), _q("cr")):
                    text_parts.append("\n")
                elif sub.tag == _q("instrText"):
                    m = _HYPERLINK_INSTR_RE.search(sub.text or "")
                    if m and hyperlink_target is None:
                        hyperlink_target = m.group(1)
            text = "".join(text_parts)
            if text:
                runs.append(Run(text=text, italic=italic, color=color, hyperlink_target=hyperlink_target))

        else:
            # Autres conteneurs (w:smartTag, w:ins, w:sdt...) : on descend dedans.
            runs.extend(_extract_runs(child, rels, hyperlink_target))

    return runs


def _parse_paragraph(p_elem: ET.Element, rels: dict[str, str], heading_levels: dict[str, int]) -> Paragraph:
    heading_level = None
    ppr = p_elem.find(_q("pPr"))
    if ppr is not None:
        outline_el = ppr.find(_q("outlineLvl"))
        if outline_el is not None:
            try:
                heading_level = int(outline_el.get(_q("val"))) + 1
            except (TypeError, ValueError):
                heading_level = None
        if heading_level is None:
            pstyle = ppr.find(_q("pStyle"))
            if pstyle is not None:
                heading_level = heading_levels.get(pstyle.get(_q("val")))
    runs = _extract_runs(p_elem, rels)
    return Paragraph(runs=runs, heading_level=heading_level)


def _parse_table(tbl_elem: ET.Element, rels: dict[str, str]) -> Table:
    rows: list[list[str]] = []
    for tr in tbl_elem.findall(_q("tr")):
        cells: list[str] = []
        for tc in tr.findall(_q("tc")):
            cell_parts = []
            for p in tc.findall(_q("p")):
                runs = _extract_runs(p, rels)
                cell_parts.append("".join(r.text for r in runs))
            cells.append("\n".join(part for part in cell_parts if part))
        rows.append(cells)
    return Table(rows=rows)


def read_docx(path: str) -> list:
    """Lit un fichier .docx et retourne la liste ordonnée des paragraphes et
    tableaux du corps du document (objets Paragraph / Table)."""

    with zipfile.ZipFile(path) as zf:
        document_xml = zf.read("word/document.xml")
        try:
            rels_xml = zf.read("word/_rels/document.xml.rels")
        except KeyError:
            rels_xml = None
        try:
            styles_xml = zf.read("word/styles.xml")
        except KeyError:
            styles_xml = None

    rels = _resolve_relationships(rels_xml)
    heading_levels = _resolve_heading_levels(styles_xml)

    root = ET.fromstring(document_xml)
    body = root.find(_q("body"))
    if body is None:
        return []

    items: list = []
    for child in body:
        if child.tag == _q("p"):
            items.append(_parse_paragraph(child, rels, heading_levels))
        elif child.tag == _q("tbl"):
            items.append(_parse_table(child, rels))
    return items


# --------------------------------------------------------------------------- #
# Nettoyage du texte (règle 3)                                                 #
# --------------------------------------------------------------------------- #

# Puces issues de polices "symboles" (Wingdings/Symbol), espaces spéciaux,
# caractères de contrôle, etc. -> remplacés par une puce "-" ou supprimés.
_BULLET_CHARS = "•▪●◦‣·"
_BULLET_RE = re.compile(r"^[ \t]*[" + re.escape(_BULLET_CHARS) + r"][ \t]*")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-​-‏]")
_MULTISPACE_RE = re.compile(r"[ \t]+")
_MULTIBLANKLINE_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Nettoie un texte extrait du DEX (règle 3 : caractères parasites) sans
    modifier le sens : normalisation des espaces, suppression des caractères
    de contrôle / icônes de puces de polices symboles, conversion des espaces
    insécables, et compression des lignes vides successives."""

    if text is None:
        return ""

    # Espace insécable / fine -> espace normal
    text = text.replace(" ", " ").replace(" ", " ")

    # Caractères de contrôle / icônes de puces "police symbole"
    text = _CONTROL_CHARS_RE.sub("", text)

    lines = []
    for raw_line in text.splitlines():
        line = _BULLET_RE.sub("- ", raw_line)
        line = _MULTISPACE_RE.sub(" ", line).strip()
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = _MULTIBLANKLINE_RE.sub("\n\n", cleaned)
    return cleaned.strip()


# --------------------------------------------------------------------------- #
# Repérage des sections (règle 1 : par nom, pas par numéro)                   #
# --------------------------------------------------------------------------- #

def _normalize_heading(text: str) -> str:
    """Normalise un titre pour la comparaison : enlève la numérotation
    ("2.1", "12.3.", "4.2.2 - "), les accents, la ponctuation, et met en
    minuscules."""

    # Retire un préfixe de numérotation type "2.1", "12.3.4)", "Annexe 1 -"
    text = re.sub(r"^\s*([0-9]+\.)*[0-9]+[.)\-\s]*", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = _MULTISPACE_RE.sub(" ", text).strip()
    return text


def _heading_matches(normalized_heading: str, keywords: list[str]) -> bool:
    """Un mot-clé correspond au titre normalisé :
    - mot-clé composé de plusieurs mots (ex: "architecture fonctionnelle
      applicative") : simple inclusion de la phrase ;
    - mot-clé d'un seul mot (ex: "servitude", "certificat", "log") : un mot
      du titre doit COMMENCER par ce mot-clé (gère le singulier/pluriel :
      "servitude" matche "servitudes"), ce qui évite par ailleurs les faux
      positifs par sous-chaîne (ex: "log" ne matche pas "metrologie", car
      aucun mot de "metrologie" ne commence par "log")."""

    words = normalized_heading.split()
    for kw in keywords:
        kw_words = kw.split()
        if len(kw_words) == 1:
            if any(w.startswith(kw) for w in words):
                return True
        elif kw in normalized_heading:
            return True
    return False


def find_section(
    items: list,
    keywords: list[str],
    *,
    start_after: int = 0,
) -> Optional[tuple[int, int, int]]:
    """Cherche, à partir de l'index `start_after`, le premier titre dont le
    texte normalisé contient un des `keywords`.

    Retourne (index_du_titre, index_de_debut_contenu, index_de_fin_exclu)
    où la fin est le prochain titre de niveau <= au titre trouvé (ou la fin
    du document). Retourne None si aucun titre ne correspond.
    """

    for i in range(start_after, len(items)):
        item = items[i]
        if isinstance(item, Paragraph) and item.is_heading:
            if _heading_matches(_normalize_heading(item.text), keywords):
                level = item.heading_level
                end = len(items)
                for j in range(i + 1, len(items)):
                    nxt = items[j]
                    if isinstance(nxt, Paragraph) and nxt.is_heading and nxt.heading_level <= level:
                        end = j
                        break
                return i, i + 1, end
    return None


def section_text(items: list, start: int, end: int) -> str:
    """Concatène le contenu utile (paragraphes non explicatifs + tableaux)
    entre deux index, nettoyé (règles 2 et 3). Les sous-titres rencontrés
    sont conservés (ils font partie du contenu utile d'un chapitre entier,
    ex: "Supervision")."""

    parts: list[str] = []
    for item in items[start:end]:
        if isinstance(item, Paragraph):
            if item.is_explanatory():
                continue
            text = item.text.strip()
            if not text:
                continue
            cleaned = clean_text(text)
            if cleaned:
                parts.append(cleaned)
        elif isinstance(item, Table):
            table_text = item.to_text()
            if table_text:
                parts.append(table_text)
    return "\n".join(parts).strip()


def section_links(items: list, start: int, end: int, text_pattern: Optional[re.Pattern] = None) -> list[str]:
    """Extrait uniquement les hyperliens (et, si `text_pattern` est fourni,
    les références textuelles correspondantes, ex: "DAP1234", "ADU5678")
    présents entre deux index. Utilisé pour les champs "LIEN UNIQUEMENT"
    (Dossier Archi / Schéma Applicatif)."""

    links: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            links.append(value)

    for item in items[start:end]:
        if not isinstance(item, Paragraph):
            continue
        for run in item.runs:
            if run.hyperlink_target:
                add(run.hyperlink_target)
            if text_pattern:
                for m in text_pattern.finditer(run.text):
                    add(m.group(0))
    return links


# --------------------------------------------------------------------------- #
# Définition des champs CAST'IN (règles métier du prompt de reprise)          #
# --------------------------------------------------------------------------- #

# Chaque champ est décrit par :
#   key        : identifiant interne
#   label      : libellé exact du champ CAST'IN (utilisé dans la sortie)
#   tab        : onglet CAST'IN ("Description détaillée" ou "DEX")
#   kind       : "text" | "link" | "empty" | "merge"
#   keywords   : mots-clés (normalisés) des titres de section source
#   hint       : indication du numéro de chapitre dans le DEX (~), pour info
#                 uniquement (NE PAS chercher par numéro, cf règle 1)
#   none_value : valeur si la section est absente ("Non concerné" sauf cas
#                 particuliers prévus par le prompt)
#   optional   : champ optionnel (Informations supplémentaires)

CASTIN_FIELDS = [
    # ---- Onglet "Description détaillée" -----------------------------------
    {
        "key": "lien_dossier_archi",
        "label": "Lien Dossier Archi (DAP…)",
        "tab": "Description détaillée",
        "kind": "link",
        "keywords": ["architecture fonctionnelle applicative"],
        "link_pattern": re.compile(r"\bDAP[0-9A-Z\-]*\b"),
        "hint": "~2.2 Architecture fonctionnelle & applicative",
        "none_value": "Non concerné",
    },
    {
        "key": "schema_applicatif",
        "label": "Schéma Applicatif (ADU…)",
        "tab": "Description détaillée",
        "kind": "link",
        "keywords": ["architecture fonctionnelle applicative", "description de la solution"],
        "link_pattern": re.compile(r"\bADU[0-9A-Z\-]*\b"),
        "hint": "~2.2 (ou ~2.1) Architecture fonctionnelle & applicative / Description de la solution",
        "none_value": "Non concerné",
    },
    {
        "key": "description_fonctionnelle",
        "label": "Description Fonctionnelle",
        "tab": "Description détaillée",
        "kind": "text",
        "keywords": ["description de la solution"],
        "hint": "~2.1 Description de la solution",
        "none_value": "Non concerné",
    },
    {
        "key": "donnees_solution",
        "label": "Données de la solution",
        "tab": "Description détaillée",
        "kind": "text",
        "keywords": ["donnees"],
        "hint": "~2.3 Données",
        "none_value": "Non concerné",
    },
    {
        "key": "principes_decisions",
        "label": "Principes et décisions",
        "tab": "Description détaillée",
        "kind": "empty",
        "keywords": [],
        "hint": "Champ volontairement vide (règle 5)",
        "none_value": "",
    },
    {
        "key": "description_technique",
        "label": "Description Technique",
        "tab": "Description détaillée",
        "kind": "text",
        "keywords": ["architecture technique"],
        "hint": "~4.1 Architecture technique",
        "none_value": "Non concerné",
    },
    # ---- Onglet "DEX" -------------------------------------------------------
    {
        "key": "plage_fonctionnement",
        "label": "Plage de fonctionnement / maintenance",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["plage de fonctionnement", "plages de fonctionnement"],
        "hint": "~3.3 Plages de fonctionnement",
        "none_value": "Non concerné",
    },
    {
        "key": "supervision",
        "label": "Supervision",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["supervision"],
        "hint": "~6 Supervision (chapitre entier)",
        "none_value": "Non concerné",
    },
    {
        "key": "observabilite",
        "label": "Observabilité",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["metrologie"],
        "hint": "~9 ou ~11 Métrologie",
        "none_value": "Non concerné",
    },
    {
        "key": "log",
        "label": "Log",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["diagnostic", "diagnostique", "log", "trace"],
        "hint": "~8.2 Diagnostique / LOG / Trace",
        "none_value": "Non concerné",
    },
    {
        "key": "sauvegardes",
        "label": "Sauvegardes",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["sauvegarde"],
        "hint": "~7 Sauvegarde",
        "none_value": "Non concerné",
    },
    {
        "key": "servitudes",
        "label": "Servitudes et ordonnancements",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["servitude"],
        "hint": "~9 Servitudes (si absent -> Non concerné)",
        "none_value": "Non concerné",
    },
    {
        "key": "comptes_services",
        "label": "Comptes et services",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["compte de service", "comptes de service"],
        "hint": "~12.2 Compte de service",
        "none_value": "Non concerné",
    },
    {
        "key": "certificats",
        "label": "Certificats",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["certificat"],
        "hint": "~12.3 Certificats",
        "none_value": "Non concerné",
    },
    {
        "key": "liste_blanche",
        "label": "Liste blanche",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["liste blanche", "whitelist"],
        "hint": "~12.4",
        "none_value": "Non concerné",
    },
    {
        "key": "flux",
        "label": "Flux",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["flux et interdependance", "flux et interdependances"],
        "hint": "~4.3 Flux et interdépendances",
        "none_value": "Non concerné",
    },
    {
        "key": "support",
        "label": "Support",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["matrice de responsabilite", "matrice des responsabilites", "raci"],
        "hint": "~8.1 Matrice responsabilité",
        "none_value": "Non concerné",
    },
    {
        "key": "changement_mep",
        "label": "Changement et MEP",
        "tab": "DEX",
        "kind": "merge",
        "keywords": ["controle des operations", "changements et mep", "changement et mep"],
        "hint": "~10 Contrôle des opérations + ~5 Changements et MEP",
        "none_value": "Non concerné",
    },
    {
        "key": "matiere_repo",
        "label": "Matière (repo)",
        "tab": "DEX",
        "kind": "merge",
        "keywords": ["referentiel", "repository", "depot de code", "matiere"],
        "extra_search": re.compile(r"merge request", re.IGNORECASE),
        "hint": "~5.1 + recherche \"Merge Request\"",
        "none_value": "Non concerné",
    },
    {
        "key": "procedure_restauration",
        "label": "Procédure de restauration",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["restauration"],
        "hint": "~13.1 Restauration",
        "none_value": "Non concerné",
    },
    {
        "key": "procedure_reconstruction",
        "label": "Procédure de reconstruction",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["reconstruction"],
        "hint": "~13.2 Reconstruction",
        "none_value": "Non concerné",
    },
    {
        "key": "procedure_resynchronisation",
        "label": "Procédure de resynchronisation",
        "tab": "DEX",
        "kind": "text",
        "keywords": ["resynchronisation"],
        "hint": "~13.3 Resynchronisation",
        "none_value": "Non concerné",
    },
    {
        "key": "informations_supplementaires",
        "label": "Informations supplémentaires",
        "tab": "DEX",
        "kind": "appendix",
        "keywords": ["assets mainframe"],
        "hint": "Contenu après ~13.3 + ~4.2.2 Assets mainframe (optionnel)",
        "none_value": "",
        "optional": True,
    },
]


# --------------------------------------------------------------------------- #
# Identification (numéro de solution, auteur, responsable)                    #
# --------------------------------------------------------------------------- #

_SOLUTION_RE = re.compile(r"(?<![A-Za-z0-9])S\d{4,6}(?!\d)")


def extract_identification(items: list, filename: str) -> dict:
    """Extrait le numéro de solution (Sxxxx), l'auteur (page de garde) et le
    responsable (page 2, ou nom du service si absent)."""

    result = {"solution": None, "auteur": None, "responsable": None}
    notes: list[str] = []

    # Numéro de solution : nom de fichier en priorité, sinon contenu du document.
    m = _SOLUTION_RE.search(filename or "")
    if m:
        result["solution"] = m.group(0)
    else:
        for item in items[:60]:
            if isinstance(item, Paragraph):
                m = _SOLUTION_RE.search(item.text)
                if m:
                    result["solution"] = m.group(0)
                    break
        if not result["solution"]:
            notes.append(
                "Numéro de solution (Sxxxx) introuvable dans le nom de fichier ni dans "
                "le début du document — à confirmer."
            )

    # Auteur : page de garde -> on cherche un paragraphe "Auteur : ..." dans le
    # tout début du document (avant le premier titre).
    first_heading = next((i for i, it in enumerate(items) if isinstance(it, Paragraph) and it.is_heading), len(items))
    cover_items = items[:first_heading]

    auteur = _find_labelled_value(cover_items, [r"auteur"])
    if auteur:
        result["auteur"] = auteur
    else:
        notes.append("Auteur du DEX introuvable sur la page de garde — à confirmer.")

    # Responsable : page 2 (on cherche jusqu'au 2e titre rencontré, large mais sûr).
    responsable_scope = items[:first_heading]
    for i, it in enumerate(items):
        if isinstance(it, Paragraph) and it.is_heading:
            responsable_scope = items[: i + 1]
            break

    responsable = _find_labelled_value(items[:60], [r"responsable"])
    if responsable:
        result["responsable"] = responsable
    else:
        service = _find_labelled_value(items[:60], [r"service"])
        if service:
            result["responsable"] = service
            notes.append("Responsable absent : nom du service repris à la place (à confirmer).")
        else:
            notes.append("Responsable (ou nom du service) introuvable en page 2 — à confirmer.")

    return {"values": result, "notes": notes}


def _find_labelled_value(items: list, label_patterns: list[str]) -> Optional[str]:
    """Cherche un paragraphe de la forme "Label : valeur" (ou "Label\\tvaleur")
    et retourne la valeur nettoyée."""

    for pattern in label_patterns:
        regex = re.compile(rf"^\s*{pattern}\s*[:\t]\s*(.+)$", re.IGNORECASE)
        for item in items:
            if isinstance(item, Paragraph):
                text = item.text.strip()
                m = regex.match(text)
                if m:
                    value = clean_text(m.group(1))
                    if value:
                        return value
    return None


# --------------------------------------------------------------------------- #
# Traitement complet                                                           #
# --------------------------------------------------------------------------- #

def process_dex(path: str, filename: Optional[str] = None) -> dict:
    """Traite un fichier DEX .docx et retourne un dictionnaire :

    {
      "identification": {"solution": ..., "auteur": ..., "responsable": ...},
      "champs": {champ_key: {"label", "tab", "content"}, ...},
      "points_a_verifier": [str, ...],
    }

    Conforme aux règles du prompt de reprise DEX -> CAST'IN.
    """

    filename = filename or path
    items = read_docx(path)

    points_a_verifier: list[str] = []

    ident = extract_identification(items, filename)
    points_a_verifier.extend(ident["notes"])

    champs: dict[str, dict] = {}

    for fdef in CASTIN_FIELDS:
        key = fdef["key"]
        label = fdef["label"]
        kind = fdef["kind"]

        if kind == "empty":
            # Règle 5 : "Principes et décisions" reste vide.
            champs[key] = {"label": label, "tab": fdef["tab"], "content": ""}
            continue

        if kind == "link":
            content, found = _extract_link_field(items, fdef)
        elif kind == "merge":
            content, found = _extract_merge_field(items, fdef)
        elif kind == "appendix":
            content, found = _extract_appendix_field(items, fdef)
        else:
            content, found = _extract_text_field(items, fdef)

        if not content:
            content = fdef["none_value"]
            if not fdef.get("optional") and not found:
                points_a_verifier.append(
                    f"Champ « {label} » : section source introuvable "
                    f"({fdef['hint']}) -> mis à \"{fdef['none_value'] or '(vide)'}\", à vérifier."
                )

        champs[key] = {"label": label, "tab": fdef["tab"], "content": content}

    return {
        "identification": ident["values"],
        "champs": champs,
        "points_a_verifier": points_a_verifier,
    }


def _extract_text_field(items: list, fdef: dict) -> tuple[str, bool]:
    section = find_section(items, fdef["keywords"])
    if section is None:
        return "", False
    _, start, end = section
    return section_text(items, start, end), True


def _extract_link_field(items: list, fdef: dict) -> tuple[str, bool]:
    """Champ "LIEN UNIQUEMENT" : peut être indiqué par le prompt dans
    plusieurs sections candidates (ex: ADU dans "Architecture fonctionnelle &
    applicative" OU "Description de la solution"). On parcourt TOUTES les
    sections correspondant aux mots-clés et on agrège les liens trouvés."""

    links: list[str] = []
    found_any = False
    cursor = 0
    while True:
        section = find_section(items, fdef["keywords"], start_after=cursor)
        if section is None:
            break
        _, start, end = section
        found_any = True
        for link in section_links(items, start, end, fdef.get("link_pattern")):
            if link not in links:
                links.append(link)
        cursor = end
    return "\n".join(links), found_any


def _extract_merge_field(items: list, fdef: dict) -> tuple[str, bool]:
    """Champ composé de plusieurs sections (ex: "Changement et MEP" =
    "Contrôle des opérations" + "Changements et MEP"), avec recherche
    additionnelle optionnelle (ex: "Merge Request" pour "Matière (repo)")."""

    parts: list[str] = []
    found_any = False

    section = find_section(items, fdef["keywords"])
    if section is not None:
        _, start, end = section
        text = section_text(items, start, end)
        if text:
            parts.append(text)
        found_any = True
        # Cherche une deuxième section distincte après la première (cas
        # "Changement et MEP" = deux chapitres séparés).
        second = find_section(items, fdef["keywords"], start_after=end)
        if second is not None:
            _, start2, end2 = second
            text2 = section_text(items, start2, end2)
            if text2:
                parts.append(text2)

    extra_pattern: Optional[re.Pattern] = fdef.get("extra_search")
    if extra_pattern is not None:
        extra_lines = []
        for item in items:
            if isinstance(item, Paragraph) and not item.is_heading and not item.is_explanatory():
                if extra_pattern.search(item.text):
                    cleaned = clean_text(item.text)
                    if cleaned:
                        extra_lines.append(cleaned)
        if extra_lines:
            parts.append("Références \"Merge Request\" trouvées dans le document :\n" + "\n".join(extra_lines))
            found_any = True

    return "\n\n".join(p for p in parts if p).strip(), found_any


def _extract_appendix_field(items: list, fdef: dict) -> tuple[str, bool]:
    """"Informations supplémentaires" (optionnel) = contenu situé après la
    section "Resynchronisation" (~13.3) + section "Assets mainframe" (~4.2.2)
    si elle existe ailleurs dans le document."""

    parts: list[str] = []
    found_any = False

    resync = find_section(items, ["resynchronisation"])
    if resync is not None:
        _, _, end = resync
        tail_items = items[end:]
        tail_text = section_text(tail_items, 0, len(tail_items))
        if tail_text:
            parts.append(tail_text)
            found_any = True

    mainframe = find_section(items, fdef["keywords"])
    if mainframe is not None:
        _, start, end = mainframe
        text = section_text(items, start, end)
        if text:
            parts.append("Assets mainframe :\n" + text)
            found_any = True

    return "\n\n".join(p for p in parts if p).strip(), found_any


# --------------------------------------------------------------------------- #
# Mise en forme de la sortie                                                   #
# --------------------------------------------------------------------------- #

def format_markdown(result: dict) -> str:
    """Produit les trois blocs de sortie attendus par le prompt de reprise."""

    lines: list[str] = []
    ident = result["identification"]

    lines.append("## 1. IDENTIFICATION")
    lines.append(f"Solution : {ident.get('solution') or 'Non concerné'}")
    lines.append(f"Auteur : {ident.get('auteur') or 'Non concerné'}")
    lines.append(f"Responsable : {ident.get('responsable') or 'Non concerné'}")
    lines.append("")

    lines.append("## 2. CONTENU PAR CHAMP CAST'IN")
    for fdef in CASTIN_FIELDS:
        champ = result["champs"][fdef["key"]]
        lines.append(f"**[{champ['label']}]**")
        if fdef["kind"] == "empty":
            lines.append("(laisser vide)")
        else:
            lines.append(champ["content"] or "Non concerné")
        lines.append("")

    lines.append("## 3. POINTS À VÉRIFIER AUPRÈS DE L'ÉQUIPIER OPS")
    points = result["points_a_verifier"]
    if points:
        for p in points:
            lines.append(f"- {p}")
    else:
        lines.append("RAS")

    return "\n".join(lines)


def to_json(result: dict) -> dict:
    """Représentation JSON (utilisée par le serveur Office.js) : un
    dictionnaire {champ_key: {label, tab, content}} + identification +
    points à vérifier + rendu markdown complet."""

    return {
        "identification": result["identification"],
        "champs": result["champs"],
        "points_a_verifier": result["points_a_verifier"],
        "markdown": format_markdown(result),
    }
