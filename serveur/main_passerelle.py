"""Point d'entree de la VM2 "Passerelle" (Debian 13, sans interface graphique).

Responsabilite unique de cette VM : etre la facade reseau du systeme.
Elle ne calcule aucune simulation. Elle :

1. s'abonne au moteur de la VM1 par un socket TCP interne ;
2. rediffuse chaque etat recu a tous les clients connectes (interfaces
   PyQt6 et application ambulance) ;
3. remonte les commandes des clients vers la VM1, et renvoie la reponse
   du moteur au client exact qui avait emis la commande ;
4. enregistre le bilan de la session dans SA base locale
   (`carrefour_stats_db`).

Interet de cette separation : le coeur metier (VM1) n'est jamais expose
aux clients, et une panne de la liaison inter-VM n'interrompt pas le
service des clients, qui sont prevenus du mode degrade.

Lancement :
    python3 serveur/main_passerelle.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database.connexion import connexion_passerelle
from database.dao import DAOPasserelle
from reseau.client_moteur import ClientMoteur
from reseau.serveur_socket import ServeurSocket


class Passerelle:
    """Relais bidirectionnel entre le moteur (VM1) et les clients finaux."""

    PERIODE_BOUCLE = 0.01  # seconde ; cadence de lecture des commandes clients

    def __init__(self):
        """Prepare la base locale, la facade client et le lien vers la VM1."""
        self.connexion_db = connexion_passerelle()
        self.dao = DAOPasserelle(self.connexion_db) if self.connexion_db else None
        self.session_id = self.dao.ouvrir_session() if self.dao else None

        self.dernier_etat = {}

        self.facade = ServeurSocket(config.SOCKET_ECOUTE_HOTE, config.SOCKET_PORT,
                                    libelle="Facade clients")
        self.lien = ClientMoteur(config.MOTEUR_HOTE, config.MOTEUR_PORT,
                                 sur_etat=self._sur_etat,
                                 sur_info=self._sur_info,
                                 sur_statut=self._sur_statut)

    def _sur_etat(self, message):
        """Rediffuse a tous les clients un etat recu du moteur."""
        self.dernier_etat = message
        self.facade.diffuser(message)

    def _sur_info(self, message):
        """Renvoie la reponse du moteur au seul client qui a commande."""
        identifiant = message.pop("_client", None)
        connexion = self.facade.connexion_par_id(identifiant)
        if connexion is not None:
            self.facade.envoyer_a(connexion, message)

    def _sur_statut(self, connecte, texte):
        """Previent les clients quand la liaison avec la VM1 change d'etat."""
        if not connecte:
            self.facade.diffuser({
                "type": "info",
                "message": f"Mode degrade : {texte}",
            })

    def demarrer(self):
        """Ouvre la facade client et la liaison vers le moteur."""
        print("=== VM2 - Passerelle reseau du carrefour ===")
        self.facade.demarrer()
        self.lien.demarrer()

    def boucler(self):
        """Relaie les commandes clients vers la VM1 jusqu'a Ctrl+C."""
        while True:
            for connexion, commande in self.facade.commandes_en_attente():
                commande["_client"] = self.facade.id_de(connexion)
                if not self.lien.envoyer_commande(commande):
                    self.facade.envoyer_a(connexion, {
                        "type": "info",
                        "message": "Commande impossible : moteur (VM1) injoignable.",
                    })
            time.sleep(self.PERIODE_BOUCLE)

    def arreter(self):
        """Cloture la session en base et ferme proprement les sockets."""
        if self.dao:
            if self.dao.cloturer_session(self.session_id,
                                         self.dernier_etat.get("stats")):
                print("[DB:passerelle] Bilan de session enregistre.")
            else:
                print("[DB:passerelle] Aucun bilan a enregistrer : "
                      "aucun etat recu du moteur pendant cette session.")
        self.lien.arreter()
        self.facade.arreter()
        if self.connexion_db:
            self.connexion_db.close()


def main():
    """Lance la passerelle et la maintient en service jusqu'a interruption."""
    passerelle = Passerelle()
    passerelle.demarrer()
    try:
        passerelle.boucler()
    except KeyboardInterrupt:
        print("\nArret demande.")
    finally:
        passerelle.arreter()


if __name__ == "__main__":
    main()
