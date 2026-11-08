# Carrefour intelligent connecté — Maquette de simulation

Maquette PyQt6 + sockets (V2I) + MariaDB d'un carrefour capable
d'ouvrir un **couloir prioritaire** pour les véhicules d'urgence.

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

Fonctionnement réseau (communication bidirectionnelle) :

1. Le client envoie `{"type": "commande", "action": "ajouter"|"supprimer", "usager": ...}`
   sur le socket (écriture protégée par un verrou, aucun widget touché).
2. Côté serveur, un thread de lecture par client dépose la commande dans
   une `queue.Queue`.
3. La boucle de simulation vide cette file **entre deux ticks** : le
   moteur n'est jamais modifié par deux threads en même temps.
4. Le serveur répond `{"type": "info", "message": ...}` au client, qui
   l'affiche via un signal Qt.

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

## Installation

### VM Serveur (moteur + base + socket)

```bash
sudo apt install mariadb-server python3 python3-venv -y
mysql -u root -p < database/schema.sql
python3 -m venv venv && source venv/bin/activate
pip install mysql-connector-python

export CARREFOUR_DB_HOST="127.0.0.1"
export CARREFOUR_DB_USER="carrefour_user"
export CARREFOUR_DB_PASSWORD="ton_mot_de_passe"
export CARREFOUR_SOCKET_ECOUTE="0.0.0.0"
export CARREFOUR_SOCKET_PORT="5050"

python3 serveur/main_serveur.py
```

### VM Client (interface PyQt6)

```bash
sudo apt install python3 python3-venv -y
python3 -m venv venv && source venv/bin/activate
pip install PyQt6

export CARREFOUR_SOCKET_SERVEUR_HOTE="192.168.56.10"   # IP de la VM Serveur
export CARREFOUR_SOCKET_PORT="5050"

python3 client/main_client.py
```

### Test sur un seul PC (sans VM)

Deux terminaux, avec `CARREFOUR_SOCKET_ECOUTE=127.0.0.1` d'un côté et
`CARREFOUR_SOCKET_SERVEUR_HOTE=127.0.0.1` de l'autre.

## Structure

```
config.py                    paramètres (géométrie, vitesses, densité, réseau, DB)
models/
  carrefour.py                géométrie, trajectoires avec virages, passages piétons
  usager.py                   classe mère : trajectoire, dynamique, cap
  usagers_concrets.py         Vehicule / Cycliste / Pieton
  feu_circulation.py          cycle des feux + phase de dégagement
simulation/
  centrale_v2i.py             alertes, couloir prioritaire, déviations, arbitrage
  generateur_trafic.py        création des usagers
  moteur.py                   règles de circulation, collisions, métriques
reseau/
  protocole.py                messages JSON délimités (protocole maison)
  serveur_socket.py           serveur TCP, diffusion aux clients
serveur/main_serveur.py      point d'entrée VM Serveur
client/
  main_client.py              point d'entrée VM Client
  fenetre_principale.py       IHM + tableau de bord (signaux/slots)
  scene_carrefour.py          rendu QGraphicsScene
  thread_reseau.py            QThread de réception
database/                    connexion, DAO, schema.sql
utils/metriques.py           statistiques
```

## Conformité à la stack imposée

- **PyQt6** uniquement (`QGraphicsScene`/`QGraphicsView`), pas de Pygame/Tkinter
- **Sockets bruts** (`socket` standard), protocole JSON maison, pas de MQTT
- **QThread + pyqtSignal/pyqtSlot** : aucun widget touché depuis le thread réseau
- **MariaDB** via `mysql-connector-python`
- `requirements.txt` à la racine avec versions exactes

## Limites connues (à assumer devant le jury)

- Une seule voie par sens et par branche ; pas de voie de tourne-à-gauche dédiée
- Les véhicules prioritaires vont tout droit (cas d'usage de la démo)
- Les cyclistes suivent les mêmes trajectoires que les véhicules, décalés
  sur une bande ; pas de sas vélo
- Quelques collisions résiduelles (~5 pour 12 000 ticks) dans des
  configurations de croisement serrées
- Le couloir est ouvert dès l'apparition du véhicule d'urgence, pas à une
  distance calibrée du carrefour
- Pas de modélisation des pertes réseau ni de la latence V2I
