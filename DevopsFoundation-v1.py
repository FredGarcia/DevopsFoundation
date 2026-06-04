# Script Python qui parcourt l’intégralité du projet Java, lit chaque fichier source et ressource, 
# puis génère un unique fichier de commande Windows (.cmd). 
# Ce fichier .cmd doit contenir, sous forme concaténée et encodée, tout le contenu du projet, 
# et être capable de recréer fidèlement l’arborescence et tous les fichiers du projet Java original. 
# En résumé: un seul fichier .cmd autonome qui permet de redéployer le projet source depuis zéro.
# Script Python qui parcourt l’intégralité du projet Java, lit chaque fichier source et ressource, 
# puis génère un unique fichier de commande Windows (.cmd).
import os
import hashlib
import base64
from pathlib import Path

# Configuration du projet
PROJECT_ROOT = "."
OUTPUT_CMD = "auditaccess-rebuild.cmd"
EXCLUDED_DIRS = {".git", ".vscode", "target"}
EXCLUDED_FILES = {"mvnw", "mvnw.cmd", OUTPUT_CMD}
# line = line.replace("(r.trend^|^|'first')","(r.trend||'first')")
# ============== Fonctions utilitaires ==============

def sha256_of_bytes(data):
    return hashlib.sha256(data).hexdigest()

def escape_line_for_cmd(line):
    """
    Échappement intelligent pour le batch.
    Analyse la ligne pour détecter si on est entre guillemets.
    - Hors guillemets : & doit devenir ^& (pour ne pas casser la commande echo).
    - Entre guillemets : & reste & (sinon le ^ apparait dans le fichier final).
    """
    # Le pourcentage est toujours doublé
    line = line.replace("%", "%%")
    
    result = []
    in_quote = False
    
    for char in line:
        if char == '"':
            # On bascule l'état "entre guillemets"
            in_quote = not in_quote
            result.append(char)
        elif char in "&|<>":
            if in_quote:
                # Entre guillemets : on laisse tel quel (protégé par les quotes)
                result.append(char)
            else:
                # Hors guillemets : on échappe avec ^
                result.append('^' + char)
        elif char == '^':
            if in_quote:
                # Entre guillemets : ^ est un caractère littéral
                result.append(char)
            else:
                # Hors guillemets : on double le caret pour l'afficher
                result.append('^^')
        else:
            result.append(char)
            
    return "".join(result)

def writeln(cmd, text):
    cmd.write(text + "\r\n")

# ============== Génération du fichier .cmd ==============

def generate_cmd():
    script_name = Path(__file__).name
    original_hashes = {}

    with open(OUTPUT_CMD, "w", encoding="utf-8-sig", newline="\r\n") as cmd:
        writeln(cmd, "@echo off")
        writeln(cmd, "setlocal disabledelayedexpansion")
        writeln(cmd, "echo ================================================")
        writeln(cmd, "echo   RECONSTRUCTION DU PROJET JAVA")
        writeln(cmd, "echo ================================================")
        writeln(cmd, "echo.")

        # Création des dossiers
        for root, dirs, files in os.walk(PROJECT_ROOT):
            rel_root = Path(root).relative_to(PROJECT_ROOT)
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for d in dirs:
                dir_path = os.path.join(rel_root, d) if rel_root != Path('.') else d
                writeln(cmd, f'if not exist "{dir_path}" mkdir "{dir_path}"')

        # Écriture des fichiers
        for root, dirs, files in os.walk(PROJECT_ROOT):
            rel_root = Path(root).relative_to(PROJECT_ROOT)
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for file in files:
                if file in EXCLUDED_FILES or file == script_name:
                    continue

                file_path = Path(root) / file
                rel_path = file_path.relative_to(PROJECT_ROOT)

                # Lecture du contenu binaire
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # Calcul du hash
                expected_hash = sha256_of_bytes(data)
                original_hashes[str(rel_path)] = expected_hash
                cmd.write(f'echo Décompression de {rel_path}\r\n')

                # Détection Texte vs Binaire
                try:
                    content = data.decode('utf-8')
                    
                    # --- CAS FICHIER TEXTE ---
                    lines = content.splitlines()
                    if not lines:
                        cmd.write(f'type nul > "{rel_path}"\r\n')
                    else:
                        first = True
                        for line in lines:
                            safe_line = escape_line_for_cmd(line)
                            # IMPORTANT : Pas d'espace après echo( pour ne pas altérer le contenu
                            if first:
                                writeln(cmd, f'> "{rel_path}" echo({safe_line}')
                                first = False
                            else:
                                writeln(cmd, f'>> "{rel_path}" echo({safe_line}')

                except UnicodeDecodeError:
                    # --- CAS FICHIER BINAIRE ---
                    print(f"[BINAIRE] {rel_path}")
                    b64_content = base64.b64encode(data).decode('ascii')
                    tmp_b64_file = "tmp_b64_payload.txt"
                    
                    writeln(cmd, f'type nul > "{tmp_b64_file}"')
                   
                    chunk_size = 2000
                    for i in range(0, len(b64_content), chunk_size):
                        chunk = b64_content[i:i+chunk_size]
                        writeln(cmd, f'>> "{tmp_b64_file}" echo({chunk}')
                   
                    writeln(cmd, f'certutil -decode "{tmp_b64_file}" "{rel_path}" >nul')
                    writeln(cmd, f'del "{tmp_b64_file}"')

                # Vérification SHA-256
                writeln(cmd, f'certutil -hashfile "{rel_path}" SHA256 | findstr /I /C:"{expected_hash.upper()}" >nul')
                writeln(cmd, f'if %errorlevel%==0 (echo    [OK] {rel_path}) else (echo    [ERREUR] {rel_path})')

        # Fin du script
        writeln(cmd, "echo.")
        writeln(cmd, "echo Reconstruction terminée.")
        writeln(cmd, "pause")
        
    print(f"✅ {OUTPUT_CMD} généré")

if __name__ == "__main__":
    generate_cmd()

    # Nettoyage des lignes vides
    print("Nettoyage des lignes vides...")
    with open(OUTPUT_CMD, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    clean_lines = [line for line in lines if line.strip() != ""]
    
    with open(OUTPUT_CMD, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.writelines(clean_lines)

    print(f"✅ {OUTPUT_CMD} généré et compacté avec succès.")