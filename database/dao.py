"""Acces aux donnees (DAO), un objet par base et donc par VM.

Le projet repartit la persistance sur les deux machines :

- `DAOMoteur` tourne sur la VM1 et ecrit les donnees produites tick par
  tick par la simulation (entrees, sorties, evenements) ;
- `DAOPasserelle` tourne sur la VM2 et ecrit le bilan agrege d'une
  session de simulation, au moment ou cette session se termine.

Chaque methode verifie que la connexion existe avant d'ecrire : si la
base est absente, elle ne fait rien et la simulation continue.
"""

from datetime import datetime


class _DAOBase:
    """Partie commune aux deux DAO : execution protegee d'une requete."""

    def __init__(self, connexion):
        """Memorise la connexion MariaDB (ou None si base indisponible)."""
        self.connexion = connexion

    def _executer(self, requete, valeurs):
        """Execute une requete d'ecriture et valide la transaction.

        Toute erreur SQL est affichee mais jamais propagee : une base
        indisponible ne doit pas interrompre la simulation en cours.
        """
        if not self.connexion:
            return None
        try:
            curseur = self.connexion.cursor()
            curseur.execute(requete, valeurs)
            self.connexion.commit()
            identifiant = curseur.lastrowid
            curseur.close()
            return identifiant
        except Exception as e:
            print(f"[DB] Erreur lors de l'ecriture : {e}")
            return None


class DAOMoteur(_DAOBase):
    """Ecritures temps reel de la VM1 : tables `usager` et `evenement`."""

    def enregistrer_usager(self, usager):
        """Insere un usager au moment ou il entre dans le carrefour."""
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
        """Complete la ligne d'un usager qui vient de sortir du carrefour."""
        requete = "UPDATE usager SET heure_sortie = %s, temps_parcours = %s WHERE id = %s"
        duree = usager.heure_sortie - usager.heure_entree
        valeurs = (datetime.fromtimestamp(usager.heure_sortie), duree, usager.id)
        self._executer(requete, valeurs)

    def log_evenement(self, usager_id, type_evenement):
        """Journalise un evenement ('passage', 'accident', 'attente_feu')."""
        requete = "INSERT INTO evenement (usager_id, type_evenement) VALUES (%s, %s)"
        self._executer(requete, (usager_id, type_evenement))


class DAOPasserelle(_DAOBase):
    """Bilans de session de la VM2 : table `session_simulation`."""

    # Types d'usagers comptes comme des vehicules dans le bilan.
    TYPES_VEHICULES = ("vehicule_normal", "vehicule_autonome", "vehicule_urgence")

    def ouvrir_session(self):
        """Cree la ligne de session au demarrage de la passerelle.

        Returns:
            L'identifiant de la session creee, ou None si pas de base.
        """
        requete = "INSERT INTO session_simulation (date_debut) VALUES (%s)"
        return self._executer(requete, (datetime.now(),))

    def cloturer_session(self, session_id, stats):
        """Complete la ligne de session avec le bilan observe.

        Args:
            session_id: identifiant renvoye par ouvrir_session().
            stats (dict): bloc "stats" du dernier etat recu de la VM1
                (nb_collisions, passages par type, temps_moyen_urgence).
        """
        if session_id is None or not stats:
            return
        passages = stats.get("passages", {})
        nb_vehicules = sum(passages.get(t, 0) for t in self.TYPES_VEHICULES)
        requete = (
            "UPDATE session_simulation SET date_fin = %s, nb_vehicules = %s, "
            "nb_cyclistes = %s, nb_pietons = %s, nb_accidents = %s, "
            "temps_moyen_urgence = %s WHERE id = %s"
        )
        valeurs = (
            datetime.now(),
            nb_vehicules,
            passages.get("cycliste", 0),
            passages.get("pieton", 0),
            stats.get("nb_collisions", 0),
            stats.get("temps_moyen_urgence"),
            session_id,
        )
        self._executer(requete, valeurs)
