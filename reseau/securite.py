"""Sécurité des messages V2I : signature HMAC-SHA256.

En production, la clé serait distribuée aux véhicules d'urgence
autorisés par une autorité de certification (comme les normes V2X
le font avec des certificats). Dans la maquette, on utilise une
clé partagée configurable par variable d'environnement.

Utilisation :
    from reseau.securite import signer_message, verifier_message

    # Côté ambulance (envoi)
    message["signature"] = signer_message(message)

    # Côté serveur (réception)
    if not verifier_message(message):
        print("Alerte rejetée : signature invalide")
"""

import hashlib
import hmac
import json
import os

# Clé partagée — à changer en production
CLE_SECRETE = os.environ.get(
    "CARREFOUR_CLE_V2I",
    "carrefour_mulhouse_cle_secrete_2026"
).encode("utf-8")


def _payload(message):
    """Extrait les champs signés (tout sauf la signature elle-même)."""
    return {k: v for k, v in sorted(message.items()) if k != "signature"}


def signer_message(message):
    """Retourne la signature HMAC-SHA256 du message (en hexadécimal)."""
    contenu = json.dumps(_payload(message), sort_keys=True, ensure_ascii=False)
    return hmac.new(CLE_SECRETE, contenu.encode("utf-8"), hashlib.sha256).hexdigest()


def verifier_message(message):
    """Vérifie la signature d'un message reçu.
    Retourne True si valide, False si absente ou incorrecte."""
    signature_recue = message.get("signature")
    if not signature_recue:
        return False
    signature_attendue = signer_message(message)
    return hmac.compare_digest(signature_recue, signature_attendue)
