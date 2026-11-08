"""Point d'entrée à lancer sur la VM Client.

Application graphique PyQt6 qui se connecte au serveur (VM Serveur)
par socket et affiche la simulation en temps réel."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from client.fenetre_principale import FenetrePrincipale


def main():
    app = QApplication(sys.argv)
    fenetre = FenetrePrincipale()
    fenetre.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
