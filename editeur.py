#!/usr/bin/env python3
"""Editeur de niveau web.

Lancer :  python editeur.py
Puis le navigateur s'ouvre sur http://127.0.0.1:8765
- Ctrl+S dans l'editeur ecrit niveau.json (une copie niveau.json.bak est gardee)
- Bouton "Jouer" lance le jeu ; si le jeu tourne deja, appuie sur F5 dans le jeu
  pour recharger le niveau.
"""

import json
import os
import shutil
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DOSSIER = os.path.dirname(os.path.abspath(__file__))
NIVEAU = os.path.join(DOSSIER, "niveau.json")
PAGE = os.path.join(DOSSIER, "editeur", "index.html")
JEU = os.path.join(DOSSIER, "jeux_1_5.py")
HOTE = "127.0.0.1"
PORT = 8765
TAILLE_MAX = 2_000_000

processus_jeu = None


def python_du_projet():
    venv = os.path.join(DOSSIER, ".venv", "bin", "python")
    return venv if os.path.exists(venv) else sys.executable


def niveau_valide(data):
    if not isinstance(data, dict):
        return "le niveau doit etre un objet JSON"
    for cle, taille in (("blocks", 5), ("grates", 3), ("hazards", 4), ("hints", 4)):
        liste = data.get(cle, [])
        if not isinstance(liste, list):
            return f"'{cle}' doit etre une liste"
        for element in liste:
            if not isinstance(element, list) or len(element) != taille:
                return f"element invalide dans '{cle}' : {element!r}"
    for cle, taille in (("start", 2), ("goal", 4)):
        valeur = data.get(cle)
        if not isinstance(valeur, list) or len(valeur) != taille:
            return f"'{cle}' doit etre une liste de {taille} nombres"
    return None


def formater_niveau(data):
    """JSON lisible : un objet par ligne."""
    lignes = ["{", f'  "start": {json.dumps(data["start"])},']
    for cle in ("blocks", "grates", "hazards", "hints"):
        elements = data.get(cle, [])
        if not elements:
            lignes.append(f'  "{cle}": [],')
            continue
        lignes.append(f'  "{cle}": [')
        lignes.append(
            ",\n".join("    " + json.dumps(e, ensure_ascii=False) for e in elements)
        )
        lignes.append("  ],")
    lignes.append(f'  "goal": {json.dumps(data["goal"])}')
    lignes.append("}")
    return "\n".join(lignes) + "\n"


def origine_autorisee(origine):
    """Pages locales seulement (ex. Live Server de VS Code sur le port 5500)."""
    if not origine:
        return None
    if origine == "null":  # page ouverte en file://
        return origine
    for prefixe in ("http://127.0.0.1", "http://localhost"):
        if origine == prefixe or origine.startswith(prefixe + ":"):
            return origine
    return None


class Gestionnaire(BaseHTTPRequestHandler):
    def entetes_cors(self):
        origine = origine_autorisee(self.headers.get("Origin"))
        if origine:
            self.send_header("Access-Control-Allow-Origin", origine)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        self.send_response(204)
        self.entetes_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def repondre(self, code, contenu, type_mime="application/json; charset=utf-8"):
        if isinstance(contenu, str):
            contenu = contenu.encode("utf-8")
        self.send_response(code)
        self.entetes_cors()
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(contenu)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(contenu)

    def message(self, code, texte):
        self.repondre(code, json.dumps({"message": texte}))

    def do_GET(self):
        if self.path in ("/", "/index.html", "/editeur/index.html"):
            with open(PAGE, "rb") as fichier:
                self.repondre(200, fichier.read(), "text/html; charset=utf-8")
        elif self.path.startswith("/niveau.json"):
            with open(NIVEAU, "rb") as fichier:
                self.repondre(200, fichier.read())
        else:
            self.message(404, "introuvable")

    def do_POST(self):
        global processus_jeu

        origine = self.headers.get("Origin")
        if origine and not origine_autorisee(origine):
            self.message(403, "origine refusee")
            return

        if self.path == "/niveau.json":
            longueur = int(self.headers.get("Content-Length", 0))
            if longueur <= 0 or longueur > TAILLE_MAX:
                self.message(400, "taille invalide")
                return
            try:
                data = json.loads(self.rfile.read(longueur).decode("utf-8"))
            except ValueError as erreur:
                self.message(400, f"JSON invalide : {erreur}")
                return
            erreur = niveau_valide(data)
            if erreur:
                self.message(400, erreur)
                return
            if os.path.exists(NIVEAU):
                shutil.copyfile(NIVEAU, NIVEAU + ".bak")
            temporaire = NIVEAU + ".tmp"
            with open(temporaire, "w", encoding="utf-8") as fichier:
                fichier.write(formater_niveau(data))
            os.replace(temporaire, NIVEAU)
            self.message(200, "niveau.json sauvegarde")

        elif self.path == "/jouer":
            if processus_jeu is not None and processus_jeu.poll() is None:
                self.message(200, "Le jeu tourne deja : appuie sur F5 dans le jeu")
                return
            processus_jeu = subprocess.Popen([python_du_projet(), JEU], cwd=DOSSIER)
            self.message(200, "Jeu lance")
        else:
            self.message(404, "introuvable")

    def log_message(self, format, *args):
        pass


def main():
    serveur = ThreadingHTTPServer((HOTE, PORT), Gestionnaire)
    adresse = f"http://{HOTE}:{PORT}"
    print(f"Editeur : {adresse}   (Ctrl+C pour quitter)")
    webbrowser.open(adresse)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
