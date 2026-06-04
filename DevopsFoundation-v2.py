#!/usr/bin/env python3
"""
auditaccess-builder-v2.py
Variante Linux/Cross-platform du builder original.
Parcourt l'arborescence du projet et génère un fichier .cmd auto-décompressable.
Le .cmd est strictement identique à celui produit sur Windows.
"""
import os
import sys
import hashlib
import base64
from pathlib import Path

PROJECT_ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
OUTPUT_CMD   = sys.argv[2] if len(sys.argv) > 2 else "auditaccess-rebuild-v2.cmd"
EXCLUDED_DIRS  = {".git", ".vscode", "target", "__pycache__"}
EXCLUDED_FILES = {"mvnw", "mvnw.cmd", OUTPUT_CMD, Path(__file__).name}


def sha256_of_bytes(data):
    return hashlib.sha256(data).hexdigest()


def escape_line_for_cmd(line):
    """Échappement intelligent (identique à l'original) :
    - hors guillemets : & | < > sont préfixés par ^
    - dans les guillemets : pas d'échappement
    - % est doublé partout
    """
    line = line.replace("%", "%%")
    result = []
    in_quote = False
    for char in line:
        if char == '"':
            in_quote = not in_quote
            result.append(char)
        elif char in "&|<>":
            result.append(char if in_quote else '^' + char)
        elif char == '^':
            result.append(char if in_quote else '^^')
        else:
            result.append(char)
    return "".join(result)


def writeln(cmd, text):
    cmd.write(text + "\r\n")


def generate_cmd():
    project_root = Path(PROJECT_ROOT).resolve()
    output_path = Path(OUTPUT_CMD).resolve()
    script_name = Path(__file__).name

    with open(output_path, "w", encoding="utf-8-sig", newline="\r\n") as cmd:
        writeln(cmd, "@echo off")
        writeln(cmd, "setlocal disabledelayedexpansion")
        writeln(cmd, "echo ================================================")
        writeln(cmd, "echo   RECONSTRUCTION DU PROJET CYBERAUDIT7E v2")
        writeln(cmd, "echo   (Preconisation + Tickets ServiceNow par regle)")
        writeln(cmd, "echo ================================================")
        writeln(cmd, "echo.")

        # ── 1) Création des dossiers ──
        for root, dirs, files in os.walk(project_root):
            rel_root = Path(root).relative_to(project_root)
            dirs[:] = sorted([d for d in dirs if d not in EXCLUDED_DIRS])
            for d in dirs:
                dir_path = (rel_root / d) if str(rel_root) != '.' else Path(d)
                # Format Windows
                win_path = str(dir_path).replace("/", "\\")
                writeln(cmd, f'if not exist "{win_path}" mkdir "{win_path}"')

        # ── 2) Écriture des fichiers ──
        for root, dirs, files in os.walk(project_root):
            rel_root = Path(root).relative_to(project_root)
            dirs[:] = sorted([d for d in dirs if d not in EXCLUDED_DIRS])

            for file in sorted(files):
                if file in EXCLUDED_FILES or file == script_name or file == output_path.name:
                    continue

                file_path = Path(root) / file
                rel_path = file_path.relative_to(project_root)
                win_rel_path = str(rel_path).replace("/", "\\")

                with open(file_path, 'rb') as f:
                    data = f.read()

                expected_hash = sha256_of_bytes(data)
                cmd.write(f'echo Decompression de {win_rel_path}\r\n')

                try:
                    content = data.decode('utf-8')
                    # ── Fichier texte ──
                    lines = content.splitlines()
                    if not lines:
                        cmd.write(f'type nul > "{win_rel_path}"\r\n')
                    else:
                        first = True
                        for line in lines:
                            safe_line = escape_line_for_cmd(line)
                            prefix = '>' if first else '>>'
                            writeln(cmd, f'{prefix} "{win_rel_path}" echo({safe_line}')
                            first = False
                except UnicodeDecodeError:
                    # ── Fichier binaire ──
                    print(f"[BINAIRE] {rel_path}", file=sys.stderr)
                    b64_content = base64.b64encode(data).decode('ascii')
                    tmp_b64 = "tmp_b64_payload.txt"
                    writeln(cmd, f'type nul > "{tmp_b64}"')
                    chunk_size = 2000
                    for i in range(0, len(b64_content), chunk_size):
                        chunk = b64_content[i:i + chunk_size]
                        writeln(cmd, f'>> "{tmp_b64}" echo({chunk}')
                    writeln(cmd, f'certutil -decode "{tmp_b64}" "{win_rel_path}" >nul')
                    writeln(cmd, f'del "{tmp_b64}"')

                # SHA-256 verification
                writeln(cmd, f'certutil -hashfile "{win_rel_path}" SHA256 | findstr /I /C:"{expected_hash.upper()}" >nul')
                writeln(cmd, f'if %errorlevel%==0 (echo    [OK] {win_rel_path}) else (echo    [ERREUR] {win_rel_path})')

        # ── Fin ──
        writeln(cmd, "echo.")
        writeln(cmd, "echo Reconstruction terminee.")
        writeln(cmd, "echo Lancer ensuite : mvnw.cmd spring-boot:run")
        writeln(cmd, "pause")

    print(f"[OK] {output_path} genere", file=sys.stderr)


def cleanup_blank_lines():
    with open(OUTPUT_CMD, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    clean = [l for l in lines if l.strip() != ""]
    with open(OUTPUT_CMD, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.writelines(clean)


if __name__ == "__main__":
    generate_cmd()
    cleanup_blank_lines()
    print(f"[OK] {OUTPUT_CMD} compacte", file=sys.stderr)
