"""Point d'entrée à lancer sur la VM Serveur (aucune interface graphique).

Fait tourner le moteur de simulation, écrit en base MariaDB et diffuse
l'état complet aux clients PyQt6 connectés par socket TCP."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.connexion import obtenir_connexion
from database.dao import DAO
from simulation.moteur import MoteurSimulation
from reseau.serveur_socket import ServeurSocket


def main():
    print("=== Serveur Carrefour Intelligent (V2I) ===")

    connexion = obtenir_connexion()
    dao = DAO(connexion) if connexion else None

    moteur = MoteurSimulation(dao=dao)

    serveur = ServeurSocket(config.SOCKET_ECOUTE_HOTE, config.SOCKET_PORT)
    serveur.demarrer()

    intervalle = 1.0 / config.TICKS_PAR_SECONDE
    print(f"Simulation démarrée ({config.TICKS_PAR_SECONDE} ticks/s). Ctrl+C pour arrêter.")

    try:
        while True:
            debut = time.time()

            # Commandes de l'opérateur, appliquées entre deux ticks
            for connexion, commande in serveur.commandes_en_attente():
                retour = moteur.appliquer_commande(commande)
                print(f"[Commande] {commande.get('action')} {commande.get('usager')} -> {retour}")
                serveur.envoyer_a(connexion, {"type": "info", "message": retour})

            moteur.tick()
            serveur.diffuser(moteur.etat_reseau())
            attente = intervalle - (time.time() - debut)
            if attente > 0:
                time.sleep(attente)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
    finally:
        print("\n--- Résumé de la simulation ---")
        for ligne in moteur.metriques.resume():
            print(ligne)
        serveur.arreter()
        if connexion:
            connexion.close()


if __name__ == "__main__":
    main()
