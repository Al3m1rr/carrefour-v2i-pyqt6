"""Connexion aux bases MariaDB du projet.

Le projet est reparti sur deux VM, chacune avec sa propre base locale :

- VM1 "Simulation"  -> `carrefour_moteur_db`  (tables usager, evenement)
- VM2 "Passerelle"  -> `carrefour_stats_db`   (table session_simulation)

Chaque processus ouvre donc SA base, en local (127.0.0.1 de son cote).
Si la connexion echoue (service MariaDB arrete, mauvais identifiants),
le processus continue de fonctionner SANS enregistrement : la simulation
reste utilisable pour une demonstration meme base indisponible.
"""

import config

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None
    MySQLError = Exception


def obtenir_connexion(parametres, libelle="base"):
    """Ouvre une connexion MariaDB a partir d'un dictionnaire de parametres.

    Args:
        parametres (dict): configuration de connexion (host, user,
            password, database), typiquement config.DB_MOTEUR_CONFIG ou
            config.DB_PASSERELLE_CONFIG.
        libelle (str): nom lisible de la base, utilise dans les messages
            affiches dans la console.

    Returns:
        Une connexion mysql.connector ouverte, ou None si la base est
        injoignable (le processus appelant doit alors fonctionner sans).
    """
    if mysql is None:
        print(f"[DB:{libelle}] mysql-connector-python absent -- base desactivee.")
        print("[DB] Installez-le avec : pip install mysql-connector-python")
        return None
    try:
        connexion = mysql.connector.connect(**parametres)
        if connexion.is_connected():
            print(f"[DB:{libelle}] Connexion a {parametres['database']}"
                  f"@{parametres['host']} reussie.")
            return connexion
    except MySQLError as e:
        print(f"[DB:{libelle}] Connexion impossible ({e}) -- on continue sans base.")
    return None


def connexion_moteur():
    """Ouvre la base locale de la VM1 (usagers et evenements)."""
    return obtenir_connexion(config.DB_MOTEUR_CONFIG, "moteur")


def connexion_passerelle():
    """Ouvre la base locale de la VM2 (bilans de session)."""
    return obtenir_connexion(config.DB_PASSERELLE_CONFIG, "passerelle")
