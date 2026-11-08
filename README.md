# Carrefour intelligent connecté — Maquette de simulation

**SAÉ 3.02 — Groupe « Python Mayo »**

| Étudiant | |
|---|---|
| Atakan Gocer | |
| Louise Halter-Tisler | |

Maquette PyQt6 + sockets (V2I) + MariaDB d'un carrefour capable
d'ouvrir un **couloir prioritaire** pour les véhicules d'urgence.

Le système est **réparti sur deux machines virtuelles Debian 13** : la
VM1 héberge le moteur de simulation et sa base, la VM2 la passerelle
réseau et la sienne (voir *Architecture répartie* plus bas).

---

## ▶ Démarrage rapide (5 minutes, sans VM)

Pour voir le projet fonctionner tout de suite, sur une seule machine.
Les trois rôles tournent en local et dialoguent par sockets, exactement
comme ils le feraient à travers le réseau.

**Prérequis : Python 3.11 ou plus récent** (`python3 --version`). Les
versions des dépendances sont figées, comme l'exige la consigne, et ne
s'installeront pas sur une version antérieure.

```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Puis lancez les trois rôles d'un coup :

- **Windows** : double-cliquez sur `LANCER_TOUT.bat`
- **Linux / macOS** : `./lancer_local.sh`

MariaDB n'est **pas nécessaire** pour cette démonstration : en son
absence la simulation tourne sans enregistrement et le signale au
démarrage.

> **Pour le déploiement réel sur les deux VM Debian**, qui est
> l'architecture du projet, suivez
> [deploiement/README.md](deploiement/README.md) — création des VM
> scriptée, puis provisionnement automatisé de chacune. Comptez 30 à
> 45 minutes.

---

## Le principe implémenté : la voie réservée aux secours

1. Un véhicule d'urgence émet une **alerte V2I** en approchant du carrefour.
2. Sa route devient une **voie réservée** : panneau *sens interdit — SAUF
   URGENCES* allumé à l'entrée de sa route **et** à l'entrée de sa voie de
   sortie. Aucun usager ordinaire (véhicule normal, autonome, cycliste) ne
   peut plus y entrer ; les véhicules d'urgence, eux, peuvent l'emprunter.
3. Les véhicules ordinaires déjà présents sur cette route sont **déviés** à
   gauche ou à droite : la route se vide devant l'ambulance.
4. **Préemption des feux** : seule la direction de l'ambulance a le vert.
   Le trafic d'en face est retenu (sinon les véhicules qui tournent à gauche
   devant l'ambulance lui céderaient le passage indéfiniment) et les feux
   piétons passent au rouge (les piétons déjà engagés terminent).
5. Plusieurs secours peuvent partager la voie : même itinéraire, ou même
   axe en sens opposé (voies parallèles, ils ne se croisent jamais).
6. Deux secours sur des **axes qui se croisent** : un seul couloir à la
   fois, le second s'arrête et passe dès la libération (premier arrivé,
   premier servi). Couloir limité à 30 s par sécurité.

### Résultat mesuré (15 situations de trafic identiques, avec / sans système)

| | Sans système | Avec voie réservée |
|---|---|---|
| Temps de traversée moyen de l'ambulance | 28,1 s | **12,3 s** |
| Temps passé à l'arrêt | ~13,7 s | **~0,7 s** |

**Gain : −56 % de temps de traversée.** Sécurité : 4 à 6 collisions
résiduelles pour 12 000 cycles de simulation.

## Alertes anticipées et niveaux de priorité

### Alerte anticipée

Le véhicule d'urgence n'apparaît plus « par surprise » : il envoie son
alerte V2I **12 s avant** d'arriver au carrefour (`DELAI_ALERTE`). Un
bandeau clignotant l'annonce à l'entrée de sa route, avec un compte à
rebours. La voie réservée s'ouvre dès l'alerte, ce qui laisse aux usagers
présents le temps de dégager.

La préemption renforcée (trafic d'en face retenu, piétons au rouge) ne
s'active que dans les **6 dernières secondes** de l'approche
(`PREEMPTION_AVANT_ARRIVEE`). Plus tôt, elle bloquerait piétons et trafic
inutilement longtemps ; plus tard, les véhicules qui tournent à gauche
devant l'ambulance n'auraient pas le temps de passer.

Résultats (20 situations de trafic identiques, voie réservée + serrage) :

| | Alerte au dernier moment | Alerte 12 s avant |
|---|---|---|
| Usagers encore devant l'ambulance à son arrivée | 3,5 | **0,3** |
| Temps de traversée moyen | 9,5 s | **7,3 s** |
| Temps passé à l'arrêt | 1,0 s | **0,1 s** |
| Pire cas | 15,0 s | **10,4 s** |

### Niveau de priorité

L'alerte transmet un niveau de priorité :

| Niveau | Signification |
|---|---|
| P1 | Urgence vitale (SMUR, pompiers sur feu ou secours à personne) |
| P2 | Urgence (ambulance, police en intervention) |
| P3 | Non urgente (transport sanitaire, retour de mission) |

Arbitrage entre deux urgences dont les trajectoires se croisent :

1. la plus prioritaire est servie en premier ; à priorité égale, celle qui
   arrive la première ;
2. si une urgence **plus prioritaire** alerte alors que le bénéficiaire du
   couloir est **encore en approche**, le couloir lui est réattribué ;
3. un bénéficiaire **déjà arrivé** au carrefour ne perd jamais son couloir
   (retirer la priorité à un véhicule en train de traverser serait dangereux) ;
4. les itinéraires compatibles (même itinéraire, ou même axe en sens
   opposé) partagent la voie réservée.

Dans l'interface, la priorité se choisit dans le menu « Priorité alerte »
avant de cliquer sur **+** à côté de « Urgences ». Le bouton **−** annule
d'abord une alerte dont le véhicule n'est pas encore arrivé. Le panneau V2I
liste les alertes en cours (priorité, itinéraire, compte à rebours, statut).

Sécurité : 3,3 collisions en moyenne sur 10 graines × 8 000 ticks (3,9
avant l'ajout des alertes) ; aucune collision dans les scénarios de
réattribution testés.

## Serrer à droite à l'approche d'un véhicule d'urgence

Comme dans la réalité, un usager qui a un véhicule d'urgence derrière lui
dans sa voie :

- **serre à droite** (décalage latéral progressif vers le bord de la voie) ;
- **ralentit fortement** et allume ses **feux de détresse** ;
- **ne s'engage pas dans le carrefour** devant l'ambulance ;
- ne se replace au centre de sa voie que lorsque l'ambulance l'a
  **nettement dépassé** (pas de rabattement sur son flanc).

L'ambulance, elle, se rapproche de la ligne médiane et **remonte la file**.
Elle n'engage le dépassement que si la voiture devant est suffisamment
rangée. Les cyclistes, déjà sur la bande cyclable, n'ont pas à se ranger.

Garde-fous : on ne se range pas sur un cycliste qui roule à sa hauteur, et
on ne reste pas rangé plus de 5 s si l'ambulance ne peut pas avancer (sinon
tout le monde s'attendrait mutuellement).

Mise en œuvre : chaque usager a une position **sur sa trajectoire** (suivi
de route, feux, lignes d'arrêt) et un **décalage latéral** dans sa voie. La
position réelle sur la chaussée combine les deux ; c'est elle qui sert à la
détection du véhicule de devant, aux collisions et à l'affichage.
Paramètres dans `config.py` (section *SERRER À DROITE*), désactivable avec
`SERRAGE_ACTIF = False`.

### Résultats (20 situations de trafic identiques)

| Configuration | Temps moyen de traversée | Temps à l'arrêt | Pire cas |
|---|---|---|---|
| Aucun système | 31,0 s | 16,0 s | 100 s (bloquée) |
| Serrage à droite seul | 14,3 s | 3,3 s | 32,3 s |
| Voie réservée seule | 11,8 s | 0,5 s | 15,4 s |
| **Voie réservée + serrage** | **9,6 s** | 1,0 s | 15,0 s |

Sécurité : 3,5 collisions en moyenne sans serrage, 3,9 avec (sur 10
graines × 8 000 ticks, écart dans le bruit statistique) ; 3 collisions liées
au serrage sur 80 000 ticks.

## Étude comparative des mécanismes

Lance `ETUDE_COMPARATIVE.bat` (ou `python utils/etude_comparative.py`) pour
mesurer le temps de traversée de l'ambulance sur 20 situations de trafic
identiques selon 5 configurations. Un CSV et un graphique PNG sont générés.

| Configuration | Temps moyen | Pire cas |
|---|---|---|
| 1. Aucun système | 31,8 s | 100 s (bloquée) |
| 2. Préemption des feux seule | 46,3 s | 100 s (contre-productif !) |
| 3. + Voie réservée et déviation | 12,0 s | 15,4 s |
| 4. + Serrage à droite | 9,4 s | 14,4 s |
| 5. + Alerte anticipée (12 s) | **7,5 s** | **10,4 s** |

**Résultat notable** : la préemption des feux seule (config 2) est
*pire* que sans système. Pourquoi ? Le feu vert retient le trafic de
l'axe perpendiculaire, mais ne vide pas la file déjà présente devant
l'ambulance sur SA voie. Elle se retrouve bloquée derrière des voitures
qui ont le vert mais ne peuvent pas avancer (carrefour lui-même bloqué).
C'est un résultat connu : la préemption des feux seule aggrave la
situation si la voie est déjà saturée. C'est précisément ce que la voie
réservée résout, en forçant le dégagement de cette file.

## Ajouter / supprimer des usagers (boutons + / −)

Le panneau « Usagers présents » propose, pour chaque type d'usager
(véhicule, autonome, urgence, cycliste, piéton), un bouton **+** et un
bouton **−**.

- **+** : l'usager apparaît sur une entrée libre choisie au hasard. Si
  toutes les entrées sont occupées (bouchon), la demande est mise en
  attente et l'usager entre dès qu'une place se libère. Les usagers
  ordinaires n'entrent jamais sur une voie réservée aux secours.
- **−** : annule d'abord un ajout encore en attente ; sinon retire
  l'usager de ce type arrivé le plus récemment, en évitant ceux qui sont
  au milieu du carrefour.

Fonctionnement réseau (communication bidirectionnelle, deux sauts) :

1. Le client envoie `{"type": "commande", "action": "ajouter"|"supprimer", "usager": ...}`
   sur le socket (écriture protégée par un verrou, aucun widget touché).
2. Sur la **VM2**, un thread de lecture par client dépose la commande
   dans une `queue.Queue`. La passerelle l'étiquette avec l'identifiant
   du client émetteur et la transmet à la VM1.
3. Sur la **VM1**, un thread de lecture dépose la commande dans sa
   propre file. La boucle de simulation la vide **entre deux ticks** :
   le moteur n'est jamais modifié par deux threads en même temps.
4. La VM1 répond `{"type": "info", "message": ..., "_client": id}`. La
   passerelle lit cet identifiant, retire le champ et renvoie la réponse
   **au seul client** qui avait émis la commande, qui l'affiche via un
   signal Qt.

L'étiquette `_client` est strictement interne à la liaison inter-VM :
elle ne quitte jamais la VM2 en direction des clients.

## Règles du Code de la route appliquées

| Règle | Où |
|---|---|
| Circulation à droite, voies entrante et sortante distinctes | `models/carrefour.py` |
| Distance de sécurité, freinage progressif | `simulation/moteur.py` (`_leader`) |
| Freinage plus fort que l'accélération | `models/usager.py` |
| Arrêt à la ligne d'arrêt au rouge ; orange franchi seulement si on ne peut plus s'arrêter | `_peut_franchir` |
| Phase de dégagement « tout rouge » entre deux axes | `models/feu_circulation.py` |
| Priorité au piéton engagé sur le passage (entrée **et** sortie) | `_pieton_engage_sur`, `_pieton_devant_en_sortie` |
| Refus de priorité en tourne-à-gauche (art. R415-5) | `_trafic_en_face` |
| Interdiction de bloquer le carrefour (dégagement) | `_peut_degager` |
| Bande cyclable séparée, piétons sur deux demi-passages | `config.DECALAGE_CYCLABLE`, `route_pieton` |

## Résultats mesurés (12 000 ticks, ~6,5 min de simulation)

- **5 collisions** (contre 2402 avant les corrections de priorité)
- 9 couloirs prioritaires ouverts, 29 déviations forcées
- Gain de temps des véhicules prioritaires : **~30 à 80 %** selon le trafic
- Trafic stable (pas d'emballement des files d'attente)

## Architecture répartie sur deux VM

Le projet ne tourne pas sur une seule machine : les **processus** et les
**bases de données** sont répartis sur deux VM Debian 13.

```
   VM1 « Simulation »  192.168.56.10      VM2 « Passerelle »  192.168.56.11
  ┌──────────────────────────────┐      ┌──────────────────────────────┐
  │  main_moteur.py              │      │  main_passerelle.py          │
  │   · moteur de simulation     │◄────►│   · relais vers les clients  │
  │   · règles du code de la route│ 5051 │   · routage des commandes    │
  │                              │      │                              │
  │  MariaDB carrefour_moteur_db │      │  MariaDB carrefour_stats_db  │
  │   · usager, evenement        │      │   · session_simulation       │
  └──────────────────────────────┘      └──────────────┬───────────────┘
                                                       │ 5050
                                  ┌────────────────────┴───────────────┐
                                  │  Clients (PC hôte ou 3e machine)   │
                                  │   · main_client.py   (PyQt6)       │
                                  │   · main_ambulance.py (boîtier V2I)│
                                  └────────────────────────────────────┘
```

**Pourquoi ce découpage ?**

1. **Séparation métier / réseau.** La VM1 ne fait que calculer la
   simulation ; la VM2 ne fait que du relais. Aucune VM ne concentre
   l'ensemble des processus.
2. **Le cœur métier n'est jamais exposé.** Les clients ne joignent que
   la VM2. Un client défaillant ou malveillant ne peut pas atteindre
   directement la machine qui fait tourner la simulation.
3. **Chaque base est colocalisée avec son principal producteur.** La
   VM1 écrit `usager` et `evenement` à chaque tick (jusqu'à plusieurs
   écritures par seconde) : les garder en local évite un aller-retour
   réseau systématique. La VM2 n'écrit `session_simulation` que deux
   fois par session, à l'ouverture et à la clôture — cette table suit
   donc le processus qui gère les sessions clients.
4. **Tolérance aux pannes.** Si la liaison inter-VM tombe, la VM2
   continue de servir ses clients et les prévient du mode dégradé ;
   elle se reconnecte seule dès que la VM1 revient.

La liaison VM1 ↔ VM2 réutilise le **même protocole JSON sur sockets
bruts** que les clients, conformément à la contrainte « coder la couche
transport/session soi-même ».

## Installation

### Récupérer le projet

```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### VM1 « Simulation » (Debian 13)

```bash
sudo apt install -y mariadb-server python3 python3-venv
sudo mariadb < database/schema_moteur.sql
sudo mariadb -e "CREATE USER IF NOT EXISTS 'carrefour_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';
                 GRANT ALL ON carrefour_moteur_db.* TO 'carrefour_user'@'localhost'; FLUSH PRIVILEGES;"

export CARREFOUR_DB_MOTEUR_PASSWORD="votre_mot_de_passe"
export CARREFOUR_MOTEUR_ECOUTE="0.0.0.0"

python3 serveur/main_moteur.py
```

### VM2 « Passerelle » (Debian 13)

```bash
sudo apt install -y mariadb-server python3 python3-venv
sudo mariadb < database/schema_passerelle.sql
sudo mariadb -e "CREATE USER IF NOT EXISTS 'carrefour_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';
                 GRANT ALL ON carrefour_stats_db.* TO 'carrefour_user'@'localhost'; FLUSH PRIVILEGES;"

export CARREFOUR_DB_PASSERELLE_PASSWORD="votre_mot_de_passe"
export CARREFOUR_MOTEUR_HOTE="192.168.56.10"    # IP host-only de la VM1
export CARREFOUR_SOCKET_ECOUTE="0.0.0.0"

python3 serveur/main_passerelle.py
```

### Poste client (interface PyQt6)

```bash
export CARREFOUR_SOCKET_SERVEUR_HOTE="192.168.56.11"   # IP de la VM2
python3 client/main_client.py
```

L'application ambulance, qui simule le boîtier embarqué, se lance de la
même façon et vise également la VM2 :

```bash
python3 ambulance/main_ambulance.py 192.168.56.11 5050 1 N   # alerte P1 depuis le nord
```

> **Vous voulez juste tester le projet ?** Le guide
> [deploiement/README.md](deploiement/README.md) donne deux chemins :
> tout sur un seul PC en 5 minutes, ou le déploiement complet sur deux
> VM Debian avec des scripts automatisés.

### Tout faire tourner sur un seul PC (démonstration rapide)

Sous Windows, `LANCER_TOUT.bat` ouvre les trois rôles dans trois
fenêtres (moteur, passerelle, client) en 127.0.0.1. Les bases ne sont
alors pas nécessaires : si MariaDB est absent, la simulation tourne
sans enregistrement et l'affiche au démarrage.

Pour les lancer séparément : `LANCER_MOTEUR.bat`, puis
`LANCER_PASSERELLE.bat`, puis `LANCER_CLIENT.bat`.

### Variables d'environnement disponibles

| Variable | Rôle | Défaut |
|---|---|---|
| `CARREFOUR_MOTEUR_ECOUTE` | interface d'écoute du moteur (VM1) | `0.0.0.0` |
| `CARREFOUR_MOTEUR_HOTE` | IP de la VM1, vue depuis la VM2 | `192.168.56.10` |
| `CARREFOUR_MOTEUR_PORT` | port de la liaison inter-VM | `5051` |
| `CARREFOUR_SOCKET_ECOUTE` | interface d'écoute de la passerelle (VM2) | `0.0.0.0` |
| `CARREFOUR_SOCKET_SERVEUR_HOTE` | IP de la VM2, vue depuis les clients | `192.168.56.11` |
| `CARREFOUR_SOCKET_PORT` | port des clients | `5050` |
| `CARREFOUR_DB_MOTEUR_*` | connexion à la base de la VM1 | voir `config.py` |
| `CARREFOUR_DB_PASSERELLE_*` | connexion à la base de la VM2 | voir `config.py` |
| `CARREFOUR_CLE_V2I` | clé HMAC partagée des alertes d'urgence | voir `reseau/securite.py` |

## Structure

```
config.py                     paramètres (géométrie, vitesses, densité, réseau, 2 bases)

── exécuté sur la VM1 « Simulation » ────────────────────────────────
serveur/main_moteur.py        point d'entrée VM1 : moteur + port interne
models/
  carrefour.py                géométrie, trajectoires avec virages, passages piétons
  usager.py                   classe mère : trajectoire, dynamique, cap
  usagers_concrets.py         Vehicule / Cycliste / Pieton
  feu_circulation.py          cycle des feux + phase de dégagement
simulation/
  centrale_v2i.py             alertes, couloir prioritaire, déviations, arbitrage
  generateur_trafic.py        création des usagers
  moteur.py                   règles de circulation, collisions, métriques
database/schema_moteur.sql    tables usager + evenement

── exécuté sur la VM2 « Passerelle » ────────────────────────────────
serveur/main_passerelle.py    point d'entrée VM2 : relais clients ↔ VM1
reseau/client_moteur.py       client TCP vers la VM1, avec reconnexion
database/schema_passerelle.sql
                              table session_simulation

── exécuté sur le poste client ──────────────────────────────────────
client/
  main_client.py              point d'entrée de l'interface
  fenetre_principale.py       IHM + tableau de bord (signaux/slots)
  scene_carrefour.py          rendu QGraphicsScene
  thread_reseau.py            QThread de réception
ambulance/main_ambulance.py   boîtier embarqué V2I (alerte signée HMAC)

── partagé par les trois rôles ──────────────────────────────────────
reseau/
  protocole.py                messages JSON délimités (protocole maison)
  serveur_socket.py           serveur TCP générique (VM1 et VM2)
  securite.py                 signature HMAC-SHA256 des alertes
database/
  connexion.py                ouverture de la base locale d'une VM
  dao.py                      DAOMoteur (VM1) et DAOPasserelle (VM2)
utils/
  metriques.py                statistiques
  etude_comparative.py        banc d'essai des 5 configurations
```

## Conformité à la stack imposée

- **PyQt6** uniquement (`QGraphicsScene`/`QGraphicsView`), pas de Pygame/Tkinter
- **Sockets bruts** (`socket` standard), protocole JSON maison, pas de MQTT —
  y compris pour la liaison interne entre les deux VM
- **QThread + pyqtSignal/pyqtSlot** : aucun widget touché depuis le thread réseau
- **`threading` + `queue`** côté serveurs (VM1 et VM2), sans interface graphique
- **MariaDB** via `mysql-connector-python`
- `requirements.txt` à la racine avec versions exactes

## Limites connues (à assumer devant le jury)

- Une seule voie par sens et par branche ; pas de voie de tourne-à-gauche dédiée
- Les véhicules prioritaires vont tout droit (cas d'usage de la démo)
- Les cyclistes suivent les mêmes trajectoires que les véhicules, décalés
  sur une bande ; pas de sas vélo
- Quelques collisions résiduelles (~5 pour 12 000 ticks) dans des
  configurations de croisement serrées
- Le couloir s'ouvre à l'alerte, soit un délai fixe de 12 s avant
  l'arrivée (`DELAI_ALERTE`), et non à une distance calibrée en mètres
- Pas de modélisation des pertes de paquets ni de la latence V2I ; la
  liaison inter-VM gère en revanche la coupure franche (reconnexion
  automatique et mode dégradé annoncé aux clients)
- Déviation du trafic vers une branche tirée au hasard, pas vers la
  branche la moins chargée
- Pas de tests unitaires automatisés
