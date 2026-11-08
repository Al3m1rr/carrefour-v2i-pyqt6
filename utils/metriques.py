"""Statistiques agrégées d'une session de simulation."""


class Metriques:
    """Statistiques de la simulation. Le chiffre clé du projet est le
    temps de parcours moyen des véhicules prioritaires, à comparer à
    celui des véhicules ordinaires."""

    def __init__(self):
        """Initialise des compteurs vides pour une nouvelle session."""
        self.temps_parcours = {}
        self.nb_passages = {}
        self.nb_collisions = 0
        self.nb_deviations = 0

    def enregistrer_passage(self, usager):
        """Comptabilise la traversée d'un usager qui vient de sortir.

        Les usagers retirés avant d'avoir terminé leur trajet sont
        ignorés : leur temps de parcours fausserait les moyennes.

        Args:
            usager (Usager): l'usager sorti du carrefour.
        """
        if usager.heure_entree is None or usager.heure_sortie is None:
            return
        duree = usager.heure_sortie - usager.heure_entree
        self.temps_parcours.setdefault(usager.type_usager, []).append(duree)
        self.nb_passages[usager.type_usager] = self.nb_passages.get(usager.type_usager, 0) + 1
        if getattr(usager, "devie", False):
            self.nb_deviations += 1

    def enregistrer_collision(self, a, b):
        """Incrémente le compteur de collisions pour le couple en cause."""
        self.nb_collisions += 1

    def temps_moyen(self, type_usager):
        """Retourne le temps de parcours moyen d'un type d'usager, ou None."""
        valeurs = self.temps_parcours.get(type_usager, [])
        return sum(valeurs) / len(valeurs) if valeurs else None

    def vers_dict(self):
        """Sérialise les statistiques pour l'envoi réseau et la base."""
        return {
            "nb_collisions": self.nb_collisions,
            "nb_deviations": self.nb_deviations,
            "passages": dict(self.nb_passages),
            "temps_moyen_urgence": self._arrondi(self.temps_moyen("vehicule_urgence")),
            "temps_moyen_normal": self._arrondi(self.temps_moyen("vehicule_normal")),
        }

    @staticmethod
    def _arrondi(valeur):
        """Arrondit à deux décimales en laissant None inchangé."""
        return round(valeur, 2) if valeur is not None else None

    def resume(self):
        """Construit le bilan lisible affiché à l'arrêt de la simulation.

        Returns:
            Une liste de lignes de texte, dont le gain de temps des
            véhicules prioritaires par rapport aux véhicules ordinaires.
        """
        lignes = [
            f"Collisions          : {self.nb_collisions}",
            f"Déviations forcées  : {self.nb_deviations}",
        ]
        for type_usager, nb in sorted(self.nb_passages.items()):
            moyenne = self.temps_moyen(type_usager)
            txt = f"{moyenne:.1f}s" if moyenne else "N/A"
            lignes.append(f"{type_usager:<20}: {nb} passages, temps moyen {txt}")

        t_urgence = self.temps_moyen("vehicule_urgence")
        t_normal = self.temps_moyen("vehicule_normal")
        if t_urgence and t_normal:
            gain = (1 - t_urgence / t_normal) * 100
            lignes.append(f"Gain de temps des prioritaires : {gain:.0f}% vs véhicule ordinaire")
        return lignes
