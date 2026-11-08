"""Point d'entree de la VM1 "Simulation" (Debian 13, sans interface graphique).

Responsabilite unique de cette VM : faire tourner le moteur de
simulation du carrefour et persister les donnees temps reel dans SA
base locale (`carrefour_moteur_db`).

Elle n'expose rien aux clients finaux : elle ouvre un seul port interne
(MOTEUR_PORT) auquel la passerelle de la VM2 se connecte. Les clients
PyQt6 ne joignent jamais cette VM directement, ce qui isole le coeur
metier du reseau exterieur.

Flux a chaque tick :
    commandes recues de la VM2  ->  appliquees entre deux ticks
    moteur.tick()               ->  etat complet diffuse vers la VM2

Lancement :
    python3 serveur/main_moteur.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.connexion import connexion_moteur
from database.dao import DAOMoteur
from simulation.moteur import MoteurSimulation
from reseau.serveur_socket import ServeurSocket


def main():
    """Demarre la simulation et la sert a la passerelle jusqu'a Ctrl+C."""
    print("=== VM1 - Moteur de simulation du carrefour ===")

    connexion = connexion_moteur()
    dao = DAOMoteur(connexion) if connexion else None

    moteur = MoteurSimulation(dao=dao)

    lien = ServeurSocket(config.MOTEUR_ECOUTE_HOTE, config.MOTEUR_PORT,
                         libelle="Lien VM2")
    lien.demarrer()

    intervalle = 1.0 / config.TICKS_PAR_SECONDE
    print(f"Simulation demarree ({config.TICKS_PAR_SECONDE} ticks/s). Ctrl+C pour arreter.")

    try:
        while True:
            debut = time.time()

            # Commandes relayees par la passerelle, appliquees entre deux ticks.
            for connexion_passerelle, commande in lien.commandes_en_attente():
                identifiant_client = commande.get("_client")
                retour = moteur.appliquer_commande(commande)
                print(f"[Commande] {commande.get('action')} "
                      f"{commande.get('usager')} -> {retour}")
                lien.envoyer_a(connexion_passerelle, {
                    "type": "info",
                    "message": retour,
                    "_client": identifiant_client,
                })

            moteur.tick()
            lien.diffuser(moteur.etat_reseau())

            attente = intervalle - (time.time() - debut)
            if attente > 0:
                time.sleep(attente)
    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        print("\n--- Resume de la simulation ---")
        for ligne in moteur.metriques.resume():
            print(ligne)
        lien.arreter()
        if connexion:
            connexion.close()


if __name__ == "__main__":
    main()
