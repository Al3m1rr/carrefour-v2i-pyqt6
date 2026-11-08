"""Point d'entrée du poste client (interface graphique PyQt6).

Application graphique qui se connecte à la passerelle (VM2) par socket
et affiche la simulation en temps réel. Elle ne joint jamais le moteur
(VM1) directement."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from client.fenetre_principale import FenetrePrincipale


def main():
    """Crée l'application Qt, affiche la fenêtre et lance la boucle d'événements."""
    app = QApplication(sys.argv)
    fenetre = FenetrePrincipale()
    fenetre.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
