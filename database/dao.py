"""Fonctions d'accès aux données (DAO). Chaque fonction vérifie que la
connexion existe avant d'écrire -- si elle est absente, elle ne fait
rien et la simulation continue normalement."""

from datetime import datetime


class DAO:
    def __init__(self, connexion):
        self.connexion = connexion

    def _executer(self, requete, valeurs):
        if not self.connexion:
            return
        try:
            curseur = self.connexion.cursor()
            curseur.execute(requete, valeurs)
            self.connexion.commit()
            curseur.close()
        except Exception as e:
            print(f"[DB] Erreur lors de l'écriture : {e}")

    def enregistrer_usager(self, usager):
        requete = (
            "INSERT INTO usager (id, type_usager, direction_origine, heure_entree) "
            "VALUES (%s, %s, %s, %s)"
        )
        valeurs = (
            usager.id,
            usager.type_usager,
            usager.direction,
            datetime.fromtimestamp(usager.heure_entree),
        )
        self._executer(requete, valeurs)

    def finaliser_usager(self, usager):
        requete = "UPDATE usager SET heure_sortie = %s, temps_parcours = %s WHERE id = %s"
        duree = usager.heure_sortie - usager.heure_entree
        valeurs = (datetime.fromtimestamp(usager.heure_sortie), duree, usager.id)
        self._executer(requete, valeurs)

    def log_evenement(self, usager_id, type_evenement):
        requete = "INSERT INTO evenement (usager_id, type_evenement) VALUES (%s, %s)"
        self._executer(requete, (usager_id, type_evenement))
