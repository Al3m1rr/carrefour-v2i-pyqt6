import config
from models.usager import Usager


class Vehicule(Usager):
    longueur = 28.0
    largeur = 15.0

    def __init__(self, branche, destination, route, urgence=False, autonome=False):
        if urgence:
            type_usager = "vehicule_urgence"
        elif autonome:
            type_usager = "vehicule_autonome"
        else:
            type_usager = "vehicule_normal"
        vitesse = config.VITESSE_VEHICULE_URGENCE if urgence else config.VITESSE_VEHICULE
        super().__init__(type_usager, branche, route, vitesse)
        self.destination = destination      # branche de sortie
        self.urgence = urgence
        self.autonome = autonome
        self.couloir_accorde = False        # True si la centrale lui a donné le couloir
        self.devie = False                  # True si son itinéraire a été modifié par la centrale
        self.priorite = 2                   # niveau transmis dans l'alerte (1 = vital)
        self.tick_arrivee = 0               # instant (prévu ou réel) d'arrivée au carrefour
        self.en_approche = False            # alerte envoyée, pas encore arrivé dans la zone


class Cycliste(Usager):
    longueur = 16.0
    largeur = 9.0

    def __init__(self, branche, destination, route):
        super().__init__("cycliste", branche, route, config.VITESSE_CYCLISTE)
        self.destination = destination


class Pieton(Usager):
    longueur = 10.0
    largeur = 10.0

    def __init__(self, branche, route):
        super().__init__("pieton", branche, route, config.VITESSE_PIETON)
        self.vitesse = 0.0          # attend sur le trottoir avant de s'engager
        self.engage = False         # True dès qu'il a posé le pied sur la chaussée
