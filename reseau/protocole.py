"""Protocole applicatif "maison" pour la communication V2I par sockets.

Format : chaque message est un objet JSON sur une seule ligne, terminé
par un caractère '\\n'. Pas de librairie réseau haut niveau (pas de
MQTT) : uniquement la lib standard (socket, json, struct possible si
besoin d'un format binaire plus tard).

Types de messages actuellement définis :
- "etat"      : snapshot complet de la simulation (envoyé par le serveur)
- "bienvenue" : message d'accueil envoyé à la connexion d'un client
"""

import json

SEPARATEUR = b"\n"


def encoder_message(dictionnaire):
    """Transforme un dict Python en bytes prêts à être envoyés sur le socket."""
    return json.dumps(dictionnaire, ensure_ascii=False).encode("utf-8") + SEPARATEUR


def decoder_message(ligne_bytes):
    """Transforme une ligne reçue (bytes, sans le \\n) en dict Python."""
    return json.loads(ligne_bytes.decode("utf-8"))


def extraire_messages(buffer):
    """Découpe le buffer accumulé en messages complets (séparés par \\n).
    Retourne (liste_de_dicts, reste_du_buffer_non_traité).

    Utilisation typique dans une boucle de réception :
        buffer = b""
        while True:
            morceau = sock.recv(4096)
            if not morceau:
                break
            messages, buffer = extraire_messages(buffer + morceau)
            for m in messages:
                traiter(m)
    """
    morceaux = buffer.split(SEPARATEUR)
    # Le dernier élément est soit vide (buffer se terminait par \n),
    # soit un message incomplet à conserver pour la prochaine réception.
    reste = morceaux.pop()
    messages = [decoder_message(m) for m in morceaux if m]
    return messages, reste
