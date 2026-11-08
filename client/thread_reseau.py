"""Thread réseau côté client (VM Client).

Règle de thread-safety respectée : ce thread ne modifie JAMAIS
directement un widget Qt. Il reçoit les données sur le socket et les
transmet au thread principal via des signaux (pyqtSignal).

Dans l'autre sens, l'interface envoie des commandes (boutons + / -)
avec envoyer_commande() : l'écriture sur le socket est protégée par un
verrou et ne touche à aucun widget."""

import socket
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from reseau.protocole import encoder_message, extraire_messages


class ThreadReseau(QThread):
    etat_recu = pyqtSignal(dict)            # état de la simulation
    statut_connexion = pyqtSignal(bool, str)  # connecté ?, message
    info_recue = pyqtSignal(str)            # réponse du serveur à une commande

    def __init__(self, hote, port, parent=None):
        super().__init__(parent)
        self.hote = hote
        self.port = port
        self._actif = True
        self._sock = None
        self._verrou_envoi = threading.Lock()

    def run(self):
        """Exécuté dans le thread secondaire (jamais dans le thread GUI)."""
        while self._actif:
            try:
                self._connecter_et_ecouter()
            except (ConnectionRefusedError, OSError) as e:
                self.statut_connexion.emit(False,
                    f"⚠️ Mode dégradé : connexion perdue ({e}). "
                    f"Le carrefour fonctionne en cycle fixe. "
                    f"Reconnexion dans 3 s...")
                time.sleep(3)

    def _connecter_et_ecouter(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.hote, self.port))
            with self._verrou_envoi:
                self._sock = sock
            self.statut_connexion.emit(True, f"Connecté au serveur {self.hote}:{self.port}")

            buffer = b""
            try:
                while self._actif:
                    morceau = sock.recv(65536)
                    if not morceau:
                        self.statut_connexion.emit(False, "Le serveur a fermé la connexion.")
                        break
                    messages, buffer = extraire_messages(buffer + morceau)
                    for message in messages:
                        type_message = message.get("type")
                        if type_message == "etat":
                            self.etat_recu.emit(message)
                        elif type_message == "info":
                            self.info_recue.emit(message.get("message", ""))
            finally:
                with self._verrou_envoi:
                    self._sock = None

    def envoyer_commande(self, action, type_usager, **parametres):
        """Envoie une commande au serveur (ex. priorite=1 pour une alerte).
        Retourne False si non connecté."""
        contenu = {"type": "commande", "action": action, "usager": type_usager}
        contenu.update(parametres)
        message = encoder_message(contenu)
        with self._verrou_envoi:
            if self._sock is None:
                return False
            try:
                self._sock.sendall(message)
                return True
            except OSError:
                return False

    def arreter(self):
        self._actif = False
        with self._verrou_envoi:
            if self._sock is not None:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        self.wait(1000)
