"""Classe mère de tous les usagers de la simulation.

Un usager suit une trajectoire faite de waypoints, avec une position
« sur la trajectoire » (x, y) et un décalage latéral dans sa voie. Cette
séparation est essentielle : le suivi de route, les feux et les lignes
d'arrêt raisonnent sur (x, y), tandis que la détection du véhicule de
devant, les collisions et l'affichage utilisent pos_effective(), qui
combine les deux.
"""

import itertools
import math

import config

# Compteur global : chaque usager créé reçoit un identifiant unique,
# réutilisé comme clé primaire en base de données.
_compteur_id = itertools.count(1)


class Usager:
    """Classe mère de tout ce qui circule. Gère le suivi d'une
    trajectoire (waypoints) avec une vitesse qui varie progressivement
    (pas de démarrage ni d'arrêt instantané, plus réaliste et
    indispensable pour respecter les distances de sécurité)."""

    longueur = 26.0
    largeur = 14.0

    def __init__(self, type_usager, branche, route, vitesse_max):
        """Place l'usager au premier point de sa trajectoire.

        Args:
            type_usager (str): catégorie ("vehicule_normal",
                "vehicule_urgence", "cycliste", "pieton"...), utilisée
                pour l'affichage et les statistiques.
            branche (str): branche d'entrée dans le carrefour (N/S/E/W).
            route (list): waypoints (x, y) à parcourir dans l'ordre.
            vitesse_max (float): vitesse de croisière en pixels/tick.
        """
        self.id = next(_compteur_id)
        self.type_usager = type_usager
        self.branche = branche              # branche d'entrée (N/S/E/W)
        self.route = list(route)
        self.index_waypoint = 1             # 0 = point de départ, on vise le suivant
        self.x, self.y = route[0]
        self.vitesse_max = vitesse_max
        self.vitesse = vitesse_max
        self.cap = (0.0, 0.0)               # vecteur unitaire de direction
        self.engage_intersection = False
        self.sortie_intersection = False
        self.tick_engagement = None     # départage les conflits de croisement
        self.ticks_bloque = 0           # temps passé immobilisé dans le carrefour

        # Décalage latéral dans la voie (positif = vers la droite).
        # (x, y) reste la position SUR la trajectoire, utilisée pour le
        # suivi de route, les feux et les lignes d'arrêt ; la position
        # réelle sur la chaussée est pos_effective().
        self.decalage = 0.0
        self.decalage_cible = 0.0
        self.cede_passage = False       # en train de serrer à droite pour une urgence
        self.ticks_cede = 0
        self._urgences_ignorees = set() # garde-fou : urgences pour lesquelles on a trop attendu
        self.est_sorti = False
        self.heure_entree = None
        self.heure_sortie = None
        self.arrete = False
        self._maj_cap()

    # ---------- Trajectoire ----------

    def cible(self):
        """Retourne le prochain waypoint visé, ou None en fin de trajectoire."""
        if self.index_waypoint < len(self.route):
            return self.route[self.index_waypoint]
        return None

    def _maj_cap(self):
        """Recalcule le vecteur unitaire de direction vers le waypoint visé."""
        cible = self.cible()
        if cible is None:
            return
        dx, dy = cible[0] - self.x, cible[1] - self.y
        distance = math.hypot(dx, dy)
        if distance > 1e-6:
            self.cap = (dx / distance, dy / distance)

    def ajuster_vitesse(self, vitesse_voulue):
        """Rapproche progressivement la vitesse courante de la consigne.

        Le freinage (config.DECELERATION) est volontairement bien plus
        fort que l'accélération : sans cela, la distance de freinage
        dépasserait la distance à laquelle on détecte le véhicule de
        devant, et les collisions seraient inévitables.

        Args:
            vitesse_voulue (float): consigne de vitesse en pixels/tick.
        """
        ecart = vitesse_voulue - self.vitesse
        if ecart > config.ACCELERATION:
            self.vitesse += config.ACCELERATION
        elif ecart < -config.DECELERATION:
            self.vitesse -= config.DECELERATION
        else:
            self.vitesse = vitesse_voulue
        self.vitesse = max(0.0, self.vitesse)
        self.arrete = self.vitesse < 0.05

    def avancer(self):
        """Déplace l'usager de `self.vitesse` le long de sa trajectoire.

        La boucle consomme la distance restante waypoint par waypoint :
        un usager rapide peut franchir plusieurs waypoints en un seul
        tick, notamment dans les virages où ils sont rapprochés. Marque
        `est_sorti` dès que la trajectoire est épuisée.
        """
        restant = self.vitesse
        while restant > 1e-6:
            cible = self.cible()
            if cible is None:
                self.est_sorti = True
                return
            dx, dy = cible[0] - self.x, cible[1] - self.y
            distance = math.hypot(dx, dy)
            if distance <= restant:
                self.x, self.y = cible
                self.index_waypoint += 1
                restant -= distance
                if self.cible() is None:
                    self.est_sorti = True
                    return
                self._maj_cap()
            else:
                self.x += restant * dx / distance
                self.y += restant * dy / distance
                restant = 0.0
        self._maj_cap()

    # ---------- Décalage latéral ----------

    def droite(self):
        """Vecteur unitaire pointant vers la droite du sens de marche
        (repère écran, y vers le bas)."""
        return (-self.cap[1], self.cap[0])

    def pos_effective(self):
        """Retourne la position réelle sur la chaussée (trajectoire + décalage).

        C'est cette position, et non (x, y), qui sert à la détection du
        véhicule de devant, aux collisions et à l'affichage.
        """
        dx, dy = self.droite()
        return (self.x + dx * self.decalage, self.y + dy * self.decalage)

    def maj_decalage(self):
        """Rapproche le décalage latéral courant de sa cible, pas à pas.

        Le déplacement est progressif plutôt qu'instantané pour que le
        fait de se ranger sur le côté reste visible et réaliste.
        """
        ecart = self.decalage_cible - self.decalage
        pas = config.VITESSE_DECALAGE
        if abs(ecart) <= pas:
            self.decalage = self.decalage_cible
        else:
            self.decalage += pas if ecart > 0 else -pas

    # ---------- Géométrie ----------

    def angle_degres(self):
        """Retourne l'orientation du cap en degrés, pour l'affichage."""
        return math.degrees(math.atan2(self.cap[1], self.cap[0]))

    def distance_a(self, autre):
        """Retourne la distance centre à centre avec un autre usager."""
        ax, ay = autre.pos_effective()
        bx, by = self.pos_effective()
        return math.hypot(ax - bx, ay - by)

    def rayon(self):
        """Retourne le rayon du cercle englobant, utilisé pour les collisions."""
        return max(self.longueur, self.largeur) / 2

    def __repr__(self):
        """Représentation courte et lisible, utile au débogage."""
        return f"<{self.type_usager} #{self.id} {self.branche} ({self.x:.0f},{self.y:.0f})>"
