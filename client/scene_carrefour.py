"""Rendu graphique du carrefour (QGraphicsScene).

Le décor est dessiné une seule fois ; seuls les usagers, les feux, les
panneaux et le couloir prioritaire sont mis à jour à chaque état reçu.
Toutes les mises à jour se font depuis le thread principal."""

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsPolygonItem, QGraphicsSimpleTextItem,
)
from PyQt6.QtGui import QBrush, QColor, QPen, QPolygonF, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF

import config

COULEURS_FEU = {"vert": "#22C55E", "orange": "#F59E0B", "rouge": "#EF4444"}
COULEURS_PRIORITE = {1: "#EF4444", 2: "#F59E0B", 3: "#60A5FA"}
SANS_STYLO = QPen(Qt.PenStyle.NoPen)


class SceneCarrefour(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, config.LARGEUR_SCENE, config.HAUTEUR_SCENE)
        self.setBackgroundBrush(QBrush(QColor(config.COULEUR_HERBE)))

        self._items_usagers = {}
        self._lampes = {}
        self._panneaux = {}
        self._surlignage_couloir = []
        self._bandeaux_alertes = []

        self._dessiner_decor()
        self._creer_feux()
        self._creer_panneaux_sens_interdit()

    # ============================================================
    #  Décor statique
    # ============================================================

    def _dessiner_decor(self):
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        demi = config.DEMI_CHAUSSEE
        L, H = config.LARGEUR_SCENE, config.HAUTEUR_SCENE

        # --- Trottoirs (bandes plus larges sous la chaussée) ---
        trottoir = QBrush(QColor(config.COULEUR_TROTTOIR))
        marge = 12
        self.addRect(cx - demi - marge, 0, (demi + marge) * 2, H, SANS_STYLO, trottoir)
        self.addRect(0, cy - demi - marge, L, (demi + marge) * 2, SANS_STYLO, trottoir)

        # --- Chaussée ---
        asphalte = QBrush(QColor(config.COULEUR_ASPHALTE))
        self.addRect(cx - demi, 0, demi * 2, H, SANS_STYLO, asphalte)
        self.addRect(0, cy - demi, L, demi * 2, SANS_STYLO, asphalte)

        self._dessiner_axes_centraux()
        self._dessiner_bandes_cyclables()
        self._dessiner_passages_pietons()
        self._dessiner_lignes_arret()

    def _dessiner_axes_centraux(self):
        """Ligne axiale discontinue séparant les deux sens."""
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        dz = config.DEMI_ZONE_CONFLIT
        stylo = QPen(QColor(config.COULEUR_MARQUAGE), 3)
        stylo.setDashPattern([8, 10])

        self.addLine(cx, 0, cx, cy - dz, stylo)
        self.addLine(cx, cy + dz, cx, config.HAUTEUR_SCENE, stylo)
        self.addLine(0, cy, cx - dz, cy, stylo)
        self.addLine(cx + dz, cy, config.LARGEUR_SCENE, cy, stylo)

    def _dessiner_bandes_cyclables(self):
        """Marquage de la bande cyclable au bord droit de chaque voie entrante."""
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        dz = config.DEMI_ZONE_CONFLIT
        d = config.DECALAGE_CYCLABLE
        o = config.OFFSET_VOIE
        stylo = QPen(QColor("#4ADE80"), 2, Qt.PenStyle.DotLine)

        self.addLine(cx - o - d - 8, 0, cx - o - d - 8, cy - dz, stylo)
        self.addLine(cx + o + d + 8, cy + dz, cx + o + d + 8, config.HAUTEUR_SCENE, stylo)
        self.addLine(0, cy + o + d + 8, cx - dz, cy + o + d + 8, stylo)
        self.addLine(cx + dz, cy - o - d - 8, config.LARGEUR_SCENE, cy - o - d - 8, stylo)

    def _dessiner_passages_pietons(self):
        """Zébras : bandes blanches perpendiculaires à la circulation."""
        blanc = QBrush(QColor("#F3F4F6"))
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        debut, fin = config.PASSAGE_DEBUT, config.PASSAGE_FIN
        large = config.DEMI_CHAUSSEE
        epaisseur = fin - debut
        pas = 14
        largeur_bande = 8

        for branche in config.BRANCHES:
            if branche == "N":
                y = cy - fin
                for x in range(int(cx - large), int(cx + large), pas):
                    self.addRect(x, y, largeur_bande, epaisseur, SANS_STYLO, blanc)
            elif branche == "S":
                y = cy + debut
                for x in range(int(cx - large), int(cx + large), pas):
                    self.addRect(x, y, largeur_bande, epaisseur, SANS_STYLO, blanc)
            elif branche == "W":
                x = cx - fin
                for y in range(int(cy - large), int(cy + large), pas):
                    self.addRect(x, y, epaisseur, largeur_bande, SANS_STYLO, blanc)
            else:
                x = cx + debut
                for y in range(int(cy - large), int(cy + large), pas):
                    self.addRect(x, y, epaisseur, largeur_bande, SANS_STYLO, blanc)

    def _dessiner_lignes_arret(self):
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        la = config.LIGNE_ARRET
        o = config.OFFSET_VOIE
        demi_voie = config.DEMI_CHAUSSEE / 2
        stylo = QPen(QColor("#F9FAFB"), 4)

        self.addLine(cx - o - demi_voie, cy - la, cx - o + demi_voie, cy - la, stylo)
        self.addLine(cx + o - demi_voie, cy + la, cx + o + demi_voie, cy + la, stylo)
        self.addLine(cx - la, cy + o - demi_voie, cx - la, cy + o + demi_voie, stylo)
        self.addLine(cx + la, cy - o - demi_voie, cx + la, cy - o + demi_voie, stylo)

    # ============================================================
    #  Feux tricolores
    # ============================================================

    def _creer_feux(self):
        """4 feux tricolores, un par branche entrante, placés juste avant
        la ligne d'arrêt, face aux conducteurs qui arrivent.

        Chaque boîtier contient :
        - 3 lampes (rouge / orange / vert)
        - une étiquette de direction (N, S, E, W)
        - un mât vertical (ligne noire sous le boîtier)

        L'état de chaque feu dépend de l'axe de sa branche :
        branches N et S → état NS / branches E et W → état EO."""
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        la = config.LIGNE_ARRET
        o = config.OFFSET_VOIE
        L, H = config.LARGEUR_SCENE, config.HAUTEUR_SCENE

        # Largeur / hauteur du boîtier
        BW, BH = 24, 66

        # Chaque feu est posé à droite de la voie entrante, contre la
        # ligne d'arrêt, face au conducteur (sens de circulation à droite).
        # On reste dans les limites de la scène pour N et E qui sont près
        # du bord en plaçant le boîtier à l'intérieur de la route.
        positions = {
            # Branche N : voitures cap sud sur la voie ouest
            # Feu posé à droite de la voie, côté axe central, juste avant la ligne
            "N": (cx - o + 4,         cy - la - BH - 6,   "NS", "N ↓"),
            # Branche S : voitures cap nord sur la voie est
            "S": (cx + o - BW - 4,    cy + la + 6,         "NS", "S ↑"),
            # Branche W : voitures cap est sur la voie sud
            "W": (cx - la - BW - 6,   cy + o - BH - 4,    "EO", "W →"),
            # Branche E : voitures cap ouest sur la voie nord
            "E": (cx + la + 6,        cy - o + 4,          "EO", "E ←"),
        }

        police_label = QFont("Arial", 8)
        police_label.setBold(True)

        for branche, (bx, by, axe, label) in positions.items():
            # Mât
            mat_x = bx + BW // 2
            mat_bas = by + BH
            mat_haut = mat_bas + 22
            self.addLine(mat_x, mat_bas, mat_x, mat_haut,
                         QPen(QColor("#111827"), 3))

            # Boîtier
            self.addRect(bx, by, BW, BH,
                         QPen(QColor("#111827"), 2),
                         QBrush(QColor("#1F2937")))

            # Étiquette direction (en blanc sous le boîtier)
            txt = QGraphicsSimpleTextItem(label)
            txt.setFont(police_label)
            txt.setBrush(QBrush(QColor("#E5E7EB")))
            r = txt.boundingRect()
            txt.setPos(bx + BW / 2 - r.width() / 2, mat_haut + 2)
            txt.setZValue(6)
            self.addItem(txt)

            # 3 lampes (rouge en haut, orange au milieu, vert en bas)
            lampes = {}
            for i, couleur in enumerate(("rouge", "orange", "vert")):
                lampe = QGraphicsEllipseItem(bx + 4, by + 5 + i * 19, 16, 16)
                lampe.setPen(SANS_STYLO)
                lampe.setBrush(QBrush(QColor("#374151")))
                lampe.setZValue(5)
                self.addItem(lampe)
                lampes[couleur] = lampe

            self._lampes[branche] = (lampes, axe)

    def _maj_feux(self, etats):
        """Met à jour les 4 feux selon l'état NS / EO reçu du serveur."""
        for branche, (lampes, axe) in self._lampes.items():
            actif = etats.get(axe)
            for couleur, lampe in lampes.items():
                lampe.setBrush(QBrush(QColor(
                    COULEURS_FEU[couleur] if couleur == actif else "#374151"
                )))

    # ============================================================
    #  Panneaux "sens interdit" (couloir prioritaire)
    # ============================================================

    def _creer_panneaux_sens_interdit(self):
        """Panneaux 'sens interdit' + panonceau 'SAUF URGENCES'.

        Deux jeux de panneaux par branche :
        - 'entree' : posé au début de la route, sur la voie entrante.
          Allumé quand cette route est réservée à l'ambulance.
        - 'sortie' : posé en face, à l'entrée de la voie sortante.
          Allumé quand cette voie de sortie est réservée."""
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        dz = config.DEMI_ZONE_CONFLIT
        o = config.OFFSET_VOIE
        L, H = config.LARGEUR_SCENE, config.HAUTEUR_SCENE

        positions = {
            "entree": {
                "N": (cx - o, 70), "S": (cx + o, H - 70),
                "E": (L - 70, cy - o), "W": (70, cy + o),
            },
            "sortie": {
                "N": (cx + o, cy - dz - 26), "S": (cx - o, cy + dz + 26),
                "E": (cx + dz + 26, cy + o), "W": (cx - dz - 26, cy - o),
            },
        }
        police = QFont("Arial", 7)
        police.setBold(True)

        self._panneaux = {"entree": {}, "sortie": {}}
        for role, par_branche in positions.items():
            for branche, (px, py) in par_branche.items():
                disque = QGraphicsEllipseItem(px - 14, py - 14, 28, 28)
                disque.setBrush(QBrush(QColor("#DC2626")))
                disque.setPen(QPen(QColor("#FFFFFF"), 2))
                barre = QGraphicsRectItem(px - 10, py - 3, 20, 6)
                barre.setBrush(QBrush(QColor("#FFFFFF")))
                barre.setPen(SANS_STYLO)

                cartouche = QGraphicsRectItem(px - 30, py + 16, 60, 13)
                cartouche.setBrush(QBrush(QColor("#FFFFFF")))
                cartouche.setPen(QPen(QColor("#111827"), 1))
                texte = QGraphicsSimpleTextItem("SAUF URGENCES")
                texte.setFont(police)
                texte.setBrush(QBrush(QColor("#111827")))
                largeur_texte = texte.boundingRect().width()
                texte.setPos(px - largeur_texte / 2, py + 17)

                items = (disque, barre, cartouche, texte)
                for item in items:
                    item.setZValue(7)
                    item.setVisible(False)
                    self.addItem(item)
                self._panneaux[role][branche] = items

    def _maj_panneaux(self, sens_interdit):
        if isinstance(sens_interdit, list):   # compatibilité ancien format
            sens_interdit = {"entree": [], "sortie": sens_interdit}
        for role, par_branche in self._panneaux.items():
            allumees = sens_interdit.get(role, [])
            for branche, items in par_branche.items():
                for item in items:
                    item.setVisible(branche in allumees)

    # ============================================================
    #  Surlignage du couloir prioritaire
    # ============================================================

    def _maj_couloir(self, v2i):
        for item in self._surlignage_couloir:
            self.removeItem(item)
        self._surlignage_couloir = []

        couloir = v2i.get("couloir")
        if not couloir:
            return

        couleur = QColor(config.COULEUR_COULOIR)
        couleur.setAlpha(55)
        brosse = QBrush(couleur)

        for branche, entrante in ((couloir["entree"], True), (couloir["sortie"], False)):
            rect = self._rect_voie(branche, entrante)
            item = self.addRect(rect, SANS_STYLO, brosse)
            item.setZValue(1)
            self._surlignage_couloir.append(item)

        # Préemption : barre rouge sur la ligne d'arrêt du trafic retenu
        retenue = v2i.get("branche_retenue")
        if retenue:
            cx, cy = config.CENTRE_X, config.CENTRE_Y
            la, o = config.LIGNE_ARRET, config.OFFSET_VOIE
            dv = config.DEMI_CHAUSSEE / 2
            segments = {
                "N": (cx - o - dv, cy - la, cx - o + dv, cy - la),
                "S": (cx + o - dv, cy + la, cx + o + dv, cy + la),
                "W": (cx - la, cy + o - dv, cx - la, cy + o + dv),
                "E": (cx + la, cy - o - dv, cx + la, cy - o + dv),
            }
            barre = self.addLine(*segments[retenue], QPen(QColor("#EF4444"), 7))
            barre.setZValue(3)
            self._surlignage_couloir.append(barre)

    def _rect_voie(self, branche, entrante):
        """Rectangle couvrant la voie (entrante ou sortante) d'une branche."""
        cx, cy = config.CENTRE_X, config.CENTRE_Y
        o = config.OFFSET_VOIE
        demi_voie = config.DEMI_CHAUSSEE / 2
        L, H = config.LARGEUR_SCENE, config.HAUTEUR_SCENE

        if entrante:
            axe = {"N": cx - o, "S": cx + o, "E": cy - o, "W": cy + o}[branche]
        else:
            axe = {"N": cx + o, "S": cx - o, "E": cy + o, "W": cy - o}[branche]

        if branche == "N":
            return QRectF(axe - demi_voie, 0, demi_voie * 2, cy)
        if branche == "S":
            return QRectF(axe - demi_voie, cy, demi_voie * 2, H - cy)
        if branche == "W":
            return QRectF(0, axe - demi_voie, cx, demi_voie * 2)
        return QRectF(cx, axe - demi_voie, L - cx, demi_voie * 2)

    # ============================================================
    #  Usagers
    # ============================================================

    def maj_etat(self, etat):
        self._maj_feux(etat.get("feu", {}))
        v2i = etat.get("v2i", {})
        self._maj_panneaux(v2i.get("sens_interdit", {}))
        self._maj_couloir(v2i)
        self._maj_bandeaux_alertes(v2i.get("alertes", []), etat.get("tick", 0))
        self._maj_usagers(etat.get("usagers", []), etat.get("tick", 0))

    # ============================================================
    #  Bandeaux d'annonce des urgences en approche
    # ============================================================

    def _maj_bandeaux_alertes(self, alertes, tick):
        """Un bandeau clignotant à l'entrée de la route par laquelle un
        véhicule d'urgence annoncé va arriver : priorité + compte à rebours."""
        for item in self._bandeaux_alertes:
            self.removeItem(item)
        self._bandeaux_alertes = []

        cx, cy = config.CENTRE_X, config.CENTRE_Y
        o = config.OFFSET_VOIE
        L, H = config.LARGEUR_SCENE, config.HAUTEUR_SCENE
        ancrages = {"N": (cx - o, 24), "S": (cx + o, H - 24),
                    "W": (52, cy + o), "E": (L - 52, cy - o)}
        empilement = {"N": 26, "S": -26, "W": 26, "E": -26}
        compte = {}
        visible = (tick // 10) % 2 == 0
        police = QFont("Arial", 9)
        police.setBold(True)

        for a in alertes:
            if not a.get("en_approche"):
                continue
            branche = a["entree"]
            n = compte.get(branche, 0)
            compte[branche] = n + 1
            ax, ay = ancrages[branche]
            ay += empilement[branche] * n

            fond = QColor(COULEURS_PRIORITE.get(a["priorite"], "#EF4444"))
            fond.setAlpha(235 if visible else 120)
            cadre = self.addRect(QRectF(ax - 44, ay - 11, 88, 22),
                                 QPen(QColor("#FFFFFF"), 1.5), QBrush(fond))
            cadre.setZValue(8)
            texte = QGraphicsSimpleTextItem(f"P{a['priorite']} · {a['arrivee_dans']:.0f} s")
            texte.setFont(police)
            texte.setBrush(QBrush(QColor("#FFFFFF")))
            r = texte.boundingRect()
            texte.setPos(ax - r.width() / 2, ay - r.height() / 2)
            texte.setZValue(9)
            self.addItem(texte)
            self._bandeaux_alertes += [cadre, texte]

    def _maj_usagers(self, usagers, tick):
        vus = set()
        for u in usagers:
            vus.add(u["id"])
            item = self._items_usagers.get(u["id"])
            if item is None:
                item = self._creer_item(u)
                self._items_usagers[u["id"]] = item
                self.addItem(item)
            item.setPos(u["x"], u["y"])
            item.setRotation(u.get("angle", 0.0))
            if u["type"] == "vehicule_urgence":
                self._faire_clignoter(item, tick)
            warnings = item.data(1)
            if warnings:
                allume = u.get("cede", False) and (tick // 8) % 2 == 0
                for feu in warnings:
                    feu.setVisible(allume)

        for id_disparu in set(self._items_usagers) - vus:
            self.removeItem(self._items_usagers.pop(id_disparu))

    def _creer_item(self, u):
        type_usager = u["type"]
        couleur = QColor(config.COULEURS_USAGER.get(type_usager, "#FFFFFF"))

        if type_usager == "pieton":
            item = QGraphicsEllipseItem(-5, -5, 10, 10)
            item.setBrush(QBrush(couleur))
            item.setPen(QPen(QColor("#111827"), 1))
            item.setZValue(5)
            return item

        if type_usager == "cycliste":
            item = QGraphicsPolygonItem(QPolygonF([
                QPointF(9, 0), QPointF(-7, 5), QPointF(-7, -5),
            ]))
            item.setBrush(QBrush(couleur))
            item.setPen(QPen(QColor("#065F46"), 1))
            item.setZValue(4)
            return item

        # Véhicules : carrosserie orientée + pare-brise
        largeur, hauteur = 28.0, 15.0
        item = QGraphicsRectItem(-largeur / 2, -hauteur / 2, largeur, hauteur)
        item.setBrush(QBrush(couleur))
        item.setPen(QPen(QColor("#111827"), 1))
        item.setZValue(4)

        pare_brise = QGraphicsRectItem(largeur / 2 - 9, -hauteur / 2 + 2, 6, hauteur - 4, item)
        pare_brise.setBrush(QBrush(QColor("#E5E7EB")))
        pare_brise.setPen(SANS_STYLO)

        # Feux de détresse (allumés quand le véhicule se range pour une urgence)
        warnings = []
        for fx, fy in ((largeur / 2 - 3, -hauteur / 2), (largeur / 2 - 3, hauteur / 2 - 3),
                       (-largeur / 2, -hauteur / 2), (-largeur / 2, hauteur / 2 - 3)):
            feu = QGraphicsRectItem(fx, fy, 3, 3, item)
            feu.setBrush(QBrush(QColor("#FB923C")))
            feu.setPen(SANS_STYLO)
            feu.setVisible(False)
            warnings.append(feu)
        item.setData(1, warnings)

        if u["type"] == "vehicule_urgence":
            priorite = u.get("priorite") or 2
            item.setPen(QPen(QColor(COULEURS_PRIORITE.get(priorite, "#111827")), 2))
            etiquette = QGraphicsSimpleTextItem(str(priorite), item)
            police = QFont("Arial", 7)
            police.setBold(True)
            etiquette.setFont(police)
            etiquette.setBrush(QBrush(QColor("#FFFFFF")))
            etiquette.setPos(-largeur / 2 + 2, -hauteur / 2 + 1)
            gyrophare = QGraphicsEllipseItem(-4, -4, 8, 8, item)
            gyrophare.setPen(SANS_STYLO)
            gyrophare.setBrush(QBrush(QColor("#3B82F6")))
            item.setData(0, gyrophare)

        return item

    def _faire_clignoter(self, item, tick):
        gyrophare = item.data(0)
        if gyrophare is None:
            return
        bleu = (tick // 6) % 2 == 0
        gyrophare.setBrush(QBrush(QColor("#3B82F6" if bleu else "#FDE047")))
