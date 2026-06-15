#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dex_castin_word_addin_server.py — Reprise DEX -> CAST'IN, depuis Word via un
complément (add-in) Office.js.

PRINCIPE
--------
Un complément Word écrit en Office.js (JavaScript, exécuté dans le volet
Office) ne peut pas lire/écrire le système de fichiers ni parser un .docx :
il s'appuie donc sur un petit service local qui fait le travail. Ce script
EST ce service :

  - il démarre un serveur HTTP local (uniquement la bibliothèque standard :
    http.server), sur http://127.0.0.1:8943 par défaut ;
  - le complément Office.js récupère le document Word ouvert au format
    .docx (Office.js : `document.getFileAsync(Office.FileType.Compressed)`),
    l'encode en base64 et l'envoie à ce service via POST /api/process-dex ;
  - le service applique exactement les mêmes règles que dex_castin_cli.py
    (module commun dex_castin_common.py) et renvoie un JSON contenant :
      - "identification"   : Solution / Auteur / Responsable
      - "champs"            : un objet {clé: {label, tab, content}} par champ CAST'IN
      - "points_a_verifier" : liste des doutes / informations manquantes
      - "markdown"          : les trois blocs de sortie, prêts à afficher
  - le complément affiche le résultat dans le volet Office (taskpane.html /
    taskpane.js fournis dans le dossier addin/) pour copier-coller, champ par
    champ, dans CAST'IN.

Le dossier addin/ contient un exemple minimal de complément Office.js
(manifest.xml + taskpane.html/.js) qui consomme ce service. Voir le README.

LANCEMENT
---------
    python dex_castin_word_addin_server.py
    (variables d'environnement optionnelles : DEX_HOST, DEX_PORT, DEX_ALLOWED_ORIGIN)
"""

import base64
import binascii
import json
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Le module commun doit être dans le même dossier que ce script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dex_castin_common as dex  # noqa: E402


HOST = os.environ.get("DEX_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEX_PORT", "8943"))

# Origine autorisée pour les appels CORS depuis le complément Office.js.
# En développement, Office charge le taskpane sur https://localhost:3000
# (ou https://localhost:<port>). En production, indiquer l'URL d'hébergement
# du complément. "*" est accepté pour les tests locaux uniquement.
ALLOWED_ORIGIN = os.environ.get("DEX_ALLOWED_ORIGIN", "*")

# Taille maximale acceptée pour un fichier .docx envoyé (en octets).
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 Mo


class DexRequestHandler(BaseHTTPRequestHandler):
    """Gestionnaire HTTP minimal : une route de santé, une route de
    traitement. Pas de framework externe (respect du "zéro dépendance")."""

    server_version = "DexCastinAddin/1.0"

    # -- Utilitaires ------------------------------------------------------

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    # -- Pré-vol CORS -------------------------------------------------------

    def do_OPTIONS(self) -> None:  # noqa: N802 - imposé par BaseHTTPRequestHandler
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- Routes -------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok", "service": "dex-castin-addin"})
        else:
            self._send_error_json(404, "Route inconnue. Utiliser POST /api/process-dex.")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/process-dex":
            self._send_error_json(404, "Route inconnue. Utiliser POST /api/process-dex.")
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            self._send_error_json(400, "Corps de requête vide.")
            return
        if length > MAX_UPLOAD_SIZE:
            self._send_error_json(413, "Fichier trop volumineux.")
            return

        raw_body = self.rfile.read(length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error_json(400, "Corps JSON invalide.")
            return

        filename = payload.get("filename", "DEX.docx")
        docx_base64 = payload.get("docx_base64")
        if not docx_base64:
            self._send_error_json(400, "Champ 'docx_base64' manquant.")
            return

        try:
            docx_bytes = base64.b64decode(docx_base64, validate=True)
        except (binascii.Error, ValueError):
            self._send_error_json(400, "Contenu 'docx_base64' invalide (base64 attendu).")
            return

        # Le fichier .docx est écrit dans un fichier temporaire car
        # dex_castin_common.read_docx() s'appuie sur zipfile.ZipFile(path),
        # qui a besoin d'un chemin (ou d'un objet fichier-binaire complet).
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(docx_bytes)
                tmp_path = tmp.name
            try:
                result = dex.process_dex(tmp_path, filename=filename)
            finally:
                os.unlink(tmp_path)
        except Exception as exc:  # noqa: BLE001 - on renvoie un message exploitable au complément
            self._send_error_json(422, f"Impossible de traiter le document : {exc}")
            return

        self._send_json(200, dex.to_json(result))

    # -- Journalisation -------------------------------------------------------

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write(f"[dex-castin-addin] {self.address_string()} - {fmt % args}\n")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), DexRequestHandler)
    print(f"Service de reprise DEX -> CAST'IN démarré sur http://{HOST}:{PORT}")
    print("Endpoints :")
    print("  GET  /api/health")
    print("  POST /api/process-dex   { \"filename\": ..., \"docx_base64\": \"...\" }")
    print("Arrêt : Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
