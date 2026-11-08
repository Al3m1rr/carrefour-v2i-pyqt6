"""Serveur socket TCP "maison" (lib standard uniquement : socket + threading).

Rôle :
- accepter les connexions des clients (VM Client) ;
- diffuser à chacun l'état de la simulation à chaque tick ;
- recevoir les COMMANDES envoyées par les clients (ajout / suppression
  d'usagers) et les déposer dans une file thread-safe.

La boucle de simulation consomme cette file entre deux ticks : le
moteur n'est ainsi jamais modifié par deux threads en même temps."""

import queue
import socket
import threading
from reseau.protocole import encoder_message, extraire_messages


class ServeurSocket:
    def __init__(self, hote, port):
        self.hote = hote
        self.port = port
        self.socket_ecoute = None
        self.clients = []              # liste de sockets connectés
        self.verrou_clients = threading.Lock()
        self.en_cours = False
        self.file_commandes = queue.Queue()   # (connexion, message) reçus des clients

    def demarrer(self):
        self.socket_ecoute = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_ecoute.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_ecoute.bind((self.hote, self.port))
        self.socket_ecoute.listen(5)
        self.en_cours = True
        print(f"[Serveur Socket] En écoute sur {self.hote}:{self.port}")

        thread_accept = threading.Thread(target=self._boucle_acceptation, daemon=True)
        thread_accept.start()

    def _boucle_acceptation(self):
        while self.en_cours:
            try:
                connexion, adresse = self.socket_ecoute.accept()
            except OSError:
                break  # le socket d'écoute a été fermé (arrêt du serveur)

            print(f"[Serveur Socket] Nouveau client connecté : {adresse}")
            with self.verrou_clients:
                self.clients.append(connexion)

            self.envoyer_a(connexion, {"type": "bienvenue", "message": "Connecté au serveur carrefour"})
            threading.Thread(target=self._boucle_lecture, args=(connexion, adresse),
                             daemon=True).start()

    def _boucle_lecture(self, connexion, adresse):
        """Un thread par client : lit ses commandes et les met en file."""
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
        print(f"[Serveur Socket] Client déconnecté : {adresse}")

    def commandes_en_attente(self):
        """Vide la file des commandes reçues (appelé par la boucle principale)."""
        commandes = []
        while True:
            try:
                commandes.append(self.file_commandes.get_nowait())
            except queue.Empty:
                return commandes

    def envoyer_a(self, connexion, dictionnaire):
        """Envoie un message à un seul client (réponse à sa commande)."""
        with self.verrou_clients:
            try:
                connexion.sendall(encoder_message(dictionnaire))
            except OSError:
                pass

    def diffuser(self, dictionnaire):
        """Envoie le dictionnaire (encodé en JSON) à tous les clients
        connectés. Retire silencieusement les clients déconnectés."""
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
                try:
                    connexion.close()
                except OSError:
                    pass

    def arreter(self):
        self.en_cours = False
        with self.verrou_clients:
            for connexion in self.clients:
                try:
                    connexion.close()
                except OSError:
                    pass
            self.clients.clear()
        if self.socket_ecoute:
            self.socket_ecoute.close()
