#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dex_castin_cli.py — Reprise DEX -> CAST'IN, en ligne de commande (autonome).

USAGE (Windows "DOS" / invite de commandes, Linux, macOS) :

    python dex_castin_cli.py "C:\\dossiers\\DEX_S12345_MaSolution.docx"

    python dex_castin_cli.py DEX_S12345.docx -o resultat.md
    python dex_castin_cli.py DEX_S12345.docx --json resultat.json
    python dex_castin_cli.py *.docx --out-dir ./sorties

Pour chaque fichier .docx fourni, ce script :
  1. lit le DEX (.docx) avec dex_castin_common.process_dex(),
  2. affiche à l'écran les trois blocs attendus par le prompt de reprise
     (IDENTIFICATION / CONTENU PAR CHAMP CAST'IN / POINTS À VÉRIFIER),
  3. écrit le résultat dans un fichier .md (et, sur demande, .json) prêt à
     être consulté pendant la saisie dans CAST'IN.

Ce script ne dépend QUE de la bibliothèque standard (argparse, pathlib, json)
et du module commun dex_castin_common.py, situé dans le même dossier.
"""

import argparse
import json
import sys
from pathlib import Path

# Le module commun doit être dans le même dossier que ce script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dex_castin_common as dex  # noqa: E402


def process_one(docx_path: Path, out_dir: Path | None, write_json: bool) -> int:
    """Traite un fichier DEX et écrit les sorties associées.

    Retourne le nombre de "points à vérifier" détectés (0 = aucun doute,
    utile comme indicateur dans le résumé final)."""

    print(f"\n{'=' * 70}")
    print(f"DEX : {docx_path}")
    print("=" * 70)

    try:
        result = dex.process_dex(str(docx_path), filename=docx_path.name)
    except Exception as exc:  # noqa: BLE001 - on veut un message clair pour l'utilisateur
        print(f"[ERREUR] Impossible de traiter '{docx_path}' : {exc}")
        return -1

    markdown = dex.format_markdown(result)
    print(markdown)

    target_dir = out_dir if out_dir is not None else docx_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    md_path = target_dir / (docx_path.stem + "_CASTIN.md")
    md_path.write_text(markdown, encoding="utf-8")
    print(f"\n--> Rendu Markdown écrit dans : {md_path}")

    if write_json:
        json_path = target_dir / (docx_path.stem + "_CASTIN.json")
        json_path.write_text(
            json.dumps(dex.to_json(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"--> Rendu JSON écrit dans      : {json_path}")

    return len(result["points_a_verifier"])


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reprise d'un ou plusieurs DEX (.docx) vers le format CAST'IN, "
            "selon les règles du prompt de reprise DEX -> CAST'IN."
        )
    )
    parser.add_argument(
        "fichiers",
        nargs="+",
        help="Un ou plusieurs fichiers DEX au format .docx (les motifs comme *.docx "
        "sont développés par l'invite de commandes elle-même sous Linux/macOS ; "
        "sous Windows, ce script les développe lui-même si nécessaire).",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=None,
        help="Dossier de sortie pour les fichiers générés (*_CASTIN.md / .json). "
        "Par défaut : même dossier que le fichier source.",
    )
    parser.add_argument(
        "--json",
        dest="write_json",
        action="store_true",
        help="Génère en plus un fichier *_CASTIN.json (utile pour un traitement automatisé).",
    )
    return parser


def expand_inputs(patterns: list[str]) -> list[Path]:
    """Sous Windows (DOS), l'invite de commandes ne développe pas les motifs
    comme '*.docx' : on le fait nous-mêmes via Path.glob()."""

    paths: list[Path] = []
    for pattern in patterns:
        p = Path(pattern)
        if any(ch in pattern for ch in "*?[]"):
            base = p.parent if p.parent != Path("") else Path(".")
            paths.extend(sorted(base.glob(p.name)))
        else:
            paths.append(p)
    return paths


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    files = expand_inputs(args.fichiers)

    if not files:
        print("Aucun fichier trouvé.", file=sys.stderr)
        return 2

    total_points = 0
    errors = 0

    for f in files:
        if not f.exists():
            print(f"[ERREUR] Fichier introuvable : {f}", file=sys.stderr)
            errors += 1
            continue
        if f.suffix.lower() != ".docx":
            print(f"[AVERTISSEMENT] '{f}' n'est pas un fichier .docx, ignoré.", file=sys.stderr)
            continue

        nb_points = process_one(f, args.out_dir, args.write_json)
        if nb_points < 0:
            errors += 1
        else:
            total_points += nb_points

    print(f"\n{'=' * 70}")
    print(f"Terminé. {len(files) - errors} fichier(s) traité(s), {total_points} point(s) à vérifier au total.")
    if errors:
        print(f"{errors} fichier(s) en erreur.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
