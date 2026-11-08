"""Moteur de simulation.

Chaque tick applique, dans l'ordre :
  1. génération du trafic
  2. traitement des alertes V2I (couloir prioritaire)
  3. cycle des feux
  4. décision de vitesse pour chaque usager (règles du Code de la route)
  5. déplacement
  6. détection des collisions résiduelles
  7. sortie des usagers + métriques + écriture en base

Les règles appliquées côté véhicules/cyclistes :
  - distance de sécurité avec le véhicule précédent (freinage progressif)
  - arrêt à la ligne d'arrêt si le feu n'est pas vert
  - arrêt si un piéton est engagé sur le passage de leur branche
  - on ne s'engage pas dans l'intersection si elle est occupée par un
    usager venant d'une autre branche (dégagement)
  - interdiction d'emprunter la voie fermée par un couloir prioritaire
"""

import math
import random
import time
try:
    from reseau.securite import verifier_message as _verif_hmac
except ImportError:
    _verif_hmac = None

import config
from models.carrefour import Carrefour, AXE_DE_BRANCHE, DESTINATIONS, BRANCHE_OPPOSEE
from models.feu_circulation import FeuCirculation, VERT, ORANGE, ROUGE
from models.usagers_concrets import Pieton
from simulation.centrale_v2i import CentraleV2I
from simulation.generateur_trafic import GenerateurTrafic
from utils.metriques import Metriques


NOMS_USAGERS = {
    "vehicule_normal": "Véhicule",
    "vehicule_autonome": "Véhicule autonome",
    "vehicule_urgence": "Véhicule d'urgence",
    "cycliste": "Cycliste",
    "pieton": "Piéton",
}
NOMS_BRANCHES = {"N": "le nord", "S": "le sud", "E": "l'est", "W": "l'ouest"}


class MoteurSimulation:
    """Cœur métier de la simulation : fait vivre le carrefour tick par tick.

    Rassemble la géométrie, les feux, la centrale V2I et le générateur
    de trafic, et applique à chaque tick les règles de circulation qui
    déterminent la vitesse de chaque usager.
    """

    def __init__(self, dao=None):
        """Construit un carrefour vide, prêt à tourner.

        Args:
            dao (DAOMoteur): accès à la base pour journaliser les
                entrées, sorties et événements. None désactive toute
                écriture : la simulation reste utilisable sans base.
        """
        self.carrefour = Carrefour()
        self.feu = FeuCirculation()
        self.centrale = CentraleV2I(self.carrefour, self.feu)
        self.generateur = GenerateurTrafic(self.carrefour, self.centrale)
        self.metriques = Metriques()
        self.dao = dao
        self.usagers = []
        self.tick_courant = 0
        self._collisions_signalees = set()
        self.ajouts_en_attente = []     # usagers demandés par l'opérateur, pas encore entrés

    # ------------------------------------------------------------
    #  Boucle principale
    # ------------------------------------------------------------

    def tick(self):
        """Avance la simulation d'un pas de temps.

        L'ordre des étapes est important : les alertes V2I sont traitées
        avant le cycle des feux (pour pouvoir le préempter), et les
        décisions de vitesse sont toutes prises avant le moindre
        déplacement, afin que tous les usagers raisonnent sur le même
        état du carrefour.
        """
        self.tick_courant += 1
        self._traiter_ajouts_en_attente()
        self._faire_arriver_urgences()

        for u in self.generateur.generer():
            if getattr(u, "urgence", False):
                # Une urgence ne surgit pas : elle s'annonce d'abord par une alerte V2I
                u.priorite = self._tirer_priorite()
                self.centrale.recevoir_alerte(u, self.tick_courant)
                continue
            if self._place_occupee(u):
                continue  # la file remonte jusqu'à l'entrée : on n'insère pas
            u.heure_entree = time.time()
            self.usagers.append(u)
            if self.dao:
                self.dao.enregistrer_usager(u)

        self.centrale.traiter_alertes(self.usagers, self.tick_courant)
        self.feu.maj()

        actifs = [u for u in self.usagers if not u.est_sorti]
        vehicules = [u for u in actifs if not isinstance(u, Pieton)]
        pietons = [u for u in actifs if isinstance(u, Pieton)]

        self._gerer_serrage_a_droite(vehicules)

        for u in vehicules:
            self._decider_vitesse_vehicule(u, vehicules, pietons)
        for p in pietons:
            self._decider_vitesse_pieton(p, vehicules)

        for u in actifs:
            u.avancer()
            u.maj_decalage()
            self._maj_etat_intersection(u)
            coince = u.arrete and u.engage_intersection and not u.sortie_intersection
            u.ticks_bloque = u.ticks_bloque + 1 if coince else 0

        self._detecter_collisions(actifs)
        self._traiter_sorties()

    # ------------------------------------------------------------
    #  Alertes V2I : arrivée des véhicules annoncés
    # ------------------------------------------------------------

    @staticmethod
    def _tirer_priorite():
        """Tire un niveau de priorité (1 à 3) selon la répartition configurée.

        Returns:
            Le niveau tiré : 1 (urgence vitale), 2 (urgence) ou 3 (non
            urgente).
        """
        r, cumul = random.random(), 0.0
        for niveau, proba in sorted(config.REPARTITION_PRIORITES.items()):
            cumul += proba
            if r < cumul:
                return niveau
        return max(config.REPARTITION_PRIORITES)

    def _faire_arriver_urgences(self):
        """Les véhicules annoncés entrent dans la zone à l'heure prévue.
        Grâce à l'anticipation, leur voie est normalement déjà vide ; si
        l'entrée est encore occupée, ils réessaient au tick suivant."""
        for v in list(self.centrale.alertes_en_approche):
            if v.tick_arrivee > self.tick_courant or self._place_occupee(v):
                continue
            self.centrale.alertes_en_approche.remove(v)
            v.en_approche = False
            v.heure_entree = time.time()
            self.usagers.append(v)
            if self.dao:
                self.dao.enregistrer_usager(v)

    def _place_occupee(self, nouveau):
        """Empêche un usager d'apparaître sur un autre : quand la file
        d'attente remonte jusqu'au bord de la scène, le trafic entrant
        est simplement refusé (comme un carrefour saturé en amont)."""
        marge = config.DISTANCE_ARRET if not isinstance(nouveau, Pieton) else 18
        for autre in self.usagers:
            if autre.est_sorti:
                continue
            if math.hypot(autre.x - nouveau.x, autre.y - nouveau.y) < marge:
                return True
        return False

    # ------------------------------------------------------------
    #  Décision de vitesse : véhicules et cyclistes
    # ------------------------------------------------------------

    def _decider_vitesse_vehicule(self, u, vehicules, pietons):
        """Calcule et applique la consigne de vitesse d'un véhicule.

        Les contraintes s'empilent du moins au plus contraignant : on
        part de la vitesse maximale et chaque règle ne peut que la
        réduire (distance de sécurité, refus de priorité, piéton engagé,
        feu rouge).

        Args:
            u (Usager): le véhicule ou cycliste à piloter.
            vehicules (list): tous les véhicules et cyclistes actifs.
            pietons (list): tous les piétons actifs.
        """
        consigne = u.vitesse_max

        # --- 1. Distance de sécurité avec celui de devant ---
        leader = self._leader(u, vehicules)
        gap = leader[1] if leader else None
        if gap is not None:
            if gap < config.DISTANCE_ARRET:
                consigne = 0.0
            elif gap < config.DISTANCE_RALENTI:
                ratio = (gap - config.DISTANCE_ARRET) / (config.DISTANCE_RALENTI - config.DISTANCE_ARRET)
                consigne = min(consigne, u.vitesse_max * ratio)

        # --- 1 bis. On serre à droite pour une urgence : on ralentit fortement ---
        if u.cede_passage:
            consigne = min(consigne, u.vitesse_max * config.VITESSE_EN_CEDANT)

        # --- 2. Priorité au croisement dans l'intersection ---
        if self._doit_ceder_au_croisement(u, vehicules):
            consigne = 0.0

        # --- 3. Priorité au piéton du passage de SORTIE ---
        #     (un véhicule traverse deux passages : celui de sa branche
        #      d'entrée, puis celui de la branche par laquelle il ressort)
        if self._pieton_devant_en_sortie(u, pietons):
            consigne = 0.0

        # --- 4. Franchissement de la ligne d'arrêt ---
        if not u.engage_intersection:
            distance_arret = self._distance_a_la_ligne_arret(u)
            if distance_arret is not None and distance_arret > -5:
                if not self._peut_franchir(u, vehicules, pietons, distance_arret, gap):
                    consigne = min(consigne, self._vitesse_pour_s_arreter(u, distance_arret))

        u.ajuster_vitesse(consigne)

    # ------------------------------------------------------------
    #  Serrer à droite à l'approche d'un véhicule d'urgence
    # ------------------------------------------------------------

    def _gerer_serrage_a_droite(self, vehicules):
        """Comportement réel face à une sirène : les usagers qui ont une
        urgence derrière eux dans leur voie serrent à droite, ralentissent
        et ne s'engagent pas dans le carrefour devant elle. L'ambulance se
        rapproche de l'axe et remonte la file entre eux et la ligne médiane."""
        urgences = [v for v in vehicules if getattr(v, "urgence", False)]

        for u in vehicules:
            if getattr(u, "urgence", False):
                u.cede_passage = False
                remonte_file = (config.SERRAGE_ACTIF and not u.engage_intersection
                                and self._file_devant_urgence(u, vehicules))
                u.decalage_cible = config.DECALAGE_URGENCE if remonte_file else 0.0
                continue

            # Les cyclistes roulent déjà sur la bande au bord : pas besoin
            # de se ranger, l'ambulance passe à côté d'eux.
            if u.type_usager == "cycliste":
                continue

            ambulance, position = None, None
            if config.SERRAGE_ACTIF and not u.engage_intersection:
                ambulance, position = self._urgence_derriere(u, urgences)

            if ambulance is not None and position == "derriere":
                if ambulance.id in u._urgences_ignorees:
                    ambulance = None
                else:
                    u.ticks_cede += 1
                    if u.ticks_cede > config.DUREE_MAX_CEDE:
                        # Garde-fou : l'ambulance DERRIÈRE nous ne progresse
                        # pas (bloquée plus loin) ; on ne reste pas rangé
                        # indéfiniment, sinon tout le monde s'attendrait.
                        u._urgences_ignorees.add(ambulance.id)
                        ambulance = None
            # Si l'ambulance est à côté ou devant nous, elle ne nous attend
            # pas : aucun risque de blocage, on continue de céder jusqu'à ce
            # qu'elle ait quitté le carrefour (pas de garde-fou de durée).

            if ambulance is None:
                u.cede_passage = False
                u.ticks_cede = 0
                # On ne revient au centre de la voie que si aucune ambulance
                # n'est à notre hauteur (sinon on lui couperait la route).
                if not self._urgence_a_cote(u, urgences):
                    u.decalage_cible = 0.0
                continue

            u.cede_passage = True
            # On ne se range pas sur un cycliste qui roule à notre hauteur
            u.decalage_cible = 0.0 if self._cycliste_a_cote(u, vehicules) else config.DECALAGE_SERRAGE

    def _urgence_derriere(self, u, urgences):
        """Véhicule d'urgence qui arrive derrière u, dans la même voie.

        Returns:
            Un couple (urgence, position) où position vaut "derriere"
            si elle nous suit encore, ou "devant" si elle est à notre
            hauteur ou nous a dépassés. (None, None) si aucune urgence
            n'est détectée à portée.
        """
        for e in urgences:
            if e.est_sorti or e.branche != u.branche or e.sortie_intersection:
                continue
            dx, dy = u.x - e.x, u.y - e.y
            devant = dx * e.cap[0] + dy * e.cap[1]
            # Ambulance derrière nous, dans la même voie, à portée de sirène
            if 0 < devant < config.DETECTION_URGENCE:
                if e.cap[0] * u.cap[0] + e.cap[1] * u.cap[1] >= 0.6 \
                        and abs(-dx * e.cap[1] + dy * e.cap[0]) < 25:
                    return e, "derriere"
            # Ambulance à notre hauteur ou qui nous a dépassés, sans avoir
            # quitté le carrefour : on reste rangé et on ne s'engage pas
            # (sinon un tourne-à-gauche lui couperait la trajectoire).
            elif devant <= 0:
                return e, "devant"
        return None, None  # aucune urgence détectée

    def _urgence_a_cote(self, u, urgences):
        """Indique si une urgence est à hauteur de u, sur la même branche.

        Tant que c'est le cas, u ne doit pas se replacer au centre de sa
        voie : il se rabattrait sur le flanc de l'ambulance.
        """
        for e in urgences:
            if e.est_sorti or e.branche != u.branche:
                continue
            dx, dy = u.x - e.x, u.y - e.y
            if abs(dx * e.cap[0] + dy * e.cap[1]) < 50:
                return True
        return False

    def _file_devant_urgence(self, e, vehicules):
        """Y a-t-il des usagers ordinaires devant l'ambulance dans sa voie ?"""
        for u in vehicules:
            if u is e or getattr(u, "urgence", False) or u.est_sorti:
                continue
            if u.branche != e.branche or u.engage_intersection:
                continue
            dx, dy = u.x - e.x, u.y - e.y
            devant = dx * e.cap[0] + dy * e.cap[1]
            # -45 : on garde aussi le décalage tant qu'une voiture qu'on
            # vient de doubler est encore à notre hauteur (pas de rabattement).
            if -45 < devant < config.DETECTION_URGENCE:
                return True
        return False

    def _cycliste_a_cote(self, u, vehicules):
        """Indique si un cycliste roule à hauteur de u, sur la même branche.

        Garde-fou de sécurité : on ne serre pas à droite sur un cycliste.
        """
        for c in vehicules:
            if c.type_usager != "cycliste" or c.est_sorti or c.branche != u.branche:
                continue
            dx, dy = c.x - u.x, c.y - u.y
            if abs(dx * u.cap[0] + dy * u.cap[1]) < 35:
                return True
        return False

    def _vitesse_pour_s_arreter(self, u, distance):
        """Profil de freinage : plus on est près de la ligne, plus on ralentit."""
        if distance <= 3:
            return 0.0
        if distance >= config.DISTANCE_RALENTI:
            return u.vitesse_max
        return u.vitesse_max * (distance / config.DISTANCE_RALENTI)

    def _peut_franchir(self, u, vehicules, pietons, distance_arret, gap):
        """Décide si un véhicule a le droit de franchir sa ligne d'arrêt.

        Rassemble toutes les règles du code de la route applicables à
        l'entrée dans l'intersection : feu, voie réservée, préemption,
        priorité piéton, interdiction de bloquer le carrefour et refus
        de priorité en tourne-à-gauche.

        Args:
            u (Usager): le véhicule qui se présente à la ligne.
            vehicules (list): véhicules et cyclistes actifs.
            pietons (list): piétons actifs.
            distance_arret (float): distance signée à la ligne d'arrêt.
            gap (float): distance au véhicule de devant, ou None.

        Returns:
            True si le franchissement est autorisé, False sinon.
        """
        axe = AXE_DE_BRANCHE[u.branche]

        # a) Véhicule prioritaire avec couloir accordé : il passe, mais il
        #    freine quand même pour un piéton engagé et attend que l'axe
        #    perpendiculaire ait fini de dégager (sinon on crée l'accident
        #    qu'on cherche justement à éviter).
        if getattr(u, "couloir_accorde", False):
            if self._pieton_engage_sur(u.branche, pietons):
                return False
            return not self._axe_perpendiculaire_occupe(u, vehicules)

        # a bis) Usager rangé à droite pour laisser passer une urgence :
        #    il s'arrête avant la ligne et laisse l'ambulance passer devant.
        if u.cede_passage:
            return False

        # b) Feu. L'orange n'autorise que ceux qui ne peuvent plus s'arrêter.
        etat = self.feu.etat_axe(axe)
        if etat == ORANGE:
            if distance_arret > 25:
                return False
        elif etat != VERT:
            return False

        # c) Interdiction d'emprunter la voie réservée au couloir prioritaire
        if not self.centrale.destination_autorisee(u):
            return False

        # c bis) Préemption : pendant le passage du véhicule d'urgence,
        #    seule SA direction a le vert. Le trafic d'en face est retenu,
        #    sinon les véhicules qui tournent à gauche devant l'ambulance
        #    devraient lui céder le passage indéfiniment et la bloqueraient.
        if self.centrale.branche_retenue(u.branche):
            return False

        # d) Priorité au piéton engagé sur le passage de sa branche
        if self._pieton_engage_sur(u.branche, pietons):
            return False

        # e) Ne pas bloquer le carrefour : il faut de la place pour ressortir
        if not self._peut_degager(u, gap):
            return False

        # f) Dégagement et refus de priorité (tourne-à-gauche)
        if self._intersection_occupee_par_autre(u, vehicules):
            return False

        # g) Ne pas s'engager si une trajectoire sécante occupe déjà le
        #    carrefour, même sur le même axe (cas typique : un cycliste
        #    qui tourne à gauche coupe la voie d'en face)
        if self._trajectoire_secante_occupee(u, vehicules):
            return False

        return True

    def _trajectoire_secante_occupee(self, u, vehicules):
        """Occupation du carrefour par une trajectoire qui coupe la
        mienne. On ne regarde que ce qui se trouve réellement sur mon
        chemin : bloquer sur tout le carrefour ferait chuter le débit
        bien en dessous de la capacité réelle d'un carrefour à feux."""
        for autre in vehicules:
            if autre is u or autre.est_sorti:
                continue
            if not autre.engage_intersection or autre.sortie_intersection:
                continue
            alignement = autre.cap[0] * u.cap[0] + autre.cap[1] * u.cap[1]
            if alignement >= 0.6:
                continue
            dx, dy = autre.x - u.x, autre.y - u.y
            devant = dx * u.cap[0] + dy * u.cap[1]
            lateral = abs(-dx * u.cap[1] + dy * u.cap[0])
            if 0 < devant < config.PORTEE_CONFLIT and lateral < 70:
                return True
        return False

    def _axe_perpendiculaire_occupe(self, u, vehicules):
        """Indique si un usager de l'axe perpendiculaire occupe encore
        l'intersection. Même un véhicule prioritaire attend qu'elle soit
        dégagée, sinon on provoque l'accident qu'on cherche à éviter."""
        mon_axe = AXE_DE_BRANCHE[u.branche]
        return any(
            AXE_DE_BRANCHE[a.branche] != mon_axe
            and a.engage_intersection and not a.sortie_intersection
            and not a.est_sorti
            for a in vehicules if a is not u
        )

    def _passage_degage(self, p, vehicules):
        """Le piéton vérifie qu'aucun véhicule n'est en train de franchir
        ou d'approcher son passage avant de poser le pied sur la chaussée."""
        x1, y1, x2, y2 = self.carrefour.bande_passage_pieton(p.branche)
        cx_p, cy_p = (x1 + x2) / 2, (y1 + y2) / 2
        for v in vehicules:
            if v.est_sorti or v.vitesse < 0.2:
                continue
            if math.hypot(v.x - cx_p, v.y - cy_p) < 115:
                return False
        return True

    def _pieton_devant_en_sortie(self, u, pietons):
        """True si un piéton est engagé sur le passage que ce véhicule
        s'apprête à franchir en quittant le carrefour."""
        destination = getattr(u, "destination", None)
        if destination is None or not u.engage_intersection:
            return False
        if not self._pieton_engage_sur(destination, pietons):
            return False

        x1, y1, x2, y2 = self.carrefour.bande_passage_pieton(destination)
        centre = ((x1 + x2) / 2, (y1 + y2) / 2)
        dx, dy = centre[0] - u.x, centre[1] - u.y
        devant = dx * u.cap[0] + dy * u.cap[1]
        return 0 < devant < config.DISTANCE_RALENTI

    def _pieton_engage_sur(self, branche, pietons):
        """Indique si un piéton est engagé sur le passage de cette branche."""
        return any(p.engage and not p.est_sorti and p.branche == branche for p in pietons)

    def _intersection_occupee_par_autre(self, u, vehicules):
        """Règles de priorité réelles :

        - on ne s'engage pas si un usager de l'AXE PERPENDICULAIRE est
          encore dans l'intersection (dégagement de fin de phase) ;
        - en tourne-à-gauche, on cède le passage aux véhicules d'en face
          qui vont tout droit ou à droite (art. R415-5 du Code de la route).

        En revanche deux véhicules du même axe (Nord et Sud par exemple)
        ne se gênent pas : leurs voies sont parallèles et distinctes."""
        mon_axe = AXE_DE_BRANCHE[u.branche]

        for autre in vehicules:
            if autre is u or autre.est_sorti:
                continue
            if AXE_DE_BRANCHE[autre.branche] == mon_axe:
                continue
            if autre.engage_intersection and not autre.sortie_intersection:
                return True

        if self._tourne_a_gauche(u) and self._trafic_en_face(u, vehicules):
            return True

        return False

    def _tourne_a_gauche(self, u):
        """Indique si l'usager tourne à gauche, le cas qui coupe la voie d'en face."""
        destination = getattr(u, "destination", None)
        return destination is not None and destination == DESTINATIONS[u.branche]["gauche"]

    def _trafic_en_face(self, u, vehicules):
        """Véhicule venant d'en face, déjà engagé ou sur le point de
        l'être. Un véhicule arrêté (feu rouge, préemption) n'est pas une
        menace : lui céder le passage bloquerait tout le monde."""
        oppose = BRANCHE_OPPOSEE[u.branche]
        for autre in vehicules:
            if autre.est_sorti or autre.branche != oppose:
                continue
            engage = autre.engage_intersection and not autre.sortie_intersection
            distance = self._distance_a_la_ligne_arret(autre)
            arrive = (distance is not None and -10 < distance < 70
                      and autre.vitesse > 0.4
                      and not self.centrale.branche_retenue(autre.branche))
            if not (engage or arrive):
                continue
            if self._tourne_a_gauche(autre) and not engage:
                # Deux tourne-à-gauche face à face se croisent : on
                # départage par un ordre total strict, un seul cède.
                if autre.id < u.id:
                    return True
                continue
            return True
        return False

    def _peut_degager(self, u, gap):
        """On n'entre dans l'intersection que si on pourra en ressortir :
        interdiction de bloquer le carrefour derrière un bouchon."""
        if gap is None:
            return True
        longueur_traversee = 2 * config.DEMI_ZONE_CONFLIT + config.DISTANCE_ARRET
        return gap > longueur_traversee

    def _leader(self, u, vehicules):
        """Usager le plus proche DEVANT, circulant dans le même sens.

        Le filtre sur le cap est essentiel : sans lui, deux usagers dont
        les trajectoires se croisent se considèrent mutuellement comme
        "le véhicule de devant" et s'arrêtent tous les deux pour
        toujours (étreinte fatale). Les croisements sont gérés par les
        règles de priorité, pas par la distance de sécurité."""
        meilleur = None
        for autre in vehicules:
            if autre is u or autre.est_sorti:
                continue
            alignement = autre.cap[0] * u.cap[0] + autre.cap[1] * u.cap[1]
            if alignement < 0.6:
                continue  # trajectoire sécante : ce n'est pas un "précédent"
            # Positions réelles (décalage latéral compris) : c'est ce qui
            # permet à l'ambulance de remonter une file rangée à droite.
            ax, ay = autre.pos_effective()
            ux, uy = u.pos_effective()
            dx, dy = ax - ux, ay - uy
            avant = dx * u.cap[0] + dy * u.cap[1]
            if avant <= 0 or avant > config.PORTEE_DETECTION:
                continue
            lateral = abs(-dx * u.cap[1] + dy * u.cap[0])
            # L'ambulance exige un écart latéral franc avant de doubler :
            # une voiture à moitié rangée reste un obstacle devant elle.
            tolerance = (config.TOLERANCE_DEPASSEMENT_URGENCE
                         if getattr(u, "urgence", False) else config.TOLERANCE_LATERALE)
            if lateral > tolerance:
                continue
            if meilleur is None or avant < meilleur[1]:
                meilleur = (autre, avant)
        return meilleur

    def _doit_ceder_au_croisement(self, u, vehicules):
        """Conflit entre deux trajectoires sécantes dans l'intersection.

        L'ordre (instant d'engagement, puis identifiant) est un ordre
        total strict : dans une paire en conflit, un seul des deux cède.
        C'est ce qui garantit l'absence de blocage mutuel."""
        if not u.engage_intersection or u.sortie_intersection:
            return False

        # Garde-fou anti-interblocage : un usager immobilisé trop
        # longtemps au milieu du carrefour reprend la main pour dégager.
        if u.ticks_bloque > 45:
            return False

        for autre in vehicules:
            if autre is u or autre.est_sorti:
                continue
            if not autre.engage_intersection or autre.sortie_intersection:
                continue
            alignement = autre.cap[0] * u.cap[0] + autre.cap[1] * u.cap[1]
            if alignement >= 0.6:
                continue  # même sens : géré par la distance de sécurité
            # On ne cède qu'à un usager réellement SUR NOTRE CHEMIN
            # (devant nous). Céder à quelqu'un situé à côté ou derrière
            # ne sert à rien et crée des cycles d'attente.
            dx, dy = autre.x - u.x, autre.y - u.y
            devant = dx * u.cap[0] + dy * u.cap[1]
            lateral = abs(-dx * u.cap[1] + dy * u.cap[0])
            if not (0 < devant < config.PORTEE_CONFLIT and lateral < 40):
                continue
            cle_autre = (autre.tick_engagement or 0, autre.id)
            cle_moi = (u.tick_engagement or 0, u.id)
            if cle_autre < cle_moi:
                return True  # l'autre est arrivé le premier : je lui cède
        return False

    def _distance_a_la_ligne_arret(self, u):
        """Distance signée jusqu'à la ligne d'arrêt de sa branche
        (positive = pas encore franchie)."""
        decalage = config.DECALAGE_CYCLABLE if u.type_usager == "cycliste" else 0.0
        lx, ly = self.carrefour.point_ligne_arret(u.branche, decalage)
        dx, dy = lx - u.x, ly - u.y
        return dx * u.cap[0] + dy * u.cap[1]

    # ------------------------------------------------------------
    #  Décision de vitesse : piétons
    # ------------------------------------------------------------

    def _decider_vitesse_pieton(self, p, vehicules):
        """Décide si un piéton s'engage sur le passage, et à quelle vitesse.

        Un piéton déjà engagé termine toujours sa traversée : il est
        prioritaire et l'interrompre au milieu de la chaussée serait à
        la fois irréaliste et dangereux.

        Args:
            p (Pieton): le piéton à piloter.
            vehicules (list): véhicules actifs, pour vérifier que le
                passage est dégagé avant de s'engager.
        """
        if p.engage:
            p.ajuster_vitesse(p.vitesse_max)
            return

        axe = AXE_DE_BRANCHE[p.branche]
        # ROUGE strictement : à l'orange, des véhicules sont encore en
        # train de dégager le carrefour et franchissent le passage.
        feu_rouge_pour_voitures = self.feu.etat_axe(axe) == ROUGE
        # Préemption : pendant un couloir, tous les feux piétons passent
        # au rouge (les piétons déjà engagés terminent leur traversée).
        couloir_sur_cet_axe = self.centrale.preemption_renforcee()

        # Le piéton n'entre sur la chaussée que s'il a le temps de la
        # traverser complètement avant le retour du vert (comme un vrai
        # décompte piéton). Sinon il reste sur le trottoir.
        longueur = 2 * (config.DEMI_CHAUSSEE + 14)
        ticks_necessaires = longueur / max(p.vitesse_max, 0.1) + 40
        temps_disponible = self.feu.ticks_avant_vert(axe)

        voie_degagee = self._passage_degage(p, vehicules)

        if feu_rouge_pour_voitures and not couloir_sur_cet_axe \
                and temps_disponible >= ticks_necessaires and voie_degagee:
            p.engage = True
            p.ajuster_vitesse(p.vitesse_max)
        else:
            p.ajuster_vitesse(0.0)

    # ------------------------------------------------------------
    #  Suivi de l'état vis-à-vis de l'intersection
    # ------------------------------------------------------------

    def _maj_etat_intersection(self, u):
        """Met à jour les drapeaux d'entrée et de sortie de l'intersection.

        Mémorise aussi le tick d'engagement, qui sert à départager les
        conflits de croisement selon l'ordre d'arrivée.
        """
        if isinstance(u, Pieton):
            return
        dedans = self.carrefour.dans_zone_conflit(u.x, u.y)
        if dedans:
            if not u.engage_intersection:
                u.tick_engagement = self.tick_courant
            u.engage_intersection = True
        elif u.engage_intersection:
            u.sortie_intersection = True

    # ------------------------------------------------------------
    #  Collisions
    # ------------------------------------------------------------

    def _detecter_collisions(self, actifs):
        """Compte les collisions résiduelles entre usagers.

        Chaque paire n'est signalée qu'une fois : sans cela, deux
        véhicules restés en contact plusieurs ticks gonfleraient
        artificiellement le compteur d'accidents.
        """
        for i in range(len(actifs)):
            for j in range(i + 1, len(actifs)):
                a, b = actifs[i], actifs[j]
                if isinstance(a, Pieton) and isinstance(b, Pieton):
                    continue  # deux piétons qui se croisent s'évitent, ce n'est pas un accident
                paire = (min(a.id, b.id), max(a.id, b.id))
                if paire in self._collisions_signalees:
                    continue
                seuil = (a.rayon() + b.rayon()) * 0.75
                (axe_, aye_), (bxe_, bye_) = a.pos_effective(), b.pos_effective()
                if math.hypot(axe_ - bxe_, aye_ - bye_) < seuil:
                    self._collisions_signalees.add(paire)
                    self.metriques.enregistrer_collision(a, b)
                    if self.dao:
                        self.dao.log_evenement(a.id, "accident")
                        self.dao.log_evenement(b.id, "accident")

    # ------------------------------------------------------------
    #  Sorties
    # ------------------------------------------------------------

    def _traiter_sorties(self):
        """Horodate et journalise les usagers sortis, puis les retire."""
        encore_la = []
        for u in self.usagers:
            if u.est_sorti and u.heure_sortie is None:
                u.heure_sortie = time.time()
                self.metriques.enregistrer_passage(u)
                if self.dao:
                    self.dao.finaliser_usager(u)
            if not u.est_sorti:
                encore_la.append(u)
        self.usagers = encore_la

    # ------------------------------------------------------------
    #  Commandes de l'opérateur (boutons + / - du client)
    # ------------------------------------------------------------

    TYPES_USAGERS = ("vehicule_normal", "vehicule_autonome", "vehicule_urgence",
                     "cycliste", "pieton")

    def appliquer_commande(self, commande):
        """Applique une commande reçue du client. Appelée par la boucle
        principale du serveur ENTRE deux ticks : le moteur n'est jamais
        modifié depuis un autre thread.

        Les alertes issues d'un boîtier embarqué doivent porter une
        signature HMAC valide : sans cela, n'importe qui sur le réseau
        pourrait ouvrir un couloir prioritaire.

        Args:
            commande (dict): message {"action", "usager", ...} reçu.

        Returns:
            Le message de retour à afficher dans l'interface cliente.
        """
        # Vérification de la signature pour les alertes d'urgence
        if commande.get("usager") == "vehicule_urgence" and commande.get("source") == "boitier_embarque":
            if _verif_hmac and not _verif_hmac(commande):
                return "⚠️ Alerte rejetée : signature HMAC invalide (source non autorisée)"

        action = commande.get("action")
        type_usager = commande.get("usager")
        if type_usager not in self.TYPES_USAGERS:
            return f"Type d'usager inconnu : {type_usager}"
        if action == "ajouter":
            if type_usager == "vehicule_urgence":
                return self.annoncer_urgence(commande.get("priorite", 2))
            return self.ajouter_usager(type_usager)
        if action == "supprimer":
            return self.supprimer_usager(type_usager)
        return f"Action inconnue : {action}"

    def annoncer_urgence(self, priorite=2):
        """Bouton + des urgences : une alerte V2I est émise, le véhicule
        arrivera au carrefour DELAI_ALERTE plus tard.

        Args:
            priorite (int): niveau 1 à 3 ; toute valeur invalide est
                ramenée à 2 plutôt que rejetée, pour qu'une alerte mal
                formée n'empêche pas une intervention.

        Returns:
            Le message de confirmation destiné à l'interface.
        """
        try:
            priorite = int(priorite)
        except (TypeError, ValueError):
            priorite = 2
        if priorite not in config.NIVEAUX_PRIORITE:
            priorite = 2
        branche = random.choice(config.BRANCHES)
        v = self.generateur.creer_usager("vehicule_urgence", branche)
        v.priorite = priorite
        self.centrale.recevoir_alerte(v, self.tick_courant)
        delai = config.DELAI_ALERTE / config.TICKS_PAR_SECONDE
        return (f"Alerte P{priorite} ({config.NIVEAUX_PRIORITE[priorite].lower()}) : "
                f"véhicule d'urgence depuis {NOMS_BRANCHES[branche]}, arrivée dans {delai:.0f} s")

    def ajouter_usager(self, type_usager):
        """Ajoute un usager sur une entrée libre. Si toutes les entrées
        sont occupées (bouchon), la demande est mise en attente et
        l'usager entrera dès qu'une place se libère.

        Args:
            type_usager (str): type d'usager demandé par l'opérateur.

        Returns:
            Le message de confirmation destiné à l'interface.
        """
        branche = self._inserer(type_usager)
        if branche:
            return f"{NOMS_USAGERS[type_usager]} ajouté(e) depuis {NOMS_BRANCHES[branche]}"
        self.ajouts_en_attente.append(type_usager)
        return (f"Entrées occupées : {NOMS_USAGERS[type_usager].lower()} en attente, "
                f"il entrera dès qu'une place se libère ({len(self.ajouts_en_attente)} en attente)")

    def _inserer(self, type_usager):
        """Tente d'insérer l'usager sur une branche libre. Retourne la
        branche utilisée, ou None si aucune place n'est disponible.

        Les branches sont essayées dans un ordre aléatoire pour ne pas
        privilégier toujours la même entrée.
        """
        branches = list(config.BRANCHES)
        random.shuffle(branches)
        for branche in branches:
            usager = self.generateur.creer_usager(type_usager, branche)
            if usager is None or self._place_occupee(usager):
                continue
            usager.heure_entree = time.time()
            self.usagers.append(usager)
            if self.dao:
                self.dao.enregistrer_usager(usager)
            return branche
        return None

    def _traiter_ajouts_en_attente(self):
        """Réessaie d'insérer les usagers demandés alors que tout était plein."""
        restants = []
        for type_usager in self.ajouts_en_attente:
            if not self._inserer(type_usager):
                restants.append(type_usager)
        self.ajouts_en_attente = restants

    def supprimer_usager(self, type_usager):
        """Retire l'usager de ce type le plus récemment arrivé. On évite
        de retirer quelqu'un au milieu du carrefour quand c'est possible.

        Args:
            type_usager (str): type d'usager à retirer.

        Returns:
            Le message de confirmation destiné à l'interface.
        """
        # Urgence : on annule d'abord une alerte dont le véhicule n'est pas encore arrivé
        if type_usager == "vehicule_urgence":
            annulee = self.centrale.annuler_derniere_alerte()
            if annulee is not None:
                return f"Alerte P{annulee.priorite} annulée (véhicule #{annulee.id} pas encore arrivé)"

        # Annuler d'abord un ajout encore en attente, s'il y en a un
        if type_usager in self.ajouts_en_attente:
            self.ajouts_en_attente.remove(type_usager)
            return f"Ajout en attente annulé ({NOMS_USAGERS[type_usager].lower()})"

        candidats = [u for u in self.usagers
                     if u.type_usager == type_usager and not u.est_sorti]
        if not candidats:
            return f"Aucun(e) {NOMS_USAGERS[type_usager].lower()} à supprimer"
        hors_carrefour = [u for u in candidats if not u.engage_intersection]
        cible = max(hors_carrefour or candidats, key=lambda u: u.id)
        self.usagers.remove(cible)
        return f"{NOMS_USAGERS[type_usager]} #{cible.id} supprimé(e)"

    # ------------------------------------------------------------
    #  Sérialisation pour le réseau
    # ------------------------------------------------------------

    def etat_reseau(self):
        """Sérialise l'état complet du carrefour pour l'envoi réseau.

        Returns:
            Un dict JSON-sérialisable contenant les usagers visibles
            (position effective, cap, état), les feux, l'état de la
            centrale V2I et les statistiques courantes.
        """
        return {
            "type": "etat",
            "tick": self.tick_courant,
            "usagers": [
                {
                    "id": u.id,
                    "type": u.type_usager,
                    "x": round(u.pos_effective()[0], 1),
                    "y": round(u.pos_effective()[1], 1),
                    "cede": u.cede_passage,
                    "priorite": getattr(u, "priorite", None),
                    "angle": round(u.angle_degres(), 1),
                    "arrete": u.arrete,
                    "devie": getattr(u, "devie", False),
                }
                for u in self.usagers if not u.est_sorti
            ],
            "feu": self.feu.etat_pour_affichage(),
            "v2i": self.centrale.vers_dict(self.tick_courant),
            "stats": self.metriques.vers_dict(),
            "en_attente": len(self.ajouts_en_attente),
        }
