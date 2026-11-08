"""Liaison interne VM2 -> VM1 : le cote client du lien entre les deux VM.

La passerelle (VM2) n'heberge pas la simulation : elle s'abonne au
moteur (VM1) via un socket TCP et se contente de relayer.

- ce qui descend : les etats de simulation emis a chaque tick par la VM1,
  transmis a un callback qui les rediffuse aux clients PyQt6 ;
- ce qui remonte : les commandes des clients (ajout / suppression
  d'usager, alerte ambulance), envoyees telles quelles au moteur.

La reconnexion est automatique : si la VM1 redemarre, la passerelle se
reconnecte seule sans perdre ses propres clients. Uniquement de la lib
standard (socket + threading), conformement aux contraintes du projet.
"""

import socket
import threading
import time

from reseau.protocole import encoder_message, extraire_messages


class ClientMoteur:
    """Client TCP persistant de la passerelle vers le moteur de simulation."""

    DELAI_RECONNEXION = 3  # secondes entre deux tentatives

    def __init__(self, hote, port, sur_etat, sur_info, sur_statut=None):
        """Prepare la liaison sans encore se connecter.

        Args:
            hote (str): adresse de la VM1.
            port (int): port d'ecoute du moteur sur la VM1.
            sur_etat (callable): appele avec chaque message "etat" recu.
            sur_info (callable): appele avec chaque message "info" recu
                (reponse du moteur a une commande).
            sur_statut (callable): appele avec (connecte: bool, texte)
                a chaque changement d'etat de la liaison.
        """
        self.hote = hote
        self.port = port
        self.sur_etat = sur_etat
        self.sur_info = sur_info
        self.sur_statut = sur_statut
        self._actif = False
        self._sock = None
        self._verrou_envoi = threading.Lock()
        self._thread = None

    def demarrer(self):
        """Lance le thread de connexion / reception en arriere-plan."""
        self._actif = True
        self._thread = threading.Thread(target=self._boucle, daemon=True)
        self._thread.start()

    def _signaler(self, connecte, texte):
        """Transmet un changement d'etat de la liaison, si un callback existe."""
        print(f"[Lien moteur] {texte}")
        if self.sur_statut:
            self.sur_statut(connecte, texte)

    def _boucle(self):
        """Se connecte au moteur et relit en boucle, avec reconnexion."""
        while self._actif:
            try:
                self._connecter_et_ecouter()
            except OSError as e:
                self._signaler(False, f"VM1 injoignable ({e}), "
                                      f"nouvelle tentative dans {self.DELAI_RECONNEXION} s")
            if self._actif:
                time.sleep(self.DELAI_RECONNEXION)

    def _connecter_et_ecouter(self):
        """Ouvre la connexion puis lit les messages jusqu'a sa fermeture."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.hote, self.port))
            with self._verrou_envoi:
                self._sock = sock
            self._signaler(True, f"Connecte au moteur {self.hote}:{self.port}")

            buffer = b""
            try:
                while self._actif:
                    morceau = sock.recv(65536)
                    if not morceau:
                        self._signaler(False, "Le moteur a ferme la liaison.")
                        break
                    try:
                        messages, buffer = extraire_messages(buffer + morceau)
                    except ValueError:
                        buffer = b""
                        continue
                    for message in messages:
                        self._traiter(message)
            finally:
                with self._verrou_envoi:
                    self._sock = None

    def _traiter(self, message):
        """Aiguille un message recu du moteur vers le bon callback."""
        type_message = message.get("type")
        if type_message == "etat":
            self.sur_etat(message)
        elif type_message == "info":
            self.sur_info(message)

    def envoyer_commande(self, commande):
        """Transmet une commande au moteur.

        Returns:
            True si la commande est partie, False si la VM1 est
            actuellement injoignable.
        """
        donnees = encoder_message(commande)
        with self._verrou_envoi:
            if self._sock is None:
                return False
            try:
                self._sock.sendall(donnees)
                return True
            except OSError:
                return False

    def est_connecte(self):
        """Indique si la liaison avec le moteur est actuellement ouverte."""
        with self._verrou_envoi:
            return self._sock is not None

    def arreter(self):
        """Coupe la liaison et arrete le thread de reception."""
        self._actif = False
        with self._verrou_envoi:
            if self._sock is not None:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        if self._thread:
            self._thread.join(timeout=2)
