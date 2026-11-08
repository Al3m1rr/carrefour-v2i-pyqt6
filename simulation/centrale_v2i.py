"""Centrale V2I (infrastructure du carrefour connecté).

Fonctionnement :

1. ALERTE ANTICIPÉE. Un véhicule d'urgence émet une alerte depuis son
   application embarquée AVANT d'arriver au carrefour (config.DELAI_ALERTE).
   L'alerte contient son itinéraire (branche d'entrée -> sortie), son
   instant d'arrivée prévu et son NIVEAU DE PRIORITÉ (1 vital, 2 urgent,
   3 non urgent).

2. VOIE RÉSERVÉE. La centrale accorde un couloir au véhicule : sa route
   passe en "sens interdit sauf urgences", son axe passe au vert, les
   usagers ordinaires qui comptaient l'emprunter sont déviés. Comme
   l'alerte arrive en avance, la voie a le temps de se vider : elle est
   libre quand l'ambulance arrive.

3. PRÉEMPTION RENFORCÉE à l'arrivée. Quand le bénéficiaire entre dans la
   zone du carrefour, le trafic d'en face est retenu et les feux piétons
   passent au rouge. Pendant l'approche on s'en abstient, pour ne pas
   bloquer piétons et trafic inutilement longtemps.

4. ARBITRAGE. Un seul couloir à la fois (sauf itinéraires compatibles).
   Entre deux urgences dont les trajectoires se croisent, on sert la plus
   prioritaire ; à priorité égale, celle qui arrive la première.
   Si une urgence PLUS prioritaire se présente alors que le bénéficiaire
   actuel est encore en approche, le couloir lui est réattribué. Une
   fois le bénéficiaire arrivé dans la zone, on ne lui retire plus
   jamais son couloir (sécurité).
"""

import random

import config
from models.carrefour import DESTINATIONS, AXE_DE_BRANCHE, BRANCHE_OPPOSEE

# Garde-fou : un couloir ne peut jamais rester ouvert indéfiniment
# (compté à partir de l'arrivée du bénéficiaire dans la zone).
DUREE_MAX_COULOIR = 900   # ticks (30 s)


class Couloir:
    """Voie réservée accordée à un véhicule d'urgence donné.

    Mémorise l'itinéraire protégé (entrée, sortie, axe) afin que la
    centrale puisse décider quels autres usagers peuvent l'emprunter et
    lesquels doivent être déviés.
    """

    def __init__(self, vehicule, tick_ouverture=0):
        """Ouvre un couloir pour le véhicule donné.

        Args:
            vehicule (Vehicule): le bénéficiaire du couloir.
            tick_ouverture (int): tick auquel le couloir est ouvert,
                servant à mesurer sa durée de vie.
        """
        self.vehicule_id = vehicule.id
        self.priorite = vehicule.priorite
        self.tick_ouverture = tick_ouverture
        self.branche_entree = vehicule.branche
        self.branche_sortie = vehicule.destination
        self.axe = AXE_DE_BRANCHE[vehicule.branche]
        self.beneficiaire_present = False

    def vers_dict(self):
        """Sérialise l'état du couloir pour l'envoi aux clients."""
        return {
            "vehicule_id": self.vehicule_id,
            "priorite": self.priorite,
            "entree": self.branche_entree,
            "sortie": self.branche_sortie,
            "axe": self.axe,
            "beneficiaire_present": self.beneficiaire_present,
        }


class CentraleV2I:
    """Infrastructure connectée du carrefour : reçoit les alertes des
    véhicules d'urgence, accorde les voies réservées, arbitre entre
    plusieurs urgences et dévie les usagers gênants."""

    def __init__(self, carrefour, feu):
        """Prépare la centrale sans aucune alerte en cours.

        Args:
            carrefour (Carrefour): géométrie, pour recalculer les
                itinéraires des usagers déviés.
            feu (FeuCirculation): feux à préempter pendant un couloir.
        """
        self.carrefour = carrefour
        self.feu = feu
        self.couloir = None
        self.alertes_en_approche = []   # véhicules annoncés, pas encore arrivés
        self.file_attente = []
        self._deja_servis = set()
        self.nb_couloirs_ouverts = 0
        self.nb_deviations = 0
        self.nb_reattributions = 0
        self._toutes = []
        self._tick = 0

    # ------------------------------------------------------------
    #  Réception des alertes
    # ------------------------------------------------------------

    def recevoir_alerte(self, vehicule, tick_courant):
        """Message V2I : 'j'arrive par telle branche, je vais tout droit,
        j'arrive dans DELAI_ALERTE ticks, ma priorité est N'.

        Le véhicule n'entre pas tout de suite : il reste « en approche »
        le temps que la voie se vide devant lui.

        Args:
            vehicule (Vehicule): l'émetteur de l'alerte.
            tick_courant (int): tick de réception, base du compte à rebours.
        """
        vehicule.en_approche = True
        vehicule.tick_arrivee = tick_courant + config.DELAI_ALERTE
        self.alertes_en_approche.append(vehicule)

    def annuler_derniere_alerte(self):
        """Annule l'alerte la plus récente dont le véhicule n'est pas arrivé.

        Returns:
            Le véhicule dont l'alerte est annulée, ou None s'il n'y en a
            aucune en approche.
        """
        if not self.alertes_en_approche:
            return None
        return self.alertes_en_approche.pop()

    # ------------------------------------------------------------
    #  Boucle de décision (appelée à chaque tick)
    # ------------------------------------------------------------

    def traiter_alertes(self, usagers, tick_courant=0):
        """Met à jour l'attribution du couloir prioritaire, à chaque tick.

        Enchaîne quatre décisions : fermer le couloir devenu inutile,
        le réattribuer à une urgence plus prioritaire encore en approche,
        en ouvrir un nouveau si aucun n'est actif, puis recalculer qui a
        le droit d'emprunter la voie réservée.

        Args:
            usagers (list): tous les usagers présents dans la simulation.
            tick_courant (int): tick courant de la simulation.
        """
        presentes = [u for u in usagers
                     if getattr(u, "urgence", False) and not u.est_sorti]
        for u in presentes:
            if u.sortie_intersection:
                self._deja_servis.add(u.id)
        toutes = presentes + self.alertes_en_approche
        self._toutes = toutes
        self._tick = tick_courant

        # -- Fermeture : bénéficiaire passé, disparu (alerte annulée), ou délai dépassé --
        if self.couloir is not None:
            benef = self._trouver(toutes, self.couloir.vehicule_id)
            present = benef is not None and not benef.en_approche
            self.couloir.beneficiaire_present = present
            debut = max(self.couloir.tick_ouverture, benef.tick_arrivee if benef else 0)
            expire = present and (tick_courant - debut) > DUREE_MAX_COULOIR
            if benef is None or benef.sortie_intersection or expire:
                self._deja_servis.add(self.couloir.vehicule_id)
                self._fermer_couloir()

        # -- Réattribution : une urgence plus prioritaire, sur une trajectoire
        #    qui croise, alors que le bénéficiaire n'est pas encore arrivé --
        if self.couloir is not None and not self.couloir.beneficiaire_present:
            plus_prioritaire = [
                u for u in toutes
                if u.id not in self._deja_servis
                and u.priorite < self.couloir.priorite
                and not self._compatible(u)
            ]
            if plus_prioritaire:
                self.nb_reattributions += 1
                self._fermer_couloir()   # le bénéficiaire actuel redevient candidat

        # -- Ouverture : priorité d'abord, puis ordre d'arrivée --
        if self.couloir is None:
            candidats = [u for u in toutes if u.id not in self._deja_servis]
            if candidats:
                elu = min(candidats, key=lambda u: (u.priorite, u.tick_arrivee, u.id))
                self._ouvrir_couloir(elu, usagers, tick_courant)
                self.couloir.beneficiaire_present = not elu.en_approche

        # -- Droit d'emprunter la voie réservée --
        for u in toutes:
            u.couloir_accorde = self._peut_emprunter_couloir(u)

        self.file_attente = [u.id for u in toutes
                             if u.id not in self._deja_servis and not u.couloir_accorde]

    @staticmethod
    def _trouver(liste, identifiant):
        """Retrouve un usager par son identifiant, ou None s'il a disparu."""
        return next((u for u in liste if u.id == identifiant), None)

    def _compatible(self, u):
        """Itinéraire compatible avec le couloir actif : même itinéraire, ou
        même axe en sens opposé tout droit (voies parallèles)."""
        if self.couloir is None:
            return False
        meme_itineraire = (u.branche == self.couloir.branche_entree
                           and u.destination == self.couloir.branche_sortie)
        sens_oppose = (
            AXE_DE_BRANCHE[u.branche] == self.couloir.axe
            and u.destination == DESTINATIONS[u.branche]["tout_droit"]
            and self.couloir.branche_sortie == DESTINATIONS[self.couloir.branche_entree]["tout_droit"]
        )
        return meme_itineraire or sens_oppose

    def _peut_emprunter_couloir(self, u):
        """Indique si cette urgence a le droit d'emprunter la voie réservée."""
        if self.couloir is None:
            return False
        return u.id == self.couloir.vehicule_id or self._compatible(u)

    def _ouvrir_couloir(self, vehicule, usagers, tick_courant=0):
        """Ouvre un couloir : force les feux et dévie les usagers gênants."""
        self.couloir = Couloir(vehicule, tick_courant)
        self.nb_couloirs_ouverts += 1
        self.feu.forcer(self.couloir.axe)
        self._devier_vehicules_genants(usagers)

    def _fermer_couloir(self):
        """Ferme le couloir et rend la main au cycle normal des feux."""
        self.couloir = None
        self.feu.liberer()

    # ------------------------------------------------------------
    #  Déviation des véhicules qui occupent le couloir
    # ------------------------------------------------------------

    def _devier_vehicules_genants(self, usagers):
        """Détourne les usagers qui comptaient emprunter la voie réservée.

        Les véhicules déjà engagés dans l'intersection ne sont jamais
        déviés : changer leur trajectoire en plein carrefour provoquerait
        des collisions.
        """
        for u in usagers:
            if u.est_sorti or getattr(u, "urgence", False):
                continue
            if not hasattr(u, "destination") or u.engage_intersection:
                continue
            if u.destination != self.couloir.branche_sortie:
                continue
            nouvelle = self._destination_de_repli(u.branche)
            if nouvelle is None:
                continue
            self._reconstruire_itineraire(u, nouvelle)
            u.devie = True
            self.nb_deviations += 1

    def _destination_de_repli(self, branche):
        """Choisit au hasard une sortie qui n'est pas celle du couloir."""
        options = [d for d in DESTINATIONS[branche].values()
                   if d != self.couloir.branche_sortie]
        return random.choice(options) if options else None

    def _reconstruire_itineraire(self, usager, nouvelle_destination):
        """Recalcule la trajectoire d'un usager dévié, depuis sa position.

        Seuls les waypoints situés devant lui sont conservés : repartir
        du début de la nouvelle route le ferait reculer brutalement.
        """
        decalage = config.DECALAGE_CYCLABLE if usager.type_usager == "cycliste" else 0.0
        nouvelle_route = self.carrefour.construire_route(usager.branche, nouvelle_destination, decalage)
        restants = [p for p in nouvelle_route[1:] if self._est_devant(usager, p)]
        if not restants:
            restants = [nouvelle_route[-1]]
        usager.route = [(usager.x, usager.y)] + restants
        usager.index_waypoint = 1
        usager.destination = nouvelle_destination
        usager._maj_cap()

    def _est_devant(self, usager, point):
        """Indique si un point est devant l'usager (produit scalaire > 0)."""
        dx, dy = point[0] - usager.x, point[1] - usager.y
        return dx * usager.cap[0] + dy * usager.cap[1] > 0

    # ------------------------------------------------------------
    #  Règles applicables aux autres usagers
    # ------------------------------------------------------------

    def preemption_renforcee(self):
        """Trafic d'en face retenu + piétons au rouge : dans les dernières
        secondes de l'approche, puis tant que le bénéficiaire est là. Plus
        tôt, cela bloquerait piétons et trafic inutilement longtemps ; plus
        tard, les véhicules qui tournent à gauche devant l'ambulance
        n'auraient pas le temps de dégager."""
        if self.couloir is None:
            return False
        if self.couloir.beneficiaire_present:
            return True
        benef = self._trouver(self._toutes, self.couloir.vehicule_id)
        return (benef is not None
                and benef.tick_arrivee - self._tick <= config.PREEMPTION_AVANT_ARRIVEE)

    def branche_retenue(self, branche):
        """Indique si le trafic de cette branche est retenu (trafic d'en face).

        Le trafic venant d'en face est bloqué pendant la préemption
        renforcée : sinon, les véhicules qui tournent à gauche devant
        l'ambulance lui céderaient le passage indéfiniment.
        """
        if not self.preemption_renforcee():
            return False
        return branche == BRANCHE_OPPOSEE[self.couloir.branche_entree]

    def couloir_actif(self):
        """Indique si une voie réservée est actuellement ouverte."""
        return self.couloir is not None

    def sortie_interdite(self, branche_sortie):
        """Indique si cette voie de sortie est réservée aux secours."""
        return self.couloir is not None and self.couloir.branche_sortie == branche_sortie

    def destination_autorisee(self, usager):
        """Indique si cet usager peut rejoindre sa destination actuelle.

        Les véhicules d'urgence ne sont jamais bloqués par un couloir.
        """
        if getattr(usager, "urgence", False):
            return True
        return not self.sortie_interdite(getattr(usager, "destination", None))

    def branches_sens_interdit(self):
        """Retourne les branches en sens interdit « sauf urgences ».

        Returns:
            Un dict {"entree": [...], "sortie": [...]} des branches où
            le panneau doit s'allumer côté client.
        """
        if not self.couloir:
            return {"entree": [], "sortie": []}
        return {"entree": [self.couloir.branche_entree],
                "sortie": [self.couloir.branche_sortie]}

    # ------------------------------------------------------------
    #  Sérialisation
    # ------------------------------------------------------------

    def vers_dict(self, tick_courant=0):
        """Sérialise l'état complet de la centrale pour le panneau V2I.

        Args:
            tick_courant (int): tick courant, pour calculer les comptes
                à rebours d'arrivée affichés côté client.

        Returns:
            Un dict décrivant le couloir actif, les sens interdits et la
            liste des alertes en cours, triées par priorité.
        """
        alertes = []
        for u in sorted(self._toutes, key=lambda v: (v.priorite, v.tick_arrivee, v.id)):
            if u.id in self._deja_servis:
                continue
            if u.couloir_accorde:
                statut = "voie réservée"
            else:
                statut = "en attente"
            alertes.append({
                "id": u.id,
                "priorite": u.priorite,
                "entree": u.branche,
                "sortie": u.destination,
                "en_approche": u.en_approche,
                "arrivee_dans": round(max(0, u.tick_arrivee - tick_courant) / config.TICKS_PAR_SECONDE, 1),
                "statut": statut,
            })
        return {
            "actif": self.couloir is not None,
            "couloir": self.couloir.vers_dict() if self.couloir else None,
            "sens_interdit": self.branches_sens_interdit(),
            "branche_retenue": (BRANCHE_OPPOSEE[self.couloir.branche_entree]
                                if self.preemption_renforcee() else None),
            "urgences_en_attente": len(self.file_attente),
            "alertes": alertes,
            "nb_reattributions": self.nb_reattributions,
        }
