"""Serveur socket TCP "maison" (lib standard uniquement : socket + threading).

Cette classe sert a DEUX endroits de l'architecture repartie :

- sur la VM1, le moteur l'utilise pour exposer la simulation a la
  passerelle (un seul "client" : la VM2) ;
- sur la VM2, la passerelle l'utilise comme facade vers les vrais
  clients (interfaces PyQt6 et application ambulance).

Role :
- accepter les connexions entrantes et leur attribuer un identifiant ;
- diffuser a chacune l'etat de la simulation ;
- recevoir les COMMANDES et les deposer dans une file thread-safe.

La boucle principale consomme cette file entre deux ticks : l'objet
metier n'est ainsi jamais modifie par deux threads en meme temps.
"""

import itertools
import queue
import socket
import threading

from reseau.protocole import encoder_message, extraire_messages


class ServeurSocket:
    """Serveur TCP multi-clients, un thread de lecture par connexion."""

    def __init__(self, hote, port, libelle="Serveur Socket"):
        """Prepare le serveur sans encore ouvrir le port.

        Args:
            hote (str): interface d'ecoute ("0.0.0.0" pour toutes).
            port (int): port TCP d'ecoute.
            libelle (str): prefixe des messages de log, pour distinguer
                le lien moteur de la facade client dans la console.
        """
        self.hote = hote
        self.port = port
        self.libelle = libelle
        self.socket_ecoute = None
        self.clients = []                      # sockets connectes
        self.verrou_clients = threading.Lock()
        self.en_cours = False
        self.file_commandes = queue.Queue()    # (connexion, message) recus
        self._compteur_id = itertools.count(1)
        self._id_par_connexion = {}
        self._connexion_par_id = {}

    def demarrer(self):
        """Ouvre le port et lance le thread qui accepte les connexions."""
        self.socket_ecoute = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_ecoute.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_ecoute.bind((self.hote, self.port))
        self.socket_ecoute.listen(5)
        self.en_cours = True
        print(f"[{self.libelle}] En ecoute sur {self.hote}:{self.port}")

        thread_accept = threading.Thread(target=self._boucle_acceptation, daemon=True)
        thread_accept.start()

    def _boucle_acceptation(self):
        """Accepte les connexions entrantes jusqu'a l'arret du serveur."""
        while self.en_cours:
            try:
                connexion, adresse = self.socket_ecoute.accept()
            except OSError:
                break  # le socket d'ecoute a ete ferme (arret du serveur)

            with self.verrou_clients:
                identifiant = next(self._compteur_id)
                self.clients.append(connexion)
                self._id_par_connexion[connexion] = identifiant
                self._connexion_par_id[identifiant] = connexion
            print(f"[{self.libelle}] Nouveau client #{identifiant} : {adresse}")

            self.envoyer_a(connexion, {"type": "bienvenue",
                                       "message": "Connecte au serveur carrefour"})
            threading.Thread(target=self._boucle_lecture,
                             args=(connexion, adresse), daemon=True).start()

    def _boucle_lecture(self, connexion, adresse):
        """Lit les commandes d'un client et les met en file (un thread par client)."""
        buffer = b""
        while self.en_cours:
            try:
                morceau = connexion.recv(4096)
            except OSError:
                break
            if not morceau:
                break
            try:
                messages, buffer = extraire_messages(buffer + morceau)
            except ValueError:
                buffer = b""  # message corrompu : on l'ignore
                continue
            for message in messages:
                if message.get("type") == "commande":
                    self.file_commandes.put((connexion, message))
        self._retirer(connexion)
        print(f"[{self.libelle}] Client deconnecte : {adresse}")

    def _retirer(self, connexion):
        """Oublie une connexion fermee (listes et tables d'identifiants)."""
        with self.verrou_clients:
            if connexion in self.clients:
                self.clients.remove(connexion)
            identifiant = self._id_par_connexion.pop(connexion, None)
            if identifiant is not None:
                self._connexion_par_id.pop(identifiant, None)
            try:
                connexion.close()
            except OSError:
                pass

    def id_de(self, connexion):
        """Retourne l'identifiant attribue a une connexion, ou None."""
        with self.verrou_clients:
            return self._id_par_connexion.get(connexion)

    def connexion_par_id(self, identifiant):
        """Retrouve la connexion correspondant a un identifiant, ou None.

        Utilise par la passerelle pour renvoyer la reponse du moteur au
        client qui avait emis la commande.
        """
        with self.verrou_clients:
            return self._connexion_par_id.get(identifiant)

    def commandes_en_attente(self):
        """Vide la file des commandes recues et la retourne.

        Returns:
            Liste de couples (connexion, message) a traiter.
        """
        commandes = []
        while True:
            try:
                commandes.append(self.file_commandes.get_nowait())
            except queue.Empty:
                return commandes

    def envoyer_a(self, connexion, dictionnaire):
        """Envoie un message a un seul client (reponse a sa commande)."""
        if connexion is None:
            return
        with self.verrou_clients:
            try:
                connexion.sendall(encoder_message(dictionnaire))
            except OSError:
                pass

    def diffuser(self, dictionnaire):
        """Envoie le message a tous les clients connectes.

        Les clients dont le socket est casse sont retires silencieusement.
        """
        message = encoder_message(dictionnaire)
        with self.verrou_clients:
            clients_a_retirer = []
            for connexion in self.clients:
                try:
                    connexion.sendall(message)
                except OSError:
                    clients_a_retirer.append(connexion)
            for connexion in clients_a_retirer:
                self.clients.remove(connexion)
                identifiant = self._id_par_connexion.pop(connexion, None)
                if identifiant is not None:
                    self._connexion_par_id.pop(identifiant, None)
                try:
                    connexion.close()
                except OSError:
                    pass

    def nb_clients(self):
        """Retourne le nombre de clients actuellement connectes."""
        with self.verrou_clients:
            return len(self.clients)

    def arreter(self):
        """Ferme toutes les connexions puis le socket d'ecoute."""
        self.en_cours = False
        with self.verrou_clients:
            for connexion in self.clients:
                try:
                    connexion.close()
                except OSError:
                    pass
            self.clients.clear()
            self._id_par_connexion.clear()
            self._connexion_par_id.clear()
        if self.socket_ecoute:
            self.socket_ecoute.close()
