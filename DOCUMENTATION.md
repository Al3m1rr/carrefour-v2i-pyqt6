# Documentation technique

**SAÉ 3.02 — Groupe « Python Mayo »**
Atakan Gocer · Louise Halter-Tisler

Ce document explique **comment le projet est construit** et **pourquoi**
il l'est ainsi. Il complète le [README](README.md), qui décrit ce que le
projet fait, et le [guide de déploiement](deploiement/GUIDE_DEPLOIEMENT.md),
qui explique comment l'installer.

---

## 1. Vue d'ensemble

Le projet simule un carrefour où des véhicules d'urgence doivent
traverser le plus vite possible, sans que les autres usagers cessent de
respecter le code de la route.

Il est réparti sur **trois rôles**, exécutés par trois processus
distincts qui communiquent par sockets TCP.

```
   ┌────────────────────────┐       ┌────────────────────────┐
   │  VM1 — le moteur       │       │  VM2 — la passerelle   │
   │                        │ 5051  │                        │
   │  calcule la simulation │◄─────►│  relaie, ne calcule    │
   │  30 fois par seconde   │       │  rien                  │
   │                        │       │                        │
   │  base : usagers et     │       │  base : bilans de      │
   │  événements            │       │  session               │
   └────────────────────────┘       └───────────┬────────────┘
                                                │ 5050
                                    ┌───────────┴────────────┐
                                    │  Le client PyQt6       │
                                    │  affiche, ne calcule   │
                                    │  rien non plus         │
                                    └────────────────────────┘
```

**Le principe directeur : un seul endroit décide.** Le moteur est le
seul à connaître l'état réel du carrefour et le seul à le modifier. La
passerelle et le client ne font que transmettre et afficher. Cela évite
toute divergence entre ce qui est calculé et ce qui est montré.

### Pourquoi trois rôles et non deux

Le sujet impose de répartir les processus sur deux VM. Nous avons séparé
**le métier du réseau** plutôt que, par exemple, le calcul de
l'affichage :

- la VM1 ne fait que calculer : elle ignore tout des clients connectés ;
- la VM2 ne fait que relayer : elle ignore tout des règles de priorité ;
- le cœur métier n'est jamais exposé — un client ne joint jamais la VM1.

Chaque base est placée **auprès du processus qui écrit dedans** : le
moteur enregistre chaque usager à chaque tick, la passerelle n'écrit
qu'au début et à la fin d'une session.

---

## 2. Le parcours d'une donnée

Deux trajets suffisent à comprendre tout le système.

### 2.1 Descendant : du calcul à l'écran, 30 fois par seconde

```
moteur.tick()                      la simulation avance d'un pas
   │
   ▼
moteur.etat_reseau()               l'état devient un dictionnaire Python
   │                               (positions, feux, alertes, stats)
   ▼
protocole.encoder_message()        le dictionnaire devient du JSON + "\n"
   │
   ▼  socket TCP, port 5051
passerelle : ClientMoteur          reçoit et transmet sans rien changer
   │
   ▼  socket TCP, port 5050
client : ThreadReseau              reçoit dans un thread séparé
   │
   ▼  pyqtSignal etat_recu
FenetrePrincipale                  met à jour l'affichage
```

**Le point à retenir** : la frontière entre le thread réseau et
l'interface est franchie par un **signal Qt**, jamais par un appel
direct. C'est la règle de thread-safety imposée par le sujet, et elle
est respectée en un seul endroit : `client/thread_reseau.py`.

### 2.2 Montant : du clic à la simulation

```
l'opérateur clique sur « + Urgences »
   │
   ▼
ThreadReseau.envoyer_commande()    {"type": "commande", ...} en JSON
   │
   ▼  socket TCP, port 5050
passerelle : ServeurSocket         dépose dans une file thread-safe
   │                               et étiquette l'émetteur
   ▼  socket TCP, port 5051
moteur : ServeurSocket             dépose dans sa propre file
   │
   ▼
main_moteur, entre deux ticks      applique la commande
   │
   ▼
réponse "info" → passerelle → le client qui avait demandé
```

**Le point à retenir** : une commande n'est jamais appliquée au moment
où elle arrive. Elle attend dans une `queue.Queue` et le moteur la
traite **entre deux ticks**. Le moteur n'est donc jamais modifié par
deux threads en même temps, sans avoir besoin du moindre verrou dans la
logique métier.

---

## 3. Les fichiers, couche par couche

### Le moteur — ce qui calcule

| Fichier | Rôle |
|---|---|
| `simulation/moteur.py` | Chef d'orchestre. Un `tick()` fait avancer tout le monde d'un pas |
| `simulation/centrale_v2i.py` | Reçoit les alertes, ouvre les couloirs prioritaires, arbitre les conflits |
| `simulation/generateur_trafic.py` | Fait apparaître les usagers selon une densité paramétrable |
| `models/usager.py` | Classe mère : position sur une trajectoire, vitesse, cap |
| `models/usagers_concrets.py` | `Vehicule`, `Cycliste`, `Pieton` — ce qui les distingue |
| `models/carrefour.py` | La géométrie : voies, trajectoires, passages piétons |
| `models/feu_circulation.py` | Le cycle des feux et sa phase de dégagement |
| `utils/metriques.py` | Les statistiques affichées et enregistrées |

### Le réseau — ce qui transporte

| Fichier | Rôle |
|---|---|
| `reseau/protocole.py` | Encode et découpe les messages JSON. 48 lignes, tout le protocole |
| `reseau/serveur_socket.py` | Serveur TCP générique, utilisé par la VM1 **et** la VM2 |
| `reseau/client_moteur.py` | Côté passerelle : client vers le moteur, avec reconnexion |
| `reseau/securite.py` | Signature HMAC des alertes du boîtier ambulance |

### Le client — ce qui affiche

| Fichier | Rôle |
|---|---|
| `client/main_client.py` | Point d'entrée, crée l'application Qt |
| `client/thread_reseau.py` | `QThread` de réception, émet des signaux |
| `client/fenetre_principale.py` | La fenêtre, les boutons, le tableau de bord |
| `client/scene_carrefour.py` | Le dessin : routes, usagers, feux, panneaux |

### Les points d'entrée

| Fichier | Lancé sur |
|---|---|
| `serveur/main_moteur.py` | la VM1 |
| `serveur/main_passerelle.py` | la VM2 |
| `client/main_client.py` | le poste qui affiche |
| `ambulance/main_ambulance.py` | n'importe où : simule le boîtier embarqué |
| `utils/etude_comparative.py` | hors simulation : compare cinq configurations |

### Le partagé

`config.py` rassemble **tous** les paramètres : géométrie, vitesses,
densités, délais, adresses réseau, bases de données. Aucune valeur
numérique n'est codée en dur ailleurs dans le projet — c'est ce qui
permet à l'étude comparative de désactiver un mécanisme sans toucher au
code.

`database/` contient la connexion, les DAO et les deux schémas SQL.

---

## 4. Les quatre mécanismes à savoir expliquer

Ce sont eux qui font l'intérêt du projet, et ce sont eux qu'on vous
demandera de justifier.

### 4.1 La voie réservée — `centrale_v2i.py`

**Le problème.** Forcer le feu au vert pour l'ambulance ne suffit pas :
si une file est déjà arrêtée devant elle, elle reste coincée derrière
des voitures qui ont le vert mais nulle part où aller.

**La solution, en trois gestes simultanés** quand une alerte arrive :

1. **Forcer les feux** sur l'axe de l'ambulance (`feu.forcer`).
2. **Interdire l'entrée** de sa route aux autres usagers — c'est le
   panneau *sens interdit, sauf urgences* affiché à l'écran.
3. **Dévier ceux qui sont déjà là** vers une autre sortie, pour que la
   voie se vide devant elle (`_devier_vehicules_genants`).

**Le détail qui compte** : on ne dévie **jamais** un véhicule déjà
engagé dans l'intersection. Changer sa trajectoire en plein carrefour
provoquerait exactement la collision qu'on cherche à éviter.

### 4.2 L'alerte anticipée — 12 secondes avant

L'ambulance n'apparaît pas par surprise : elle **s'annonce** par une
alerte V2I, et n'arrive que `DELAI_ALERTE` ticks plus tard, soit 12
secondes. La voie se vide donc **pendant** son approche, au lieu de la
faire freiner à son arrivée.

La **préemption renforcée** — retenir le trafic d'en face et passer les
piétons au rouge — ne s'active qu'aux 6 dernières secondes
(`PREEMPTION_AVANT_ARRIVEE`). C'est un compromis :

- plus tôt, on bloquerait piétons et trafic inutilement longtemps ;
- plus tard, les véhicules qui tournent à gauche n'auraient pas le
  temps de dégager.

**Pourquoi retenir le trafic d'en face ?** Sans cela, un véhicule qui
tourne à gauche devant l'ambulance doit lui céder le passage ; il reste
donc immobile au milieu du carrefour et la bloque. C'est contre-intuitif
mais c'est en bloquant *plus* de monde qu'on fait passer l'ambulance
plus vite.

### 4.3 L'arbitrage entre deux urgences — `traiter_alertes`

Appelé à chaque tick, il enchaîne **quatre décisions dans cet ordre** :

| Étape | Règle |
|---|---|
| **Fermer** | Le bénéficiaire est passé, a disparu, ou dépasse les 30 s de sécurité |
| **Réattribuer** | Une urgence **plus prioritaire** s'annonce, et le bénéficiaire actuel **n'est pas encore arrivé** |
| **Ouvrir** | Le couloir est libre : on élit `min(priorité, tick d'arrivée, id)` |
| **Autoriser** | On recalcule qui a le droit d'emprunter la voie |

Deux subtilités à savoir défendre :

- **Un bénéficiaire déjà arrivé ne perd jamais son couloir**, même face
  à une urgence plus prioritaire. Retirer la priorité à un véhicule en
  train de traverser serait dangereux.
- **Les itinéraires compatibles partagent la voie** (`_compatible`) :
  même itinéraire, ou même axe en sens opposé. Deux ambulances qui ne
  se croisent jamais n'ont pas à attendre l'une l'autre.

Le tri `min(u.priorite, u.tick_arrivee, u.id)` donne un **ordre total
strict** : priorité d'abord, puis ordre d'arrivée, puis identifiant.
Le dernier critère n'arrive jamais en pratique, mais il garantit un
résultat déterministe — sans lui, deux urgences parfaitement à égalité
pourraient se voler le couloir à chaque tick.

### 4.4 Le serrage à droite — `_gerer_serrage_a_droite`

Reproduit le réflexe réel : un usager qui entend une sirène derrière lui
se range, ralentit et ne s'engage pas dans le carrefour. L'ambulance,
elle, se rapproche de la ligne médiane et remonte la file.

Techniquement, chaque usager a **deux positions** : son avancement sur
sa trajectoire, et un **décalage latéral** dans sa voie. La position
réelle combine les deux (`pos_effective`), et c'est elle qui sert à
l'affichage comme aux collisions.

Trois garde-fous, tous nés de bugs observés :

- **Les cyclistes ne se rangent pas** : ils sont déjà sur la bande
  cyclable, au bord.
- **On ne se range pas sur un cycliste** qui roule à notre hauteur.
- **On ne reste pas rangé plus de 5 secondes** si l'ambulance
  *derrière* nous ne progresse pas — sinon tout le monde s'attendrait
  mutuellement. Ce garde-fou ne s'applique pas si l'ambulance est à
  notre hauteur ou devant : elle ne nous attend pas, il n'y a donc
  aucun risque d'interblocage.

### 4.5 Le résultat contre-intuitif à mettre en avant

L'étude comparative mesure cinq configurations sur des situations de
trafic identiques :

| Configuration | Temps moyen | Pire cas |
|---|---|---|
| Aucun système | 31,8 s | 100 s (bloquée) |
| **Préemption des feux seule** | **46,3 s** | 100 s |
| + Voie réservée et déviation | 12,0 s | 15,4 s |
| + Serrage à droite | 9,4 s | 14,4 s |
| + Alerte anticipée | **7,5 s** | 10,4 s |

**La préemption seule est pire que ne rien faire.** C'est le résultat le
plus intéressant du projet : le feu vert retient le trafic
perpendiculaire mais ne vide pas la file déjà présente devant
l'ambulance. Elle se retrouve derrière des véhicules qui ont le vert et
ne peuvent pas avancer. C'est exactement ce que la voie réservée
corrige.

---

## 5. Où se voit le respect de la stack imposée

Le sujet impose des technologies précises. Voici, pour chacune, le
fichier à ouvrir si on vous demande de le prouver.

| Contrainte | Où elle est satisfaite |
|---|---|
| **PyQt6 obligatoire**, Pygame interdit | `client/` entier. `requirements.txt` ne contient que PyQt6 |
| `QGraphicsScene` / `QGraphicsView` recommandés | `client/scene_carrefour.py` |
| **Sockets bas niveau**, MQTT interdit | `reseau/serveur_socket.py` et `reseau/client_moteur.py` : uniquement le module `socket` standard |
| Sérialisation en `json` | `reseau/protocole.py`, 48 lignes |
| **QThread + pyqtSignal** | `client/thread_reseau.py` |
| `threading` côté serveurs | `reseau/serveur_socket.py` : un thread de lecture par client |
| **Règle d'or thread-safety** | Aucun widget n'est touché hors du thread principal : voir plus bas |
| MariaDB | `database/connexion.py`, deux bases distinctes |
| Versions exactes | `requirements.txt` et `requirements-serveur.txt` |

### La couche transport, codée à la main

Le sujet interdit les protocoles clé en main et demande de coder
soi-même la couche transport. C'est l'objet de `protocole.py`, et le
problème qu'il résout mérite d'être expliqué.

Un socket TCP transporte un **flux d'octets**, pas des messages. Rien ne
garantit qu'un `recv()` corresponde à un `sendall()` : deux messages
peuvent arriver collés, ou un seul arriver en deux morceaux.

Notre solution est le **délimiteur** : chaque message est un objet JSON
sur **une seule ligne**, terminé par `\n`.

```python
def extraire_messages(buffer):
    morceaux = buffer.split(SEPARATEUR)
    reste = morceaux.pop()        # dernier morceau = message incomplet
    messages = [decoder_message(m) for m in morceaux if m]
    return messages, reste
```

Le receveur accumule les octets, découpe sur `\n`, traite les messages
complets et **conserve le reste** pour la prochaine réception. C'est ce
`reste` qui fait tout : sans lui, un message coupé en deux serait perdu.

### Comment la règle de thread-safety est tenue

C'est la question la plus probable sur la partie réseau du client.

```
ThreadReseau (thread secondaire)        FenetrePrincipale (thread principal)
        │                                            │
   recv() sur le socket                              │
        │                                            │
   etat_recu.emit(message)  ─── signal Qt ──►  @pyqtSlot maj_affichage()
                                                     │
                                            seul lui touche aux widgets
```

Le thread réseau ne fait **que** recevoir et émettre des signaux. Qt se
charge de basculer vers le thread principal, où les slots s'exécutent.
Dans l'autre sens, `envoyer_commande()` écrit sur le socket sous un
verrou, et ne touche à aucun widget.

Le fichier `client/thread_reseau.py` fait 118 lignes : c'est le seul
endroit du projet où les deux threads se rencontrent.

---

## 6. Les deux bases de données

| | VM1 — `carrefour_moteur_db` | VM2 — `carrefour_stats_db` |
|---|---|---|
| Tables | `usager`, `evenement` | `session_simulation` |
| Écrite par | le moteur, à chaque tick | la passerelle, 2 fois par session |
| Contenu | qui est entré, par où, combien de temps | le bilan agrégé d'une session |

**Pourquoi ce découpage ?** Chaque base est placée auprès du processus
qui écrit dedans. Le moteur enregistre chaque entrée et chaque sortie,
soit potentiellement des dizaines d'écritures par seconde : les faire
voyager sur le réseau à chaque fois n'aurait aucun sens. La passerelle
n'écrit qu'à l'ouverture et à la clôture d'une session.

**La preuve de la répartition**, en une commande sur chaque VM :

```bash
sudo mariadb -e "SHOW DATABASES;"
```

La VM1 a `carrefour_moteur_db` mais pas `carrefour_stats_db`, et
l'inverse sur la VM2. Les données ne sont pas centralisées.

**Deux détails défendables** :

- `enregistrer_usager` utilise `ON DUPLICATE KEY UPDATE`. Les
  identifiants d'usagers repartent de 1 à chaque démarrage du moteur :
  sans cela, une seconde exécution échouerait en doublon sur chaque
  insertion.
- Si MariaDB est injoignable, le DAO vaut `None` et la simulation
  continue **sans enregistrer**, en le signalant au démarrage. Une base
  absente ne doit pas empêcher une démonstration.
