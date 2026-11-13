# Fiche de soutenance

**SAÉ 3.02 — Groupe « Python Mayo »**
Atakan Gocer · Louise Halter-Tisler

Document interne de préparation : plan de présentation, démonstration,
chiffres à citer et réponses aux questions probables.

---

## 1. Le projet en une phrase

> Une maquette de carrefour connecté qui fait passer les véhicules
> d'urgence **sept fois plus vite** que le trafic ordinaire, sans qu'un
> seul usager cesse de respecter le code de la route — le tout réparti
> sur deux machines qui dialoguent par sockets.

---

## 2. Plan de présentation — 10 minutes

| Temps | Contenu | À montrer |
|---|---|---|
| 0–1 min | **Le problème.** Une ambulance perd du temps au carrefour. Objectif : réduire ce temps sans créer d'accidents | — |
| 1–2 min | **La fausse bonne idée.** Forcer le feu au vert ne suffit pas, et c'est même pire | Le tableau de l'étude comparative |
| 2–4 min | **Notre solution.** Voie réservée + déviation + alerte 12 s avant | La simulation, une urgence déclenchée en direct |
| 4–6 min | **L'architecture.** Deux VM, trois rôles, sockets bruts | Le schéma du README |
| 6–7 min | **Les données.** Deux bases réparties, et la preuve | `SHOW DATABASES` sur chaque VM |
| 7–9 min | **Les résultats.** Les chiffres mesurés, et ce qu'ils coûtent | La requête SQL sur `usager` |
| 9–10 min | **Les limites.** Assumées, pas cachées | — |

**Le fil conducteur** : partir d'une fausse bonne idée, montrer qu'elle
échoue avec des mesures, puis expliquer ce qui marche. C'est plus
convaincant que de présenter la solution d'emblée.

---

## 3. La démonstration

Préparez les deux VM **avant** de commencer : moteur lancé sur la VM1,
passerelle sur la VM2, interface ouverte. Vérifiez que le bandeau
affiche bien `Connecté au serveur`.

**L'enchaînement à montrer :**

1. **Le trafic normal.** Les feux alternent, les véhicules s'arrêtent à
   la ligne, les piétons traversent, les cyclistes sont sur leur bande.
2. **Déclencher une urgence** — bouton `+` sur la ligne *Urgences*.
   Commentez à voix haute pendant que ça se passe :
   - l'axe passe en rouge : c'est la voie réservée
   - les panneaux *SAUF URGENCES* s'allument aux deux entrées
   - le compte à rebours annonce l'arrivée
   - les véhicules présents sont déviés, la voie se vide
   - les autres se rangent à droite quand elle approche
3. **Les statistiques** du panneau latéral : le temps moyen des urgences
   face à celui des véhicules ordinaires.
4. **Les bases**, sur chaque VM, pour prouver la répartition.

**Si la démonstration tombe en panne**, ne vous acharnez pas : ouvrez
les requêtes SQL sur les données déjà enregistrées. Les résultats
existent indépendamment de l'affichage. C'est pour cela qu'il faut
avoir fait tourner la simulation **avant** la soutenance : la base
contient alors de vraies mesures à montrer.

---

## 4. Les chiffres à connaître

### Mesurés sur les VM, en conditions réelles

| | Temps moyen de traversée |
|---|---|
| Véhicule d'urgence | **14,0 s** |
| Véhicule ordinaire | 98,1 s |

Sur **792 usagers** enregistrés en base. Soit un rapport de **7**.

### L'étude comparative, cinq configurations

| Configuration | Temps moyen | Pire cas |
|---|---|---|
| Aucun système | 31,8 s | 100 s (bloquée) |
| Préemption des feux seule | **46,3 s** | 100 s |
| + Voie réservée et déviation | 12,0 s | 15,4 s |
| + Serrage à droite | 9,4 s | 14,4 s |
| + Alerte anticipée 12 s | **7,5 s** | 10,4 s |

### Le prix à payer, à citer spontanément

Sur une session complète : **407 véhicules**, 210 cyclistes,
116 piétons, et **20 accidents**. Les déviations forcées se comptent en
dizaines.

**Citez ces chiffres vous-même.** Un jury qui découvre un coût caché
doute de tout le reste ; un candidat qui l'annonce montre qu'il a
compris son propre système.

---

## 5. Les questions probables

### Sur l'architecture

**« Pourquoi avoir réparti ainsi plutôt qu'autrement ? »**
Nous avons séparé le métier du réseau. La VM1 ne fait que calculer et
ignore tout des clients ; la VM2 ne fait que relayer et ignore tout des
règles de priorité. Conséquence utile : le cœur métier n'est jamais
exposé, un client ne joint jamais la VM1. Et chaque base est placée
auprès du processus qui écrit dedans.

**« Pourquoi le client ne tourne-t-il pas sur une VM dédiée ? »**
Dans un déploiement réel, les deux VM sont l'infrastructure du
carrefour, et le poste de supervision est une machine d'opérateur.
C'est le rôle que joue la machine qui lance l'interface. Techniquement,
elle peut être n'importe laquelle des deux VM ou le poste hôte : seule
l'adresse de la passerelle change.

**« Que se passe-t-il si la liaison entre les VM tombe ? »**
La passerelle continue de servir ses clients et les prévient du mode
dégradé ; elle réessaie toutes les 3 secondes et se reconnecte seule.
C'est démontrable en direct : arrêtez le moteur, l'interface le
signale ; relancez-le, la connexion revient sans rien relancer.

### Sur le réseau

**« Pourquoi des sockets bruts et pas MQTT ? »**
Le sujet l'impose, et cela nous a obligés à traiter un vrai problème :
TCP transporte un flux d'octets, pas des messages. Rien ne garantit
qu'un `recv()` corresponde à un `sendall()`.

**« Comment découpez-vous les messages, alors ? »**
Chaque message est un objet JSON sur une seule ligne, terminé par `\n`.
Le receveur accumule, découpe sur le séparateur, traite les messages
complets et **conserve le reste** pour la réception suivante. Sans ce
reste, un message coupé en deux serait perdu. C'est
`protocole.extraire_messages`, en huit lignes.

**« Comment garantissez-vous qu'un thread ne touche pas à l'interface ? »**
Le thread réseau ne fait que recevoir et **émettre des signaux Qt**. Qt
bascule lui-même vers le thread principal, seul endroit où les widgets
sont modifiés. Tout cela tient dans `client/thread_reseau.py`, 118
lignes, le seul fichier où les deux threads se rencontrent.

**« Et dans l'autre sens, quand on clique sur un bouton ? »**
La commande part sur le socket sous un verrou, sans toucher à aucun
widget. Côté moteur, elle n'est pas appliquée à l'arrivée : elle attend
dans une `queue.Queue` et le moteur la traite **entre deux ticks**. Le
moteur n'est donc jamais modifié par deux threads simultanément, sans
aucun verrou dans la logique métier.

### Sur les choix métier

**« Pourquoi la préemption des feux seule est-elle pire que rien ? »**
Le feu vert retient le trafic perpendiculaire, mais ne vide pas la file
déjà présente devant l'ambulance, sur sa propre voie. Elle se retrouve
derrière des véhicules qui ont le vert et nulle part où aller. C'est un
résultat connu en régulation de trafic, et nos mesures le retrouvent :
46,3 s contre 31,8 s sans rien.

**« Pourquoi bloquer le trafic d'en face ? »**
Sans cela, un véhicule qui tourne à gauche devant l'ambulance doit lui
céder le passage ; il reste donc immobile au milieu du carrefour et la
bloque. C'est contre-intuitif : on bloque *plus* de monde pour aller
*plus* vite.

**« Pourquoi 12 secondes d'anticipation ? »**
C'est le délai qui laisse la voie se vider avant l'arrivée. La
préemption renforcée, elle, n'intervient qu'aux 6 dernières secondes :
plus tôt elle bloquerait piétons et trafic inutilement, plus tard les
véhicules qui tournent à gauche n'auraient pas le temps de dégager.

**« Une urgence plus prioritaire peut-elle voler le couloir ? »**
Seulement si le bénéficiaire actuel **n'est pas encore arrivé**. Un
véhicule déjà engagé ne perd jamais sa priorité : la lui retirer en
pleine traversée serait dangereux.

### Les questions qui déstabilisent

**« Vous avez 20 accidents. N'est-ce pas un échec ? »**
Non, c'est une limite assumée et mesurée. Nous sommes passés de 2 402
collisions à environ 5 pour 12 000 ticks après les corrections de
priorité. Les cas restants surviennent dans des configurations de
croisement serrées. Les supprimer totalement demanderait un système de
réservation d'intersection, que nous citons dans les limites.

**« Vos temps sont en pixels par tick, pas en mètres par seconde. »**
Exact, et c'est une limite que nous assumons. Les débits sont calibrés
pour rester sous la capacité réelle d'un carrefour à feux, environ
1 800 véhicules par heure, mais les distances ne sont pas en unités
réelles. Nos résultats sont donc des **comparaisons relatives** entre
configurations, valides parce que mesurées sur des situations de trafic
identiques — pas des temps absolus transposables à Mulhouse.

**« Pourquoi un garde-fou de 5 secondes ? C'est arbitraire. »**
Oui, c'est empirique, et nous le disons. Sans lui, un usager rangé
attend une ambulance elle-même bloquée plus loin, et tout le monde
s'attend mutuellement. La valeur vient de l'observation, pas d'un
calcul. Un système de réservation d'intersection rendrait ce genre de
garde-fou inutile.

**« Qu'est-ce qui ne marche pas dans votre projet ? »**
Question piège classique : répondre « rien » est la pire réponse.
Les limites réelles : une seule voie par sens, les urgences vont tout
droit, la déviation choisit une branche au hasard plutôt que la moins
chargée, pas de modélisation des pertes réseau, et aucun test
automatisé — nos validations sont manuelles.

---

## 6. À faire la veille

- [ ] Faire tourner la simulation 20 minutes pour remplir les bases
- [ ] Arrêter la passerelle avec `Ctrl+C` pour écrire un bilan de session
- [ ] Vérifier que les deux VM redémarrent et se reconnectent
- [ ] Relire les quatre mécanismes de `DOCUMENTATION.md`
- [ ] Se répartir les parties à présenter, et savoir répondre sur
      celles de l'autre
