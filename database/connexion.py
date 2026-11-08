"""Connexion à la base MariaDB du projet.

Si la connexion échoue (VM Serveur éteinte, mauvaise IP, etc.), la
simulation continue de fonctionner SANS enregistrement en base --
pratique pour tester/développer le code sans avoir la VM Serveur
allumée en permanence."""

import config

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql = None
    MySQLError = Exception


def obtenir_connexion():
    if mysql is None:
        print("[DB] mysql-connector-python n'est pas installé -- base désactivée.")
        print("[DB] Installe-le avec : pip install mysql-connector-python")
        return None
    try:
        connexion = mysql.connector.connect(**config.DB_CONFIG)
        if connexion.is_connected():
            print("[DB] Connexion à MariaDB réussie.")
            return connexion
    except MySQLError as e:
        print(f"[DB] Connexion impossible ({e}) -- la simulation continue sans base.")
    return None
