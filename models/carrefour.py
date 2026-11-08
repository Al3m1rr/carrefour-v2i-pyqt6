"""Géométrie du carrefour, conforme à la circulation à droite (France).

Convention d'orientation (repère écran, y vers le bas) :
  - un véhicule venant de "N" descend (cap sud), il roule donc sur la
    moitié ouest de la route verticale ;
  - un véhicule venant de "S" monte (cap nord), moitié est ;
  - un véhicule venant de "W" va vers l'est, moitié sud ;
  - un véhicule venant de "E" va vers l'ouest, moitié nord.

Chaque branche possède donc UNE voie entrante et UNE voie sortante,
distinctes -- c'est ce qui rend le "couloir prioritaire" réalisable :
on peut interdire une voie sortante sans bloquer la voie entrante."""

import config

# Destination d'un usager selon sa branche d'entrée et son choix.
# (tout_droit / gauche / droite, dans le respect du sens de circulation)
DESTINATIONS = {
    "N": {"tout_droit": "S", "gauche": "E", "droite": "W"},
    "S": {"tout_droit": "N", "gauche": "W", "droite": "E"},
    "W": {"tout_droit": "E", "gauche": "N", "droite": "S"},
    "E": {"tout_droit": "W", "gauche": "S", "droite": "N"},
}

AXE_DE_BRANCHE = {"N": "NS", "S": "NS", "E": "EO", "W": "EO"}

BRANCHE_OPPOSEE = {"N": "S", "S": "N", "E": "W", "W": "E"}


class Carrefour:
    """Géométrie du carrefour : axes des voies, points remarquables et
    trajectoires. Ne contient aucune logique de circulation, uniquement
    le calcul des coordonnées à partir des paramètres de config.py."""

    def __init__(self):
        """Mémorise le centre et les dimensions issus de la configuration."""
        self.cx = config.CENTRE_X
        self.cy = config.CENTRE_Y
        self.offset = config.OFFSET_VOIE
        self.demi_zone = config.DEMI_ZONE_CONFLIT

    # ---------- Axes des voies ----------

    def axe_voie_entrante(self, branche, decalage=0.0):
        """Coordonnée fixe (x pour N/S, y pour E/W) de la voie par
        laquelle on ENTRE depuis cette branche. `decalage` pousse vers
        le bord droit de la voie (utilisé pour la bande cyclable)."""
        return {
            "N": self.cx - self.offset - decalage,
            "S": self.cx + self.offset + decalage,
            "E": self.cy - self.offset - decalage,
            "W": self.cy + self.offset + decalage,
        }[branche]

    def axe_voie_sortante(self, branche, decalage=0.0):
        """Coordonnée fixe de la voie par laquelle on SORT vers cette branche.

        C'est la voie symétrique de l'entrante : la distinguer permet
        d'interdire une sortie (couloir prioritaire) sans bloquer
        l'entrée correspondante.
        """
        return {
            "N": self.cx + self.offset + decalage,
            "S": self.cx - self.offset - decalage,
            "E": self.cy + self.offset + decalage,
            "W": self.cy - self.offset - decalage,
        }[branche]

    # ---------- Points remarquables ----------

    def point_entree(self, branche, decalage=0.0):
        """Point d'apparition d'un usager, juste hors de l'écran."""
        v = self.axe_voie_entrante(branche, decalage)
        return {
            "N": (v, -20.0),
            "S": (v, config.HAUTEUR_SCENE + 20.0),
            "E": (config.LARGEUR_SCENE + 20.0, v),
            "W": (-20.0, v),
        }[branche]

    def point_ligne_arret(self, branche, decalage=0.0):
        """Point d'arrêt au feu rouge, situé AVANT le passage piéton."""
        v = self.axe_voie_entrante(branche, decalage)
        la = config.LIGNE_ARRET
        return {
            "N": (v, self.cy - la),
            "S": (v, self.cy + la),
            "E": (self.cx + la, v),
            "W": (self.cx - la, v),
        }[branche]

    def point_sortie(self, branche, decalage=0.0):
        """Point de disparition d'un usager, juste hors de l'écran."""
        v = self.axe_voie_sortante(branche, decalage)
        return {
            "N": (v, -20.0),
            "S": (v, config.HAUTEUR_SCENE + 20.0),
            "E": (config.LARGEUR_SCENE + 20.0, v),
            "W": (-20.0, v),
        }[branche]

    # ---------- Trajectoires ----------

    def construire_route(self, branche_entree, branche_sortie, decalage=0.0):
        """Liste de waypoints : entrée -> ligne d'arrêt -> (virage) -> sortie.

        Args:
            branche_entree (str): branche d'où vient l'usager (N/S/E/W).
            branche_sortie (str): branche vers laquelle il repart.
            decalage (float): décalage vers le bord droit de la voie,
                utilisé pour placer les cyclistes sur la bande cyclable.

        Returns:
            La liste des waypoints (x, y) à suivre. Un point de pivot
            supplémentaire est inséré pour les trajectoires qui tournent.
        """
        entree = self.point_entree(branche_entree, decalage)
        arret = self.point_ligne_arret(branche_entree, decalage)
        sortie = self.point_sortie(branche_sortie, decalage)

        entree_verticale = branche_entree in ("N", "S")
        sortie_verticale = branche_sortie in ("N", "S")

        if entree_verticale == sortie_verticale:
            # Tout droit : pas de point de virage nécessaire
            return [entree, arret, sortie]

        # Virage : le point de pivot est l'intersection des deux axes de voie
        if entree_verticale:
            pivot = (self.axe_voie_entrante(branche_entree, decalage),
                     self.axe_voie_sortante(branche_sortie, decalage))
        else:
            pivot = (self.axe_voie_sortante(branche_sortie, decalage),
                     self.axe_voie_entrante(branche_entree, decalage))
        return [entree, arret, pivot, sortie]

    # ---------- Zones ----------

    def zone_conflit(self):
        """Rectangle central (x1, y1, x2, y2) où les trajectoires se croisent."""
        return (self.cx - self.demi_zone, self.cy - self.demi_zone,
                self.cx + self.demi_zone, self.cy + self.demi_zone)

    def dans_zone_conflit(self, x, y):
        """Indique si un point se trouve dans l'intersection elle-même."""
        x1, y1, x2, y2 = self.zone_conflit()
        return x1 <= x <= x2 and y1 <= y <= y2

    def bande_passage_pieton(self, branche):
        """Rectangle (x1, y1, x2, y2) du passage piéton de cette branche."""
        d, f = config.PASSAGE_DEBUT, config.PASSAGE_FIN
        large = config.DEMI_CHAUSSEE + 14
        if branche == "N":
            return (self.cx - large, self.cy - f, self.cx + large, self.cy - d)
        if branche == "S":
            return (self.cx - large, self.cy + d, self.cx + large, self.cy + f)
        if branche == "W":
            return (self.cx - f, self.cy - large, self.cx - d, self.cy + large)
        return (self.cx + d, self.cy - large, self.cx + f, self.cy + large)

    def route_pieton(self, branche, sens_aller=True):
        """Trajectoire d'un piéton traversant le passage de cette branche.

        Les deux sens de circulation piétonne empruntent deux moitiés
        distinctes du passage (comme dans la réalité), ce qui évite que
        deux piétons se croisant soient comptés comme un accident."""
        x1, y1, x2, y2 = self.bande_passage_pieton(branche)
        milieu_x = (x1 + x2) / 2
        milieu_y = (y1 + y2) / 2
        decalage = 6 if sens_aller else -6

        if branche in ("N", "S"):
            voie = milieu_y + decalage
            depart, arrivee = (x1, voie), (x2, voie)
        else:
            voie = milieu_x + decalage
            depart, arrivee = (voie, y1), (voie, y2)

        if not sens_aller:
            depart, arrivee = arrivee, depart
        return [depart, arrivee]
