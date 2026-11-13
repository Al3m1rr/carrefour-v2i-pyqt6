"""Les trois types concrets d'usagers : véhicule, cycliste et piéton.

Tous héritent d'Usager et n'ajoutent que ce qui leur est propre :
gabarit, vitesse de référence et attributs métier. La logique de
déplacement, elle, reste entièrement dans la classe mère.
"""

import config
from models.usager import Usager


class Vehicule(Usager):
    """Véhicule à quatre roues : ordinaire, autonome ou d'urgence.

    Les trois variantes partagent le même comportement de conduite ;
    elles se distinguent par leur vitesse maximale, leur couleur à
    l'écran et, pour l'urgence, par le droit d'emprunter la voie
    réservée et de déclencher une alerte V2I.
    """

    longueur = 28.0
    largeur = 15.0

    def __init__(self, branche, destination, route, urgence=False, autonome=False):
        """Construit un véhicule et déduit son type des deux drapeaux.

        Args:
            branche (str): branche d'entrée (N/S/E/W).
            destination (str): branche de sortie visée.
            route (list): waypoints de la trajectoire.
            urgence (bool): véhicule prioritaire (ambulance, pompiers).
            autonome (bool): véhicule autonome. Il ne se distingue des
                véhicules ordinaires que par son type et sa couleur :
                aucun comportement de conduite spécifique n'est
                implémenté.
        """
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
    """Cycliste circulant sur la bande cyclable, au bord droit de la voie.

    Étant déjà sur le bord de la chaussée, il n'a pas à se ranger à
    l'approche d'un véhicule d'urgence.
    """

    longueur = 16.0
    largeur = 9.0

    def __init__(self, branche, destination, route):
        """Construit un cycliste suivant une trajectoire décalée vers le bord.

        Args:
            branche (str): branche d'entrée (N/S/E/W).
            destination (str): branche de sortie visée.
            route (list): waypoints, déjà décalés sur la bande cyclable.
        """
        super().__init__("cycliste", branche, route, config.VITESSE_CYCLISTE)
        self.destination = destination


class Pieton(Usager):
    """Piéton traversant sur un passage protégé.

    Il attend sur le trottoir (vitesse nulle) tant qu'il ne peut pas
    s'engager, et devient prioritaire dès qu'il a posé le pied sur la
    chaussée, conformément au code de la route.
    """

    longueur = 10.0
    largeur = 10.0

    def __init__(self, branche, route):
        """Construit un piéton à l'arrêt au bord du passage.

        Args:
            branche (str): branche dont il emprunte le passage piéton.
            route (list): les deux extrémités de la traversée.
        """
        super().__init__("pieton", branche, route, config.VITESSE_PIETON)
        self.vitesse = 0.0          # attend sur le trottoir avant de s'engager
        self.engage = False         # True dès qu'il a posé le pied sur la chaussée
