#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOF-PREP — agent IA local (OPTIONNEL).

Petit serveur HTTP, 100% bibliotheque standard (rien a installer), qui sert de
PONT entre l'application web DOF-PREP (hors-ligne) et l'API Claude (Anthropic).
Il tourne UNIQUEMENT en local et n'est JAMAIS requis pour utiliser DOF-PREP :
sans lui, l'application fonctionne exactement comme avant, entierement
hors-ligne. Avec lui, deux fonctions optionnelles s'activent dans le tableau
de bord : analyse des lacunes et proposition de nouvelles questions.

Pourquoi un serveur intermediaire plutot qu'un appel direct depuis le navigateur ?
  - La cle API Anthropic ne doit JAMAIS se trouver dans du code cote navigateur
    (elle serait visible via les outils de developpement). Ce script la garde
    cote serveur, lue depuis une variable d'environnement, jamais transmise au
    navigateur.
  - L'API Anthropic n'est pas concue pour etre appelee directement depuis un
    navigateur. Ce serveur relaie la requete et ajoute les en-tetes CORS
    necessaires pour que DOF-PREP (fichier autonome en file://, ou PWA servie
    en http://) puisse l'appeler depuis n'importe quelle origine locale.

Lancement :
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 dof-prep-agent.py

Variables d'environnement (toutes optionnelles sauf la cle) :
    ANTHROPIC_API_KEY   cle API Anthropic (obligatoire pour les vrais appels)
    DOF_AGENT_HOST      defaut 127.0.0.1
    DOF_AGENT_PORT      defaut 8799
    DOF_AGENT_MODEL     defaut claude-sonnet-5

Endpoints :
    GET  /              -> description sommaire (utile pour verifier a la main)
    GET  /health         -> etat de l'agent : {"ok", "has_key", "model"}
    POST /analyze         -> analyse de la progression + recommandations (texte)
    POST /generate-questions -> propose de nouvelles questions (a valider)

Confidentialite : rien n'est envoye a Anthropic tant qu'un des deux endpoints
POST n'est pas explicitement appele par l'utilisateur, et uniquement les
champs necessaires (scores de maitrise par domaine, domaine cible, enonces
existants pour eviter les doublons) — jamais de donnee personnelle.
"""

import os
import sys
import json
import unicodedata
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

HOST = os.environ.get("DOF_AGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("DOF_AGENT_PORT", "8799"))
MODEL = os.environ.get("DOF_AGENT_MODEL", "claude-sonnet-5")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

VALID_DOMAINS = {
    "DOFD-1": "Explorer le DevOps",
    "DOFD-2": "Principes fondamentaux du DevOps (les Trois Voies)",
    "DOFD-3": "Pratiques cles du DevOps",
    "DOFD-4": "Cadres metier et techniques",
    "DOFD-5": "Valeurs DevOps : culture, comportements et modeles operationnels",
    "DOFD-6": "Valeurs DevOps : automatisation et architecture des chaines d'outils",
    "DOFD-7": "Valeurs DevOps : mesure, metriques et reporting",
    "DOFD-8": "Valeurs DevOps : partage, accompagnement et evolution",
}
VALID_TYPES = {"single", "multiple", "truefalse"}
LEVEL_DIFFICULTY = {"moyen": (2, 3), "difficile": (3, 4), "tres_difficile": (4, 5)}


class AgentError(Exception):
    """Erreur controlee : status HTTP + message a renvoyer tel quel au client."""
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def strip_accents(s):
    """Translittere les caracteres accentues en ASCII pur. La banque existante
    est en francais SANS accents (convention du projet) ; ceci l'applique
    automatiquement au texte genere, quoi que le modele ait produit, plutot que
    de rejeter une question sinon correcte pour un simple accent."""
    if not isinstance(s, str):
        return s
    # Les ligatures ne se decomposent PAS via NFKD (ce sont des lettres a part
    # entiere) : il faut les substituer AVANT la translitteration, sinon
    # l'encodage ascii/ignore les supprime silencieusement.
    s = s.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    nf = unicodedata.normalize("NFKD", s)
    return nf.encode("ascii", "ignore").decode("ascii")


def call_claude(system, user, max_tokens):
    """Appelle l'API Messages d'Anthropic (POST /v1/messages) et renvoie le
    texte de la reponse. Aucun parametre temperature/top_p/top_k : ils sont
    inutiles ici et evitent tout risque d'incompatibilite selon le modele."""
    if not API_KEY:
        raise AgentError(400, "Cle API manquante : definissez ANTHROPIC_API_KEY avant de lancer l'agent.")
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:400]
        raise AgentError(502, "L'API Anthropic a refuse la requete (" + str(e.code) + ") : " + detail)
    except urllib.error.URLError as e:
        raise AgentError(502, "Impossible de joindre l'API Anthropic : " + str(e.reason))
    parts = data.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    if not text:
        raise AgentError(502, "Reponse de l'API sans contenu texte exploitable.")
    return text


def extract_json(text):
    """Parse un JSON renvoye par le modele, en tolerant d'eventuelles balises
    de code (```json ... ```) ou un preambule/postambule autour du JSON."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    for a, b in (("[", "]"), ("{", "}")):
        i, j = t.find(a), t.rfind(b)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise AgentError(502, "Reponse du modele non conforme (JSON illisible). Reessayez.")


def validate_question(raw, expected_domain=None):
    """Valide et normalise une question candidate issue du modele. Leve
    AgentError (502 : probleme cote reponse du modele) si non conforme."""
    if not isinstance(raw, dict):
        raise AgentError(502, "Question candidate invalide (pas un objet).")
    domain = raw.get("domain")
    if domain not in VALID_DOMAINS:
        raise AgentError(502, "Domaine invalide dans une question generee : " + str(domain))
    if expected_domain and domain != expected_domain:
        domain = expected_domain  # le domaine demande fait foi (quota/tri en aval)
    try:
        k_level = int(raw.get("k_level"))
        difficulty = int(raw.get("difficulty"))
    except (TypeError, ValueError):
        raise AgentError(502, "k_level/difficulty non numeriques dans une question generee.")
    if not (1 <= k_level <= 7):
        raise AgentError(502, "k_level hors bornes (1-7).")
    if not (1 <= difficulty <= 5):
        raise AgentError(502, "difficulty hors bornes (1-5).")
    qtype = raw.get("type")
    if qtype not in VALID_TYPES:
        raise AgentError(502, "type de question invalide : " + str(qtype))
    statement = strip_accents(str(raw.get("statement") or "").strip())
    if len(statement) < 8:
        raise AgentError(502, "Enonce de question trop court ou absent.")
    options = raw.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise AgentError(502, "Options manquantes ou insuffisantes (2 minimum).")
    norm_opts, n_correct = [], 0
    for o in options:
        if not isinstance(o, dict):
            raise AgentError(502, "Option invalide (pas un objet).")
        text = strip_accents(str(o.get("text") or "").strip())
        correct = bool(o.get("correct"))
        if not text:
            raise AgentError(502, "Option sans texte.")
        if correct:
            n_correct += 1
        norm_opts.append({"text": text, "correct": correct})
    if qtype == "truefalse" and len(norm_opts) != 2:
        raise AgentError(502, "Une question vrai/faux doit avoir exactement 2 options.")
    if qtype in ("single", "truefalse") and n_correct != 1:
        raise AgentError(502, "Une question a choix unique doit avoir exactement 1 bonne reponse.")
    if qtype == "multiple" and n_correct < 2:
        raise AgentError(502, "Une question a choix multiple doit avoir au moins 2 bonnes reponses.")
    explanation = strip_accents(str(raw.get("explanation") or "").strip())
    return {
        "domain": domain, "k_level": k_level, "difficulty": difficulty, "type": qtype,
        "statement": statement, "options": norm_opts, "explanation": explanation,
    }


def handle_analyze(payload):
    mastery = payload.get("mastery") or {}
    weak = payload.get("weak_domains") or []
    readiness = payload.get("readiness")
    target = payload.get("target")
    lines = []
    for code, label in VALID_DOMAINS.items():
        m = mastery.get(code) or {}
        score = m.get("score", 0) or 0
        attempts = m.get("attempts", 0) or 0
        lines.append("%s (%s) : maitrise=%.2f, tentatives=%d" % (code, label, score, attempts))
    context = "\n".join(lines)
    system = (
        "Tu es un coach de preparation a la certification DevOps Foundation (DOFD v3.4, "
        "DevOps Institute). Tu recois l'etat de progression d'un apprenant (maitrise par "
        "domaine, entre 0 et 1) et tu rediges une analyse COURTE (120 a 200 mots), en francais "
        "AVEC accents, chaleureuse mais precise, qui : (1) situe le niveau global, (2) nomme "
        "2 a 3 domaines prioritaires en expliquant concretement leur enjeu pour l'examen, "
        "(3) propose des actions realistes pour la prochaine session de revision. Pas de "
        "generalites creuses. Reponds en texte brut, sans titre ni markdown."
    )
    user = "Etat de progression par domaine :\n" + context
    user += "\nDomaines sous le seuil de maitrise (65%%) : %s." % (", ".join(weak) if weak else "aucun")
    if isinstance(readiness, (int, float)):
        user += "\nPreparation globale actuelle : %.0f%%." % (readiness * 100)
    if isinstance(target, (int, float)):
        user += "\nObjectif vise : %.0f%%." % (target * 100)
    return call_claude(system, user, max_tokens=600).strip()


def handle_generate(payload):
    domain = payload.get("domain")
    if domain not in VALID_DOMAINS:
        raise AgentError(400, "Domaine invalide ou manquant.")
    try:
        count = int(payload.get("count", 5))
    except (TypeError, ValueError):
        count = 5
    count = max(1, min(10, count))
    band = LEVEL_DIFFICULTY.get(payload.get("level"))
    avoid = payload.get("avoid_statements") or []
    avoid = [strip_accents(str(a))[:160] for a in avoid if str(a).strip()][:40]

    label = VALID_DOMAINS[domain]
    band_txt = ("Vise une difficulte entre %d et %d (echelle 1-5)." % band) if band \
        else "Varie les difficultes entre 1 et 5."
    avoid_txt = ""
    if avoid:
        avoid_txt = "\nN'invente PAS de question proche des enonces suivants (deja dans la banque) :\n" \
            + "\n".join("- " + a for a in avoid)

    system = (
        "Tu generes des questions d'examen blanc pour la certification DevOps Foundation "
        "(DOFD v3.4, DevOps Institute), domaine \"" + domain + " - " + label + "\". "
        "Reponds UNIQUEMENT avec un tableau JSON valide (aucun texte autour, aucune balise "
        "de code), de la forme exacte : "
        '[{"domain": "' + domain + '", "k_level": <entier 1-7>, "difficulty": <entier 1-5>, '
        '"type": "single|multiple|truefalse", "statement": "...", '
        '"options": [{"text": "...", "correct": true|false}, ...], "explanation": "..."}]. '
        "IMPORTANT : le contenu (statement, options, explanation) doit etre en FRANCAIS SANS "
        "AUCUN ACCENT (ecris comme sur un clavier US : e/e/e -> e, c -> c, etc.), pour rester "
        "compatible avec la banque existante. Les types 'single' et 'truefalse' ont EXACTEMENT "
        "une bonne reponse ; 'multiple' en a au moins deux. Les 'truefalse' ont exactement 2 "
        "options (Vrai/Faux). Fournis une explication pedagogique courte (1-2 phrases) par "
        "question. " + band_txt
    )
    user = "Genere exactement %d question(s) originale(s) et plausible(s) pour ce domaine." % count
    user += avoid_txt

    text = call_claude(system, user, max_tokens=800 + 500 * count)
    parsed = extract_json(text)
    if not isinstance(parsed, list):
        parsed = [parsed]
    if not parsed:
        raise AgentError(502, "Le modele n'a renvoye aucune question.")
    validated = [validate_question(q, expected_domain=domain) for q in parsed[:count]]
    return {"questions": validated, "count": len(validated)}


class Handler(BaseHTTPRequestHandler):
    server_version = "DOFPrepAgent/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[dof-agent] " + (fmt % args) + "\n")

    def _cors(self):
        origin = self.headers.get("Origin") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")

    def _send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True, "has_key": bool(API_KEY), "model": MODEL})
        elif self.path == "/":
            self._send_json(200, {
                "service": "dof-prep-agent", "has_key": bool(API_KEY), "model": MODEL,
                "endpoints": ["GET /health", "POST /analyze", "POST /generate-questions"],
            })
        else:
            self._send_json(404, {"error": "Route inconnue."})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Corps de requete JSON invalide."})
            return
        try:
            if self.path == "/analyze":
                self._send_json(200, {"analysis": handle_analyze(payload)})
            elif self.path == "/generate-questions":
                self._send_json(200, handle_generate(payload))
            else:
                self._send_json(404, {"error": "Route inconnue."})
        except AgentError as e:
            self._send_json(e.status, {"error": e.message})
        except Exception as e:  # filet de securite : jamais de 500 opaque
            self._send_json(500, {"error": "Erreur interne de l'agent : " + str(e)})


def main():
    if not API_KEY:
        print("[dof-agent] ATTENTION : ANTHROPIC_API_KEY n'est pas definie.")
        print("[dof-agent] L'agent demarre quand meme (utile pour /health), mais /analyze et")
        print("[dof-agent] /generate-questions repondront une erreur claire tant qu'elle est absente.")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print("[dof-agent] DOF-PREP agent IA sur http://%s:%d  (modele: %s)" % (HOST, PORT, MODEL))
    print("[dof-agent] 100%% optionnel : sans lui, DOF-PREP fonctionne hors-ligne comme avant.")
    print("[dof-agent] Ctrl+C pour arreter.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[dof-agent] Arret.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
