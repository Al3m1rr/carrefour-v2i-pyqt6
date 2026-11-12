"""Application ambulance — simule le boîtier embarqué dans le véhicule
d'urgence. Envoie une alerte V2I au serveur par socket TCP, exactement
comme un vrai boîtier embarqué le ferait via le réseau mobile ou une
borne V2X ITS-G5 installée au bord de la route.

Utilisation :
    python ambulance/main_ambulance.py [hote] [port] [priorite] [branche]

Exemples :
    python ambulance/main_ambulance.py                         # tout par défaut
    python ambulance/main_ambulance.py 127.0.0.1 5050 1 N     # P1 depuis le nord
    python ambulance/main_ambulance.py 192.168.56.11 5050 2 W  # P2 depuis l'ouest, vers la passerelle (VM2)
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import json
import random
import config
from reseau.securite import signer_message

BRANCHES = list(config.BRANCHES)
LIBELLES_PRIORITE = {
    1: "Urgence vitale (SMUR / arrêt cardiaque)",
    2: "Urgence (ambulance / police en intervention)",
    3: "Non urgente (transport sanitaire / retour de mission)",
}


def envoyer_alerte(hote, port, priorite, branche):
    """Envoie une alerte V2I signée au carrefour, puis affiche sa réponse.

    L'alerte est signée en HMAC-SHA256 : le carrefour rejette toute
    demande de couloir prioritaire dont la signature est absente ou
    invalide, comme le ferait une vraie infrastructure V2X.

    Args:
        hote (str): adresse de la passerelle (VM2).
        port (int): port d'écoute de la passerelle.
        priorite (int): niveau 1 (vitale), 2 (urgence) ou 3 (non urgente).
        branche (str): branche d'entrée prévue (N/S/E/W).
    """
    from models.carrefour import DESTINATIONS
    destination = DESTINATIONS[branche]["tout_droit"]

    message = {
        "type": "commande",
        "action": "ajouter",
        "usager": "vehicule_urgence",
        "priorite": priorite,
        "branche": branche,
        "source": "boitier_embarque",
    }
    message["signature"] = signer_message(message)
    donnees = (json.dumps(message) + "\n").encode("utf-8")

    print(f"\n{'='*55}")
    print(f"  APPLICATION AMBULANCE — Boîtier embarqué V2I")
    print(f"{'='*55}")
    print(f"  Serveur cible   : {hote}:{port}")
    print(f"  Priorité        : P{priorite} — {LIBELLES_PRIORITE[priorite]}")
    print(f"  Entrée prévue   : branche {branche} → direction {destination}")
    print(f"  Arrivée estimée : dans {config.DELAI_ALERTE // config.TICKS_PAR_SECONDE} secondes")
    print(f"{'='*55}\n")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((hote, port))
            print("  ✅ Connexion au serveur de carrefour établie.")
            sock.sendall(donnees)
            print("  📡 Alerte V2I signée (HMAC-SHA256) et envoyée au carrefour.")

            # Attendre la réponse du serveur
            sock.settimeout(3)
            try:
                reponse_brute = b""
                while b"\n" not in reponse_brute:
                    morceau = sock.recv(4096)
                    if not morceau:
                        break
                    reponse_brute += morceau
                if reponse_brute:
                    for ligne in reponse_brute.split(b"\n"):
                        if not ligne.strip():
                            continue
                        try:
                            msg = json.loads(ligne.decode("utf-8"))
                            if msg.get("type") == "info":
                                print(f"  📥 Réponse du carrefour : {msg['message']}")
                        except Exception:
                            pass
            except socket.timeout:
                pass

    except ConnectionRefusedError:
        print(f"  ❌ Impossible de joindre le serveur ({hote}:{port}).")
        print("     Vérifiez que la passerelle est lancée sur la VM2 "
              "(./deploiement/demarrer.sh passerelle).")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ Erreur : {e}")
        sys.exit(1)

    print(f"\n  Le véhicule d'urgence entrera au carrefour dans")
    print(f"  ~{config.DELAI_ALERTE // config.TICKS_PAR_SECONDE} secondes.")
    print(f"  La voie est en cours de dégagement.\n")


def main():
    """Lit les paramètres (arguments, variables d'environnement ou saisie).

    Chaque paramètre absent de la ligne de commande est demandé de façon
    interactive, ce qui permet d'utiliser l'application aussi bien en
    démonstration manuelle que dans un script.
    """
    hote = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CARREFOUR_SOCKET_SERVEUR_HOTE", "127.0.0.1")
    port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("CARREFOUR_SOCKET_PORT", "5050"))

    if len(sys.argv) > 3:
        try:
            priorite = int(sys.argv[3])
            if priorite not in (1, 2, 3):
                raise ValueError
        except ValueError:
            print("Priorité invalide, utilisation de P2 par défaut.")
            priorite = 2
    else:
        priorite = int(input("Priorité (1=Urgence vitale / 2=Urgence / 3=Non urgente) [2] : ").strip() or "2")

    if len(sys.argv) > 4:
        branche = sys.argv[4].upper()
        if branche not in BRANCHES:
            print(f"Branche invalide, branche aléatoire utilisée.")
            branche = random.choice(BRANCHES)
    else:
        print(f"Branche d'entrée disponible : {', '.join(BRANCHES)}")
        saisie = input("Branche (N/S/E/W) [aléatoire] : ").strip().upper()
        branche = saisie if saisie in BRANCHES else random.choice(BRANCHES)

    envoyer_alerte(hote, port, priorite, branche)


if __name__ == "__main__":
    main()
