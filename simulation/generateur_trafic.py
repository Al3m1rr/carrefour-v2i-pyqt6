"""Création des usagers à l'entrée du carrefour."""

import random

import config
from models.carrefour import DESTINATIONS
from models.usagers_concrets import Vehicule, Cycliste, Pieton


class GenerateurTrafic:
    """Crée les usagers à l'entrée du carrefour. Tient compte du couloir
    prioritaire : aucun véhicule ordinaire n'est introduit sur une voie
    de sortie fermée, ni sur la branche empruntée par l'ambulance."""

    def __init__(self, carrefour, centrale):
        """Mémorise la géométrie et la centrale V2I à consulter.

        Args:
            carrefour (Carrefour): fournit les trajectoires à suivre.
            centrale (CentraleV2I): consultée pour savoir quelles voies
                sont réservées aux secours à cet instant.
        """
        self.carrefour = carrefour
        self.centrale = centrale

    def _tirer_destination(self, branche):
        """Tire au sort une destination selon les probabilités configurées.

        Args:
            branche (str): branche d'entrée de l'usager.

        Returns:
            La branche de sortie (tout droit, à gauche ou à droite).
        """
        r = random.random()
        if r < config.PROBA_TOUT_DROIT:
            cle = "tout_droit"
        elif r < config.PROBA_TOUT_DROIT + config.PROBA_GAUCHE:
            cle = "gauche"
        else:
            cle = "droite"
        return DESTINATIONS[branche][cle]

    def _destination_valide(self, branche, essais=4):
        """Tire une destination qui n'emprunte pas la voie fermée.

        Args:
            branche (str): branche d'entrée de l'usager.
            essais (int): nombre de tirages avant d'abandonner. On ne
                boucle pas indéfiniment : si presque toutes les sorties
                sont fermées, mieux vaut ne pas faire entrer l'usager.

        Returns:
            Une branche de sortie autorisée, ou None après trop d'essais.
        """
        for _ in range(essais):
            destination = self._tirer_destination(branche)
            if not self.centrale.sortie_interdite(destination):
                return destination
        return None

    def _branche_bloquee(self, branche):
        """Pendant un couloir, on ne fait plus entrer de véhicules
        ordinaires derrière l'ambulance sur sa propre voie.

        Sans cette règle, la voie qu'on vient de vider se remplirait
        aussitôt par l'arrière et le couloir perdrait tout son intérêt.
        """
        couloir = self.centrale.couloir
        return couloir is not None and couloir.branche_entree == branche

    def creer_usager(self, type_usager, branche):
        """Crée un usager du type demandé sur la branche donnée, en
        respectant la voie réservée. Retourne None si c'est impossible
        (branche fermée aux usagers ordinaires, aucune sortie légale).

        Args:
            type_usager (str): "vehicule_normal", "vehicule_autonome",
                "vehicule_urgence", "cycliste" ou "pieton".
            branche (str): branche d'entrée (N/S/E/W).

        Returns:
            L'usager construit, ou None si la voie lui est interdite.
            Les véhicules d'urgence vont toujours tout droit et ne sont
            jamais bloqués par une voie réservée.
        """
        if type_usager == "pieton":
            route = self.carrefour.route_pieton(branche, random.random() < 0.5)
            return Pieton(branche, route)

        if type_usager == "vehicule_urgence":
            destination = DESTINATIONS[branche]["tout_droit"]
            route = self.carrefour.construire_route(branche, destination)
            return Vehicule(branche, destination, route, urgence=True)

        # Usagers ordinaires : interdits sur la route réservée aux secours
        if self._branche_bloquee(branche):
            return None
        destination = self._destination_valide(branche)
        if destination is None:
            return None

        if type_usager == "cycliste":
            route = self.carrefour.construire_route(branche, destination, config.DECALAGE_CYCLABLE)
            return Cycliste(branche, destination, route)

        route = self.carrefour.construire_route(branche, destination)
        return Vehicule(branche, destination, route,
                        autonome=(type_usager == "vehicule_autonome"))

    def generer(self):
        """Apparitions aléatoires selon les densités configurées.

        Appelée à chaque tick : chaque branche a une petite probabilité
        de voir arriver un véhicule, un cycliste et un piéton.

        Returns:
            La liste des usagers créés pendant ce tick.
        """
        nouveaux = []
        for branche in config.BRANCHES:
            if random.random() < config.DENSITE_VEHICULES:
                if random.random() < config.PROBABILITE_URGENCE:
                    type_usager = "vehicule_urgence"
                elif random.random() < config.PROPORTION_AUTONOMES:
                    type_usager = "vehicule_autonome"
                else:
                    type_usager = "vehicule_normal"
                self._ajouter_si_possible(nouveaux, type_usager, branche)

            if random.random() < config.DENSITE_CYCLISTES:
                self._ajouter_si_possible(nouveaux, "cycliste", branche)

            if random.random() < config.DENSITE_PIETONS:
                self._ajouter_si_possible(nouveaux, "pieton", branche)
        return nouveaux

    def _ajouter_si_possible(self, liste, type_usager, branche):
        """Ajoute l'usager à la liste, sauf si sa création a été refusée."""
        usager = self.creer_usager(type_usager, branche)
        if usager is not None:
            liste.append(usager)
