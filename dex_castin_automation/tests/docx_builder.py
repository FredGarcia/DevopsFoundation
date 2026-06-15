#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_builder.py — Petit constructeur de fichiers .docx pour les tests.

Permet de fabriquer, à partir de Python, des fichiers .docx minimalistes
(paragraphes avec niveaux de titre, italique/couleur, hyperliens, tableaux)
sans dépendance externe (uniquement zipfile + chaînes XML), afin de générer
des DEX de test pour dex_castin_common.process_dex().
"""

from __future__ import annotations

import html
import zipfile
from dataclasses import dataclass, field


W_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

PACKAGE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

# Styles "Titre 1" à "Titre 4" (avec outlineLvl, comme les styles Word
# standards) + un style "TitrePerso" SANS outlineLvl et dont le nom ne
# correspond pas au motif "heading N" / "titre N" : ce style ne sera PAS
# reconnu comme un titre par dex_castin_common -> utile pour simuler un
# faux négatif (section présente mais non détectée).
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Titre1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Titre2"><w:name w:val="heading 2"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Titre3"><w:name w:val="heading 3"/><w:pPr><w:outlineLvl w:val="2"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Titre4"><w:name w:val="heading 4"/><w:pPr><w:outlineLvl w:val="3"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="TitrePerso"><w:name w:val="Style perso"/></w:style>
</w:styles>"""


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


@dataclass
class DocxBuilder:
    """Accumule le corps du document et les relations (hyperliens), puis
    écrit un fichier .docx valide."""

    body_parts: list[str] = field(default_factory=list)
    relationships: list[tuple[str, str]] = field(default_factory=list)  # (rId, target)
    _rid_counter: int = 1

    def _next_rid(self) -> str:
        rid = f"rId{self._rid_counter}"
        self._rid_counter += 1
        return rid

    # -- Construction de contenu --------------------------------------------

    def heading(self, text: str, level: int) -> "DocxBuilder":
        """Ajoute un titre de niveau `level` (1 à 4), avec le style "TitreN"."""
        style = f"Titre{level}"
        self.body_parts.append(
            f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>'
        )
        return self

    def heading_unstyled(self, text: str) -> "DocxBuilder":
        """Ajoute un "titre visuel" qui n'est PAS reconnu comme titre par
        l'outil (style "TitrePerso", sans outlineLvl ni nom "Heading/Titre N").
        Simule un DEX dont la mise en forme ne suit pas les styles Word
        standards -> faux négatif attendu (section non détectée)."""
        self.body_parts.append(
            f'<w:p><w:pPr><w:pStyle w:val="TitrePerso"/></w:pPr>'
            f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>'
        )
        return self

    def para(self, text: str, *, italic: bool = False, color: str | None = None) -> "DocxBuilder":
        """Ajoute un paragraphe de texte normal (ou italique/coloré)."""
        rpr = ""
        if italic or color:
            rpr = "<w:rPr>"
            if italic:
                rpr += "<w:i/>"
            if color:
                rpr += f'<w:color w:val="{color}"/>'
            rpr += "</w:rPr>"
        self.body_parts.append(f'<w:p><w:r>{rpr}<w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>')
        return self

    def hyperlink_para(self, text: str, url: str) -> "DocxBuilder":
        """Ajoute un paragraphe constitué d'un hyperlien externe."""
        rid = self._next_rid()
        self.relationships.append((rid, url))
        self.body_parts.append(
            f'<w:p><w:hyperlink r:id="{rid}"><w:r><w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:hyperlink></w:p>'
        )
        return self

    def table(self, rows: list[list[str]]) -> "DocxBuilder":
        """Ajoute un tableau simple (liste de lignes de cellules texte)."""
        tr_parts = []
        for row in rows:
            tc_parts = []
            for cell in row:
                tc_parts.append(
                    f'<w:tc><w:p><w:r><w:t xml:space="preserve">{_esc(cell)}</w:t></w:r></w:p></w:tc>'
                )
            tr_parts.append(f"<w:tr>{''.join(tc_parts)}</w:tr>")
        self.body_parts.append(f"<w:tbl>{''.join(tr_parts)}</w:tbl>")
        return self

    # -- Écriture -------------------------------------------------------------

    def write(self, path: str) -> None:
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f"<w:document {W_NS}><w:body>{''.join(self.body_parts)}</w:body></w:document>"
        )

        rels_entries = "".join(
            f'<Relationship Id="{rid}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            f'Target="{target}" TargetMode="External"/>'
            for rid, target in self.relationships
        )
        document_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{rels_entries}</Relationships>"
        )

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", CONTENT_TYPES)
            zf.writestr("_rels/.rels", PACKAGE_RELS)
            zf.writestr("word/document.xml", document_xml)
            zf.writestr("word/styles.xml", STYLES)
            zf.writestr("word/_rels/document.xml.rels", document_rels)
