"""Fenêtre principale du client (VM Client).

Toute mise à jour de l'IHM passe par un slot connecté à un signal du
ThreadReseau : aucun widget n'est touché depuis le thread réseau."""

from PyQt6.QtWidgets import (
    QMainWindow, QGraphicsView, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QFormLayout, QPushButton, QGridLayout, QComboBox,
)
from PyQt6.QtGui import QPainter, QFont
from PyQt6.QtCore import Qt, pyqtSlot

import config
from client.scene_carrefour import SceneCarrefour
from client.thread_reseau import ThreadReseau

STYLE_FENETRE = """
QMainWindow, QWidget { background-color: #0F172A; color: #E2E8F0; }
QGroupBox {
    border: 1px solid #334155; border-radius: 6px;
    margin-top: 10px; padding: 8px; font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #94A3B8; }
QLabel { color: #E2E8F0; }
QPushButton {
    background-color: #1E293B; color: #E2E8F0; border: 1px solid #475569;
    border-radius: 4px; font-weight: bold; font-size: 14px;
    min-width: 28px; max-width: 28px; min-height: 24px;
}
QPushButton:hover { background-color: #334155; }
QPushButton:pressed { background-color: #475569; }
QPushButton#plus:hover { border-color: #4ADE80; color: #4ADE80; }
QPushButton#moins:hover { border-color: #F87171; color: #F87171; }
QPushButton:disabled { color: #475569; border-color: #334155; }
QComboBox {
    background-color: #1E293B; color: #E2E8F0; border: 1px solid #475569;
    border-radius: 4px; padding: 2px 6px;
}
QComboBox QAbstractItemView { background-color: #1E293B; color: #E2E8F0; }
"""

COULEURS_PRIORITE = {1: "#EF4444", 2: "#F59E0B", 3: "#60A5FA"}

TYPES_USAGERS = ("vehicule_normal", "vehicule_autonome", "vehicule_urgence",
                 "cycliste", "pieton")


class FenetrePrincipale(QMainWindow):
    """Poste de supervision du carrefour : vue graphique et tableau de bord.

    Toutes les données affichées arrivent du thread réseau par signaux
    Qt : aucun widget n'est touché depuis ce thread, conformément à la
    règle de thread-safety imposée par le projet.
    """

    def __init__(self):
        """Construit l'interface puis démarre le thread réseau."""
        super().__init__()
        self.setWindowTitle("Carrefour intelligent connecté — Poste de supervision")
        self.setStyleSheet(STYLE_FENETRE)

        self.scene = SceneCarrefour()
        self.vue = QGraphicsView(self.scene)
        self.vue.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.vue.setFixedSize(config.LARGEUR_SCENE + 4, config.HAUTEUR_SCENE + 4)
        self.vue.setStyleSheet("border: 1px solid #334155;")

        panneau = self._construire_panneau_lateral()

        corps = QHBoxLayout()
        corps.addWidget(self.vue)
        corps.addWidget(panneau)

        conteneur = QWidget()
        conteneur.setLayout(corps)
        self.setCentralWidget(conteneur)

        self.thread_reseau = ThreadReseau(config.SOCKET_SERVEUR_HOTE, config.SOCKET_PORT)
        self.thread_reseau.etat_recu.connect(self._sur_etat_recu)
        self.thread_reseau.statut_connexion.connect(self._sur_statut_connexion)
        self.thread_reseau.info_recue.connect(self._sur_info_recue)
        self.thread_reseau.start()

    # ------------------------------------------------------------

    def _construire_panneau_lateral(self):
        """Assemble le panneau de droite : statut, V2I, compteurs et boutons.

        Returns:
            Le widget prêt à être inséré dans la fenêtre.
        """
        panneau = QWidget()
        panneau.setFixedWidth(360)
        layout = QVBoxLayout(panneau)

        self.label_statut = QLabel("Connexion au serveur…")
        self.label_statut.setWordWrap(True)
        layout.addWidget(self.label_statut)

        # --- Priorité V2I ---
        groupe_v2i = QGroupBox("Priorité V2I")
        form_v2i = QFormLayout(groupe_v2i)
        self.label_couloir = QLabel("Aucun couloir actif")
        self.label_couloir.setWordWrap(True)
        police = QFont()
        police.setPointSize(9)
        police.setBold(True)
        self.label_couloir.setFont(police)
        self.label_attente = QLabel("0")
        self.label_alertes = QLabel("Aucune alerte")
        self.label_alertes.setWordWrap(True)
        self.label_alertes.setTextFormat(Qt.TextFormat.RichText)
        form_v2i.addRow("État :", self.label_couloir)
        form_v2i.addRow("Urgences en attente :", self.label_attente)
        form_v2i.addRow("Alertes :", self.label_alertes)
        layout.addWidget(groupe_v2i)

        # --- Trafic : compteurs + boutons d'ajout / suppression ---
        groupe_trafic = QGroupBox("Usagers présents")
        grille = QGridLayout(groupe_trafic)
        grille.setColumnStretch(0, 1)
        self.labels_trafic = {}
        self.boutons_usagers = []
        for ligne, type_usager in enumerate(TYPES_USAGERS):
            pastille = QLabel("●")
            pastille.setStyleSheet(f"color: {config.COULEURS_USAGER[type_usager]}; font-size: 14px;")
            nom = QLabel(self._joli_nom(type_usager))
            compteur = QLabel("0")
            compteur.setAlignment(Qt.AlignmentFlag.AlignCenter)
            compteur.setMinimumWidth(28)

            moins = QPushButton("−")
            moins.setObjectName("moins")
            moins.setToolTip(f"Supprimer un(e) {self._joli_nom(type_usager).lower()}")
            moins.clicked.connect(lambda _, t=type_usager: self._envoyer("supprimer", t))
            plus = QPushButton("+")
            plus.setObjectName("plus")
            plus.setToolTip(f"Ajouter un(e) {self._joli_nom(type_usager).lower()}")
            plus.clicked.connect(lambda _, t=type_usager: self._envoyer("ajouter", t))

            ligne_nom = QHBoxLayout()
            ligne_nom.addWidget(pastille)
            ligne_nom.addWidget(nom)
            ligne_nom.addStretch()
            grille.addLayout(ligne_nom, ligne, 0)
            grille.addWidget(moins, ligne, 1)
            grille.addWidget(compteur, ligne, 2)
            grille.addWidget(plus, ligne, 3)

            self.labels_trafic[type_usager] = compteur
            self.boutons_usagers += [moins, plus]

        ligne_prio = QHBoxLayout()
        ligne_prio.addWidget(QLabel("Priorité alerte :"))
        self.choix_priorite = QComboBox()
        for niveau, libelle in sorted(config.NIVEAUX_PRIORITE.items()):
            self.choix_priorite.addItem(f"P{niveau} · {libelle}", niveau)
        self.choix_priorite.setCurrentIndex(0)
        ligne_prio.addWidget(self.choix_priorite)
        grille.addLayout(ligne_prio, len(TYPES_USAGERS), 0, 1, 4)

        self.label_info = QLabel("Utilisez + / − pour ajouter ou retirer des usagers.")
        self.label_info.setWordWrap(True)
        self.label_info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        grille.addWidget(self.label_info, len(TYPES_USAGERS) + 1, 0, 1, 4)
        self._activer_boutons(False)
        layout.addWidget(groupe_trafic)

        # --- Statistiques ---
        groupe_stats = QGroupBox("Statistiques")
        form_stats = QFormLayout(groupe_stats)
        self.label_collisions = QLabel("0")
        self.label_deviations = QLabel("0")
        self.label_temps_urgence = QLabel("—")
        self.label_temps_normal = QLabel("—")
        form_stats.addRow("Collisions :", self.label_collisions)
        form_stats.addRow("Déviations forcées :", self.label_deviations)
        form_stats.addRow("Temps moyen urgence :", self.label_temps_urgence)
        form_stats.addRow("Temps moyen ordinaire :", self.label_temps_normal)
        layout.addWidget(groupe_stats)

        layout.addStretch()
        return panneau

    @staticmethod
    def _joli_nom(type_usager):
        """Retourne le libellé affichable d'un type d'usager."""
        return {
            "vehicule_normal": "Véhicules",
            "vehicule_autonome": "Autonomes",
            "vehicule_urgence": "Urgences",
            "cycliste": "Cyclistes",
            "pieton": "Piétons",
        }.get(type_usager, type_usager)

    # ------------------------------------------------------------
    #  Slots (exécutés dans le thread principal)
    # ------------------------------------------------------------

    @pyqtSlot(dict)
    def _sur_etat_recu(self, etat):
        """Slot Qt : rafraîchit la scène et le tableau de bord.

        Args:
            etat (dict): snapshot complet reçu de la passerelle.
        """
        self.scene.maj_etat(etat)

        compteurs = {}
        for u in etat.get("usagers", []):
            compteurs[u["type"]] = compteurs.get(u["type"], 0) + 1
        for type_usager, label in self.labels_trafic.items():
            label.setText(str(compteurs.get(type_usager, 0)))

        v2i = etat.get("v2i", {})
        couloir = v2i.get("couloir")
        if couloir:
            retenue = v2i.get("branche_retenue")
            phase = ("Préemption : en face retenu, piétons au rouge"
                     if retenue else "Approche : voie en cours de dégagement")
            self.label_couloir.setText(
                f"🚨 P{couloir['priorite']} · voie réservée {couloir['entree']} → {couloir['sortie']}\n{phase}"
            )
            self.label_couloir.setStyleSheet("color: #F87171;")
        else:
            self.label_couloir.setText("Trafic normal")
            self.label_couloir.setStyleSheet("color: #4ADE80;")
        self.label_attente.setText(str(v2i.get("urgences_en_attente", 0)))
        self.label_alertes.setText(self._format_alertes(v2i.get("alertes", [])))

        stats = etat.get("stats", {})
        self.label_collisions.setText(str(stats.get("nb_collisions", 0)))
        self.label_deviations.setText(str(stats.get("nb_deviations", 0)))
        self.label_temps_urgence.setText(self._format_temps(stats.get("temps_moyen_urgence")))
        self.label_temps_normal.setText(self._format_temps(stats.get("temps_moyen_normal")))

    @staticmethod
    def _format_alertes(alertes):
        """Met en forme en HTML la liste des alertes V2I en cours."""
        if not alertes:
            return "<span style='color:#64748B'>Aucune alerte</span>"
        lignes = []
        for a in alertes[:5]:
            couleur = COULEURS_PRIORITE.get(a["priorite"], "#E2E8F0")
            if a["en_approche"]:
                quand = f"arrive dans {a['arrivee_dans']:.0f} s"
            else:
                quand = "au carrefour"
            etat = "✅ voie réservée" if a["statut"] == "voie réservée" else "⏳ en attente"
            lignes.append(f"<span style='color:{couleur}'><b>P{a['priorite']}</b></span> "
                          f"{a['entree']}→{a['sortie']} · {quand} · {etat}")
        return "<br>".join(lignes)

    @staticmethod
    def _format_temps(valeur):
        """Affiche une durée en secondes, ou un tiret si elle est inconnue."""
        return f"{valeur:.1f} s" if valeur else "—"

    # ------------------------------------------------------------
    #  Commandes opérateur
    # ------------------------------------------------------------

    def _envoyer(self, action, type_usager):
        """Envoie une commande + / − au serveur via le thread réseau.

        Args:
            action (str): "ajouter" ou "supprimer".
            type_usager (str): type d'usager concerné. Pour une urgence
                ajoutée, le niveau de priorité choisi dans le menu est
                joint à la commande.
        """
        parametres = {}
        if type_usager == "vehicule_urgence" and action == "ajouter":
            parametres["priorite"] = self.choix_priorite.currentData()
        if not self.thread_reseau.envoyer_commande(action, type_usager, **parametres):
            self.label_info.setText("Non connecté au serveur : commande non envoyée.")
            self.label_info.setStyleSheet("color: #F87171; font-size: 11px;")

    def _activer_boutons(self, actif):
        """Active ou grise les boutons selon l'état de la connexion."""
        for bouton in self.boutons_usagers:
            bouton.setEnabled(actif)

    @pyqtSlot(str)
    def _sur_info_recue(self, message):
        """Retour du serveur après un clic sur + ou −."""
        echec = message.startswith(("Impossible", "Aucun", "Type", "Action", "Entrées occupées"))
        self.label_info.setText(message)
        self.label_info.setStyleSheet(
            f"color: {'#FBBF24' if echec else '#4ADE80'}; font-size: 11px;"
        )

    @pyqtSlot(bool, str)
    def _sur_statut_connexion(self, connecte, message):
        """Slot Qt : reflète l'état de la connexion (voyant et boutons).

        Args:
            connecte (bool): True si la liaison est établie.
            message (str): texte explicatif à afficher.
        """
        self._activer_boutons(connecte)
        self.label_statut.setText(("🟢 " if connecte else "🔴 ") + message)
        self.label_statut.setStyleSheet(
            "color: #4ADE80;" if connecte else "color: #F87171;"
        )
        # Mode dégradé : bordure rouge sur la scène pour signaler la perte
        self.vue.setStyleSheet(
            "border: 1px solid #334155;" if connecte
            else "border: 2px solid #EF4444;"
        )

    def closeEvent(self, event):
        """Arrête proprement le thread réseau à la fermeture de la fenêtre."""
        self.thread_reseau.arreter()
        super().closeEvent(event)
