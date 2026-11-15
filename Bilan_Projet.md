# Bilan de projet

**SAÉ 3.02 — Carrefour intelligent connecté**

Groupe « Python Mayo » — Atakan Gocer · Louise Halter-Tisler

---

## 1. Bilan des fonctionnalités mises en œuvre

Cette revue confronte, ligne à ligne, le livrable au périmètre du
cahier des charges déposé le 24 septembre 2026. Celui-ci classait 24
fonctionnalités selon la méthode MoSCoW. Seules les 16 classées *Must*
et *Should*, soit 100 heures estimées, constituaient un engagement.

### Synthèse

| Catégorie | Prévues | Fait | Partiel | Non retenu |
|---|---|---|---|---|
| Must have | 10 | 10 | 0 | 0 |
| Should have | 6 | 5 | 1 | 0 |
| **Engagé (Must + Should)** | **16** | **15** | **1** | **0** |
| Could have | 4 | 0 | 1 | 3 |
| Won't have | 4 | exclues du périmètre, aucune développée | | |

**Tout le périmètre engagé a été livré**, dans le respect du cahier des
charges. Les quatre *Could have*, optionnels par définition, n'étaient
pas un engagement : l'export des statistiques est réalisé pour l'étude
comparative, et les trois autres sont des pistes d'évolution identifiées.

### Revue fonctionnalité par fonctionnalité

| Fonctionnalité | Priorité | Statut | Ce qui a été livré |
|---|---|---|---|
| Moteur de simulation | Must | **Fait** | Simulation à 30 pas par seconde : usagers, trajectoires avec virages, dynamique avec freinage plus fort que l'accélération |
| Géométrie et Code de la route | Must | **Fait** | Voies entrante et sortante distinctes, arrêt à la ligne, priorité au piéton engagé, refus de priorité en tourne-à-gauche (R415-5), interdiction de bloquer le carrefour |
| Feux avec phase de dégagement | Must | **Fait** | Cycle vert, orange, « tout rouge » entre deux axes |
| Protocole applicatif sur sockets TCP | Must | **Fait** | Messages JSON sur une ligne, découpés par un délimiteur, avec conservation du message incomplet (`protocole.py`, 48 lignes) |
| Serveur multi-clients | Must | **Fait** | Un thread de lecture par client et une file thread-safe ; la même classe sert sur les deux VM |
| IHM PyQt6 | Must | **Fait** | `QGraphicsScene` : routes, usagers orientés, feux, passages piétons, panneaux dynamiques |
| Thread réseau Qt | Must | **Fait** | `QThread` et `pyqtSignal` ; aucun widget n'est touché hors du thread principal |
| Persistance MariaDB | Must | **Fait** | Schéma, DAO et historique des usagers. Seuls les accidents sont journalisés dans la table des événements |
| Centrale V2I | Must | **Fait** | Voie réservée, forçage des feux, déviation des usagers gênants, jamais d'un véhicule déjà engagé |
| Alertes anticipées et priorités | Must | **Fait** | Alerte douze secondes avant l'arrivée, niveaux P1 à P3, arbitrage entre urgences concurrentes |
| Serrage à droite | Should | **Fait** | Décalage latéral, ralentissement, feux de détresse ; trois garde-fous issus de l'observation |
| Tableau de bord et métriques | Should | **Fait** | Collisions, déviations forcées, temps moyen des urgences et des véhicules ordinaires, alertes en cours |
| Commandes opérateur | Should | **Fait** | Ajout et retrait de chaque type d'usager, choix du niveau de priorité des alertes |
| Étude comparative | Should | **Fait** | Cinq configurations mesurées sur des situations de trafic identiques (la même suite d'usagers aléatoires est rejouée à l'identique), résultats en CSV et en graphique |
| Authentification HMAC des alertes | Should | **Fait** | Signature HMAC-SHA256 des alertes du boîtier ambulance ; une alerte à signature invalide est rejetée |
| Mode dégradé en cas de perte réseau | Should | **Partiel** | Le client détecte la perte, passe en rouge, désactive ses boutons et se reconnecte seul ; la passerelle prévient aussi les clients quand le moteur tombe. La bascule des feux en cycle fixe n'est pas simulée |
| Export des statistiques | Could | **Partiel** | Fait pour l'étude comparative (CSV et histogramme PNG). Les statistiques de session restent consultables en base, sans export |
| Comportement des véhicules autonomes | Could | Non retenu | Les véhicules autonomes existent comme type (35 % du trafic, affichés en orange) ; une conduite spécifique est une piste d'évolution |
| Taux de non-respect paramétrable | Could | Non retenu | Tous les usagers respectent les règles : piste d'évolution |
| Latence et pertes réseau simulées | Could | Non retenu | La coupure franche est gérée, avec reconnexion automatique ; la latence simulée est une piste d'évolution |
| Enchaînement de plusieurs carrefours | Won't | Exclu | Respecté : un seul carrefour |
| Déploiement sur matériel réel | Won't | Exclu | Respecté |
| Cartographie réelle de Mulhouse | Won't | Exclu | Respecté : carrefour générique |
| Rendu 3D | Won't | Exclu | Respecté : vue de dessus 2D |

### Les adaptations par rapport au cahier des charges

**La répartition sur les machines virtuelles.** Le cahier des charges
prévoyait une *VM Serveur* portant le moteur, la centrale V2I, le
serveur de sockets et la base, et une *VM Client* portant l'interface.
Le client ayant demandé de répartir les **processus et les bases**, nous
avons adapté l'architecture : la VM1 porte le moteur et la base des
usagers, la VM2 porte la passerelle réseau et la base des sessions,
liées par un socket TCP interne. L'interface tourne dans la VM2. La
base unique à trois tables est devenue deux bases.

**Le système d'exploitation.** Le déploiement s'est fait sur Debian 13,
imposée pour les machines virtuelles.

**La gestion de version.** Le projet est livré sur un dépôt GitHub
public, avec 60 commits aux messages explicites, comme demandé.

**Le déploiement.** Un parcours unique, validé à trois reprises (voir
§ 2), permet à un tiers de redéployer le projet depuis le ZIP du dépôt
sur les postes de l'IUT.

### Pistes d'évolution

Le périmètre engagé étant livré, voici les extensions que nous avons
identifiées :

- les trois *Could have* restants : conduite propre aux véhicules
  autonomes, taux de non-respect paramétrable, latence et pertes
  simulées ;
- une réservation d'intersection, qui remplacerait les garde-fous
  empiriques actuels et supprimerait probablement les collisions
  résiduelles, environ cinq pour 12 000 pas de simulation (environ 6 min 40 s de trafic) ;
- la comparaison du temps de traversée des usagers ordinaires d'une
  configuration à l'autre, qui compléterait la mesure du gain obtenu
  pour les urgences ;
- des unités physiques (mètres, secondes) : nos résultats sont
  aujourd'hui des comparaisons relatives.

---

## 2. Conclusion technique

### Un choix de conception ancré dans l'existant

Avant de concevoir le système, nous nous sommes documentés sur ce qui
existe déjà pour donner la priorité aux véhicules de secours. Nous
voulions un projet **réaliste et réalisable dans la vraie vie**, et non
un scénario futuriste qui supposerait des infrastructures et des budgets
hors de portée.

- **La préemption des feux** par un émetteur embarqué sur le véhicule de
  secours existe déjà (systèmes de type *Opticom*, optiques puis GPS et
  radio, avec messages à code de sécurité et choix du véhicule le plus
  prioritaire). Elle inspire notre centrale V2I, nos niveaux de priorité
  et la signature HMAC des alertes.
- **L'alerte aux conducteurs** à l'approche d'un véhicule d'urgence est
  normalisée en Europe dans les services coopératifs C-ITS (norme ETSI
  TS 101 539-1) et a été testée en conditions réelles, notamment à
  Salzburg avec la Croix-Rouge. Notre alerte anticipée s'en inspire.
- **Le Code de la route** appliqué est celui d'aujourd'hui.

Il en découle des choix sobres : un seul équipement ajouté au véhicule
de secours, des actions que sait déjà faire un gestionnaire de voirie
(commander les feux, allumer un panneau), aucun usager obligatoirement
équipé, et des échanges en JSON sur TCP qu'une liaison radio dédiée
remplacerait en situation réelle. Les sources sont indiquées dans le
`README.md` du dépôt.

### Les difficultés rencontrées, et comment nous les avons levées

**La préemption des feux ne suffisait pas — et faisait pire.** Notre
première solution forçait le feu au vert à l'approche d'une ambulance.
Les mesures ont montré qu'elle était **moins bonne que ne rien faire**
(46,3 s contre 31,8 s). La raison : le feu vert retient le trafic
perpendiculaire mais ne vide pas la file déjà présente sur la voie de
l'ambulance, qui se retrouve bloquée derrière des véhicules ayant le
vert et nulle part où aller. C'est ce constat qui a fait naître la voie
réservée, avec déviation active des usagers gênants.

**Nos chiffres ne prouvaient pas ce que nous affirmions.** Nous
attribuions le gain à la voie réservée sans l'avoir isolé de celui de
la préemption des feux. Nous avons construit une étude par ablation :
cinq configurations, chacune ajoutant un mécanisme, mesurées sur des
situations de trafic identiques. C'est elle qui a révélé le résultat
contre-intuitif ci-dessus.

**Les collisions.** Les premières versions en produisaient plus de
2 400 pour 12 000 pas de simulation. Le travail sur les règles de priorité —
trajectoires sécantes, refus de priorité en tourne-à-gauche,
interdiction de bloquer le carrefour — les a ramenées à environ cinq.
Les cas restants surviennent dans des configurations de croisement
serrées ; les supprimer demanderait une réservation d'intersection.

**Les interblocages du serrage à droite.** Quand un usager se range
pour une ambulance elle-même bloquée plus loin, tout le monde s'attend
mutuellement. Nous avons ajouté un garde-fou : au-delà de cinq
secondes, l'usager cesse de céder le passage à cette ambulance. La
valeur est empirique, issue de l'observation, et nous l'assumons comme
telle.

**Le découpage en deux processus.** Séparer le moteur de la passerelle
a soulevé un problème que le montage monolithique masquait : quand la
passerelle transmet une commande au moteur, comment la réponse
revient-elle au **bon** client ? Nous avons étiqueté chaque commande
avec l'identifiant de son émetteur, que le moteur renvoie dans sa
réponse. Cette étiquette est purement interne : elle ne quitte jamais
la passerelle en direction des clients.

**Le réseau entre machines virtuelles.** C'est ce qui nous a coûté le
plus de temps au déploiement. Les VM fournies n'avaient qu'un seul
profil réseau, rattaché à aucune carte : chaque tentative de réparer
une interface faisait perdre son adresse à l'autre. Nous avons fini par
créer un profil par carte, avec des adresses fixes, ce qui a supprimé
le problème à la racine.

**Des bugs invisibles à la lecture.** Trois défauts n'ont été découverts
qu'en déployant réellement : un attribut inexistant dans un chemin de
code jamais exécuté sans base de données, une détection de carte réseau
qui configurait la mauvaise tout en paraissant correcte, et un message
affirmant un enregistrement qui n'avait pas eu lieu. Ils sont détaillés
dans l'[IA-graphie](IAGraphie.md).

### Validation du déploiement

Le déploiement a été rejoué à trois reprises : le 8 novembre sur des
machines virtuelles vierges, le 12 novembre sur les machines virtuelles
des postes de l'IUT, puis le 13 novembre à partir du ZIP téléchargé
depuis GitHub. À chaque fois, la simulation a fonctionné sur les deux
machines virtuelles, avec les processus et les bases répartis.

### Les choix que nous confirmons

**Le choix de la voie réservée** plutôt que la seule préemption des
feux. C'est ce qui fait l'intérêt du projet, et la mesure le confirme.

**L'étude comparative par ablation.** Elle transforme une affirmation
en démonstration, et c'est elle qui donne de la valeur à nos chiffres.

**La séparation stricte des rôles.** Un seul composant décide, les
autres transmettent et affichent. Cette discipline a rendu le découpage
sur deux machines presque mécanique le jour où il a fallu le faire.

---

## 3. Conclusion organisationnelle

### Notre méthode de travail

Nous avons réalisé **l'ensemble du projet ensemble**, sans répartir les
modules par personne : le code, les tests de déploiement et la
documentation. Ce choix nous a permis de comprendre tous les deux
l'intégralité du projet, ce qui est nécessaire pour une soutenance où
chacun peut être interrogé sur n'importe quelle partie.

Les rôles de cabinet conseil et de cabinet développement, évoqués dans
la fiche de cadrage, n'ont pas été distingués en pratique : chacun a
contribué à toutes les parties.

### Des emplois du temps complémentaires

Nous ne sommes pas dans le même groupe de travaux pratiques : Atakan
relève de RoM et Louise de DevCloud. Nos séances d'autonomie
n'étaient donc pas les mêmes. Atakan, en alternance du 5 octobre au 2
novembre, a poursuivi le travail en dehors des séances, ce qui nous a
permis de conserver un rythme régulier sur l'ensemble du projet.

### L'usage de l'IA dans notre organisation

Nous avons utilisé Claude tout au long du projet. Cela a changé notre
façon de travailler : moins de temps passé à écrire du code, davantage
à spécifier ce que nous voulions, à tester, et à comprendre les
réponses obtenues. L'[IA-graphie](IAGraphie.md) détaille cet usage.

Un effet que nous n'avions pas anticipé : notre contribution la plus
décisive a été **le test en conditions réelles**. Trois bugs qu'aucune
relecture n'aurait détectés ne sont apparus qu'en déployant sur les
machines virtuelles.

---

## 4. Analyse du planning

### Le planning prévisionnel

Le cahier des charges déposé le **24 septembre** prévoyait sept jalons
répartis des semaines 39 à 46, pour une charge estimée à **100 heures
de groupe** — 72 heures pour le périmètre *Must*, 28 pour le *Should*.

### Le temps réellement consommé

| | Volume de groupe |
|---|---|
| **Estimation** du cahier des charges | 100 h |
| Séances d'autonomie encadrées | **44 h** |
| Travail personnel hors séances | **≈ 60 h** (estimation) |
| **Total réalisé** | **≈ 104 h** |

Les séances d'autonomie inscrites à l'emploi du temps se sont étalées
de la semaine 37 à la semaine 46, à raison de trois à dix heures par
semaine selon les périodes. Le chiffre du travail personnel est une
estimation.

### L'analyse de l'écart

**L'estimation globale était juste.** 104 heures réalisées pour 100
prévues : à quatre heures près, nous avions correctement évalué
l'ampleur du travail.

**Un projet tenu grâce à l'investissement du groupe.** Environ 60 % du
projet a été réalisé en dehors des séances encadrées. Ce travail
personnel nous a permis de livrer l'intégralité du périmètre engagé et
de tenir les jalons.

**Le déploiement, un poste à part entière.** Il a occupé plusieurs
journées, pour des raisons propres à l'environnement des machines
virtuelles : profils réseau, droits d'administration, variables
d'environnement graphiques. Il est désormais automatisé par des scripts
et documenté pas à pas.

**Ce que nous en retenons.** Le temps de mise en production ne se
devine pas, il s'éprouve : c'est en déployant réellement que nous avons
fiabilisé le projet.

### Le déroulement réel face aux jalons

| Jalon | Prévu | Réalisé | Écart |
|---|---|---|---|
| J1 — Cahier des charges | 24 sept. | Déposé le 24 sept. | Tenu |
| J2 — Environnement (VM, réseau, MariaDB, dépôt Git) | S40 | VM, réseau et base en septembre ; dépôt GitHub public pour la livraison | Livré |
| J3 — Noyau de simulation | S42 | Dès la semaine 38 | Environ quatre semaines d'avance |
| J4 — Sockets et IHM PyQt6 | S44 | Vers le 18 sept., semaine 38 | Environ six semaines d'avance |
| J5 — Priorisation V2I complète | S45 | Semaines 39 et 40, d'après l'historique de conception | Environ cinq semaines d'avance |
| J6 — Tests, mesures, corrections | S46 | Mesures comparatives en septembre ; corrections et validation du déploiement en novembre | Réalisé |
| J7 — Livraison finale | 15 nov. | Dépôt, documentation, bilan, IA-graphie | Livré ; soutenance à confirmer |

Le Gantt prévoyait un effort réparti de la semaine 39 à la semaine 46,
avec le pic de priorisation V2I en semaine 43, celui des tests en
semaine 45 et celui de la documentation en semaine 46. La charge s'est
concentrée en **deux blocs** : les semaines 37 à 40, où l'essentiel du
développement a eu lieu, puis les semaines 45 et 46, consacrées au
déploiement et à la documentation. Entre les deux, le code était
stable.

### Les points marquants du déroulement

**La reprise en PyQt6 à la mi-septembre.** Le prototype Pygame a été
porté en PyQt6 avec des sockets, pour respecter la pile technique
imposée. La logique métier a été conservée ; seule la couche technique
a été refaite.

**Un périmètre fonctionnel complet en avance.** Il était réuni dès le
2 octobre, cinq semaines avant le jalon, ce qui a laissé la fin du
projet au déploiement réparti, exigence structurante du sujet.

**La répartition sur deux VM.** Réalisée début novembre, conformément à
la demande du client, elle a conduit à une architecture plus nette
(moteur d'un côté, passerelle de l'autre) et à des correctifs
identifiés en conditions réelles.

**Une documentation qui reflète l'état final.** Rédigée une fois
l'architecture stabilisée, elle décrit le projet tel qu'il est livré.

### La gestion des risques, avec le recul

| Risque prévu | S'est-il produit ? | Mesures prévues | Ce qui s'est passé |
|---|---|---|---|
| Retard sur le moteur de simulation | Non | Jalon J3, périmètre *Could* sacrifiable | Moteur terminé dès la semaine 38 |
| Conflits et collisions entre usagers | Oui, au début : plus de 2 400 collisions pour 12 000 pas | Longues campagnes de tests, scénarios rejouables | Ramenées à environ cinq ; l'étude comparative rejoue à l'identique les mêmes situations de trafic |
| Panne ou perte de temps sur les VM | Oui, plusieurs journées au déploiement | Dépôt distant, instantanés de VM, exécution sur un seul poste | Réseau stabilisé par des profils fixes et des scripts d'installation ; déploiement validé à trois reprises |

Les trois risques identifiés dans le cahier des charges ont été
traités ; le déploiement, le plus exigeant, est aujourd'hui automatisé
et documenté.
