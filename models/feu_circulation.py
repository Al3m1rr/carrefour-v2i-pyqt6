"""Cycle des feux tricolores du carrefour, et leur préemption V2I."""

import config

ROUGE, ORANGE, VERT = "rouge", "orange", "vert"


class FeuCirculation:
    """Feux des deux axes (NS et EO). Un seul axe vert à la fois, avec
    une phase de dégagement "tout rouge" entre les deux -- comme dans un
    vrai carrefour, c'est ce qui évite les collisions au changement.

    Quand la centrale V2I accorde un couloir prioritaire, l'axe concerné
    passe au vert et y reste tant que le couloir est actif."""

    def __init__(self):
        """Démarre le cycle avec l'axe nord-sud au vert."""
        self.chrono = 0
        self.etat_ns = VERT
        self.etat_eo = ROUGE
        self.axe_force = None

    def forcer(self, axe):
        """Force un axe au vert et suspend le cycle normal (préemption V2I).

        Args:
            axe (str): 'NS' ou 'EO', l'axe emprunté par le véhicule
                prioritaire. Appelé par la centrale V2I.
        """
        self.axe_force = axe
        if axe == "NS":
            self.etat_ns, self.etat_eo = VERT, ROUGE
        else:
            self.etat_ns, self.etat_eo = ROUGE, VERT

    def liberer(self):
        """Reprend le cycle normal là où il s'était arrêté. On ne remet
        surtout pas le chrono à zéro : cela redonnerait systématiquement
        la main au même axe et affamerait l'autre."""
        self.axe_force = None
        self.etat_ns, self.etat_eo = ROUGE, ROUGE

    def maj(self):
        """Avance le cycle d'un tick, sauf si une préemption est active.

        Le cycle complet enchaîne, pour chaque axe : vert, orange, puis
        une phase « tout rouge » de dégagement qui laisse le carrefour
        se vider avant de donner le vert à l'axe perpendiculaire.
        """
        if self.axe_force:
            return  # priorité en cours : le cycle normal est suspendu

        self.chrono += 1
        phase = config.DUREE_VERT + config.DUREE_ORANGE + config.DUREE_TOUT_ROUGE
        t = self.chrono % (2 * phase)

        if t < config.DUREE_VERT:
            self.etat_ns, self.etat_eo = VERT, ROUGE
        elif t < config.DUREE_VERT + config.DUREE_ORANGE:
            self.etat_ns, self.etat_eo = ORANGE, ROUGE
        elif t < phase:
            self.etat_ns, self.etat_eo = ROUGE, ROUGE
        elif t < phase + config.DUREE_VERT:
            self.etat_ns, self.etat_eo = ROUGE, VERT
        elif t < phase + config.DUREE_VERT + config.DUREE_ORANGE:
            self.etat_ns, self.etat_eo = ROUGE, ORANGE
        else:
            self.etat_ns, self.etat_eo = ROUGE, ROUGE

    def etat_axe(self, axe):
        """Retourne la couleur courante du feu d'un axe ('NS' ou 'EO')."""
        return self.etat_ns if axe == "NS" else self.etat_eo

    def peut_franchir(self, axe):
        """Le vert autorise le franchissement. L'orange aussi si on ne
        peut plus s'arrêter -- géré par l'appelant via la distance."""
        return self.etat_axe(axe) == VERT

    def ticks_avant_vert(self, axe):
        """Temps restant avant que cet axe repasse au vert. Permet au
        piéton de ne s'engager que s'il a le temps de traverser.

        Args:
            axe (str): 'NS' ou 'EO'.

        Returns:
            Nombre de ticks avant le prochain vert ; 0 si l'axe est déjà
            vert, et une valeur très grande si une préemption bloque
            l'axe opposé pour une durée indéterminée.
        """
        if self.axe_force:
            return 0 if self.axe_force == axe else 10_000

        phase = config.DUREE_VERT + config.DUREE_ORANGE + config.DUREE_TOUT_ROUGE
        cycle = 2 * phase
        t = self.chrono % cycle

        if axe == "NS":
            return 0 if t < config.DUREE_VERT else (cycle - t) % cycle
        return 0 if phase <= t < phase + config.DUREE_VERT else (phase - t) % cycle

    def etat_pour_affichage(self):
        """Retourne l'état des deux axes, sérialisable pour le réseau."""
        return {"NS": self.etat_ns, "EO": self.etat_eo}
