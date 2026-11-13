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
