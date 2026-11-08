import os

# ============================================================
#  GEOMETRIE DE LA SCENE
# ============================================================
LARGEUR_SCENE = 960
HAUTEUR_SCENE = 720

CENTRE_X = LARGEUR_SCENE // 2
CENTRE_Y = HAUTEUR_SCENE // 2

DEMI_CHAUSSEE = 60          # demi-largeur de la route (2 voies de 60 px)
OFFSET_VOIE = 30            # distance entre l'axe de la route et le centre d'une voie
DEMI_ZONE_CONFLIT = 60      # demi-côté du carré central où les trajectoires se croisent

PASSAGE_DEBUT = DEMI_ZONE_CONFLIT + 10   # début de la bande du passage piéton
PASSAGE_FIN = DEMI_ZONE_CONFLIT + 32     # fin de la bande
LIGNE_ARRET = DEMI_ZONE_CONFLIT + 40     # les véhicules s'arrêtent AVANT le passage piéton

DECALAGE_CYCLABLE = 20      # décalage des cyclistes vers le bord droit de leur voie

BRANCHES = ("N", "S", "E", "W")

# ============================================================
#  VITESSES ET DYNAMIQUE (px / tick)
# ============================================================
VITESSE_VEHICULE = 2.6
VITESSE_VEHICULE_URGENCE = 3.6
VITESSE_CYCLISTE = 1.5
VITESSE_PIETON = 0.9

ACCELERATION = 0.12         # accélération max par tick
DECELERATION = 0.45         # freinage max par tick : un véhicule freine bien
                            # plus vite qu'il n'accélère (sinon la distance
                            # de freinage dépasse la distance de détection)

# ============================================================
#  SECURITE (Code de la route)
# ============================================================
DISTANCE_ARRET = 40         # distance centre-à-centre en dessous de laquelle on s'arrête
DISTANCE_RALENTI = 78       # distance en dessous de laquelle on ralentit
TOLERANCE_LATERALE = 17     # largeur de la "voie" pour détecter un véhicule devant soi
PORTEE_DETECTION = 160      # au-delà, on ignore le véhicule de devant
PORTEE_CONFLIT = 115        # anticipation d'un croisement dans l'intersection

# ============================================================
#  ALERTES V2I : ANTICIPATION ET PRIORITÉ
# ============================================================
# L'ambulance envoie son alerte AVANT d'arriver au carrefour : la voie
# réservée s'ouvre pendant son approche et se vide avant son arrivée.
DELAI_ALERTE = 360          # ticks entre l'alerte et l'arrivée (12 s à 30 ticks/s)
PREEMPTION_AVANT_ARRIVEE = 180   # trafic d'en face retenu et piétons au rouge
                                 # dans les 6 dernières secondes de l'approche

# Niveau de priorité transmis dans l'alerte (1 = le plus prioritaire)
NIVEAUX_PRIORITE = {
    1: "Urgence vitale",        # SMUR, pompiers sur feu / secours à personne
    2: "Urgence",               # ambulance, police en intervention
    3: "Non urgente",           # transport sanitaire, retour de mission
}
REPARTITION_PRIORITES = {1: 0.3, 2: 0.5, 3: 0.2}   # pour les urgences générées au hasard

# ============================================================
#  SERRER À DROITE À L'APPROCHE D'UN VÉHICULE D'URGENCE
# ============================================================
SERRAGE_ACTIF = True
DETECTION_URGENCE = 220     # distance à laquelle on entend / détecte la sirène derrière soi
DECALAGE_SERRAGE = 16       # décalage vers le bord droit de la voie
DECALAGE_URGENCE = -9       # l'ambulance se rapproche de l'axe pour dépasser
VITESSE_DECALAGE = 0.9      # vitesse du déplacement latéral (px / tick)
VITESSE_EN_CEDANT = 0.2     # fraction de la vitesse max en serrant à droite
DUREE_MAX_CEDE = 150        # garde-fou : on ne reste pas rangé indéfiniment
TOLERANCE_DEPASSEMENT_URGENCE = 23  # écart latéral minimal pour que l'ambulance double

# ============================================================
#  TRAFIC
# ============================================================
# Débits calibrés pour rester sous la capacité réelle d'un carrefour à
# feux (~1800 véh/h tous sens confondus). Au-delà, la file remonte à
# l'infini et la simulation ne représente plus rien d'exploitable.
DENSITE_VEHICULES = 0.006
DENSITE_CYCLISTES = 0.0022
DENSITE_PIETONS = 0.0030
PROBABILITE_URGENCE = 0.03   # 3 % des véhicules : une intervention toutes les ~40 s
PROPORTION_AUTONOMES = 0.35

# Répartition des destinations pour un véhicule ordinaire
PROBA_TOUT_DROIT = 0.55
PROBA_GAUCHE = 0.20
# le reste : à droite

# ============================================================
#  FEUX
# ============================================================
DUREE_VERT = 260
DUREE_ORANGE = 55
DUREE_TOUT_ROUGE = 40       # phase de dégagement entre deux axes

# ============================================================
#  SIMULATION
# ============================================================
TICKS_PAR_SECONDE = 30

# ============================================================
#  COULEURS (hexa, utilisées côté client PyQt6)
# ============================================================
COULEURS_USAGER = {
    "vehicule_normal": "#3B82F6",
    "vehicule_autonome": "#F59E0B",
    "vehicule_urgence": "#EF4444",
    "cycliste": "#22C55E",
    "pieton": "#FDE68A",
}

COULEUR_HERBE = "#1F2937"
COULEUR_TROTTOIR = "#9CA3AF"
COULEUR_ASPHALTE = "#374151"
COULEUR_MARQUAGE = "#E5E7EB"
COULEUR_COULOIR = "#EF4444"

# ============================================================
#  BASES DE DONNEES (une par VM, chacune locale a son processus)
# ============================================================
# VM1 "Simulation" : tables `usager` et `evenement`, ecrites en temps reel
# par le moteur. Colocaliser la base avec son producteur evite un
# aller-retour reseau a chaque entree / sortie d'usager.
DB_MOTEUR_CONFIG = {
    "host": os.environ.get("CARREFOUR_DB_MOTEUR_HOST", "127.0.0.1"),
    "user": os.environ.get("CARREFOUR_DB_MOTEUR_USER", "carrefour_user"),
    "password": os.environ.get("CARREFOUR_DB_MOTEUR_PASSWORD", "changeme"),
    "database": os.environ.get("CARREFOUR_DB_MOTEUR_NAME", "carrefour_moteur_db"),
}

# VM2 "Passerelle" : table `session_simulation`, ecrite en fin de session
# par le processus qui pilote les connexions clients.
DB_PASSERELLE_CONFIG = {
    "host": os.environ.get("CARREFOUR_DB_PASSERELLE_HOST", "127.0.0.1"),
    "user": os.environ.get("CARREFOUR_DB_PASSERELLE_USER", "carrefour_user"),
    "password": os.environ.get("CARREFOUR_DB_PASSERELLE_PASSWORD", "changeme"),
    "database": os.environ.get("CARREFOUR_DB_PASSERELLE_NAME", "carrefour_stats_db"),
}

# ============================================================
#  RESEAU (V2I par sockets TCP)
# ============================================================
# Facade client : la passerelle (VM2) ecoute ici, les clients PyQt6 et
# l'application ambulance s'y connectent.
SOCKET_ECOUTE_HOTE = os.environ.get("CARREFOUR_SOCKET_ECOUTE", "0.0.0.0")
SOCKET_PORT = int(os.environ.get("CARREFOUR_SOCKET_PORT", "5050"))
SOCKET_SERVEUR_HOTE = os.environ.get("CARREFOUR_SOCKET_SERVEUR_HOTE", "192.168.56.11")

# Liaison interne entre les deux VM : le moteur (VM1) ecoute, la
# passerelle (VM2) s'y connecte en tant que client.
MOTEUR_ECOUTE_HOTE = os.environ.get("CARREFOUR_MOTEUR_ECOUTE", "0.0.0.0")
MOTEUR_PORT = int(os.environ.get("CARREFOUR_MOTEUR_PORT", "5051"))
MOTEUR_HOTE = os.environ.get("CARREFOUR_MOTEUR_HOTE", "192.168.56.10")
