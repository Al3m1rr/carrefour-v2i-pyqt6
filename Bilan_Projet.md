# Bilan de projet

**SAÉ 3.02 — Carrefour intelligent connecté**
Groupe « Python Mayo » — Atakan Gocer · Louise Halter-Tisler

---

## 1. Bilan des fonctionnalités mises en œuvre

> ⚠️ **À compléter avant le rendu** : cette revue est organisée par
> thème, à partir de ce qui a été livré. Il reste à la confronter ligne
> à ligne au tableau MoSCoW du cahier des charges déposé le 24
> septembre, pour vérifier qu'aucune fonctionnalité promise n'est
> oubliée et que le classement Must / Should correspond.

### Pleinement fonctionnel

**La simulation du carrefour.** Quatre branches, voies entrantes et
sortantes distinctes, feux tricolores avec phase de dégagement « tout
rouge », passages piétons en deux demi-traversées et bande cyclable
séparée.

**Les quatre types d'usagers** demandés : véhicules avec conducteur,
véhicules autonomes, cyclistes et piétons. Les autonomes se
distinguent réellement : ils détectent l'alerte d'urgence deux fois
plus tôt et se rangent plus précisément.

**Le respect du code de la route.** Distance de sécurité et freinage
progressif, freinage plus fort que l'accélération, arrêt à la ligne,
orange franchi seulement si l'arrêt est impossible, priorité au piéton
engagé, refus de priorité en tourne-à-gauche (article R415-5),
interdiction de bloquer le carrefour.

**La priorité aux véhicules d'urgence**, par quatre mécanismes
combinés : voie réservée avec déviation du trafic, préemption des feux,
alerte anticipée douze secondes avant l'arrivée, et serrage à droite
des usagers.

**Les niveaux de priorité P1 à P3** avec arbitrage entre urgences
concurrentes : la plus prioritaire d'abord, à priorité égale la
première arrivée, réattribution possible tant que le bénéficiaire n'est
pas arrivé, et partage de la voie entre itinéraires compatibles.

**L'architecture répartie** sur deux machines : moteur et base des
usagers sur la première, passerelle et base des sessions sur la
seconde, liaison par sockets TCP avec protocole JSON écrit par nous.

**L'interface de supervision** en PyQt6 : vue du carrefour, tableau de
bord, ajout et retrait d'usagers par type, choix du niveau de priorité
des alertes.

**La persistance** dans deux bases MariaDB réparties, avec dégradation
propre si une base est absente.

**L'étude comparative** automatisée, qui mesure cinq configurations sur
des situations de trafic identiques.

**Deux fonctions de sécurité** non exigées mais pertinentes : signature
HMAC-SHA256 des alertes du boîtier embarqué, et mode dégradé du client
lorsque la liaison réseau est perdue.

### Modifié en cours de route

**La bibliothèque graphique.** Le premier prototype utilisait Pygame.
Le cahier des charges imposant PyQt6 et interdisant Pygame, toute la
couche technique a été réécrite, la logique métier étant conservée.

**La répartition sur les VM.** Le montage initial plaçait le moteur, le
serveur socket et la base sur une seule machine, la seconde ne portant
que l'interface. Le client ayant demandé une répartition des processus
*et* des bases, l'application a été scindée en deux processus distincts
avec une base chacun.

**L'ouverture du couloir prioritaire.** Initialement déclenchée à
l'apparition du véhicule, elle l'est désormais par une alerte émise
douze secondes avant son arrivée. Les mesures ont montré que la voie
n'avait pas le temps de se vider autrement.

### Non développé, et pourquoi

**La déviation vers la branche la moins chargée.** Les usagers déviés
sont envoyés vers une sortie tirée au hasard. Mesurer la charge de
chaque branche pour choisir la moins encombrée était à notre portée,
mais nous avons priorisé la fiabilité du déploiement réparti.

**Un quota anti-famine** pour l'axe perpendiculaire. La durée maximale
d'un couloir est plafonnée à trente secondes, ce qui limite le
problème sans le traiter formellement.

**La réservation d'intersection.** Elle remplacerait les garde-fous
empiriques actuels et supprimerait probablement les collisions
résiduelles. Chantier trop important pour le temps imparti.

**Les tests automatisés.** Toutes nos validations sont manuelles. C'est
la lacune que nous regrettons le plus : elle nous a interdit de
refactorer le code en fin de projet, faute de pouvoir vérifier
rapidement que rien n'était cassé.

**La calibration en unités réelles.** Les distances sont en pixels et
le temps en ticks. Les débits sont calibrés pour rester sous la
capacité réelle d'un carrefour à feux, mais nos résultats restent des
comparaisons relatives, non des temps transposables tels quels.

**Plusieurs carrefours enchaînés**, qui auraient permis de montrer le
report de trafic provoqué par les déviations.

---

## 2. Conclusion technique

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
2 400 pour 12 000 ticks. Le travail sur les règles de priorité —
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

### Ce que nous ferions autrement

**Écrire des tests dès le début.** C'est notre principal regret. Sans
eux, chaque validation demande un déploiement complet et une
manipulation à la main. En fin de projet, cela nous a interdit de
toucher au code pour l'améliorer, le risque étant disproportionné.

**Transmettre les contraintes avant de produire du code.** Le prototype
Pygame a été entièrement réécrit parce que nous n'avions pas
communiqué le cahier des charges assez tôt.

**Déployer plus tôt en conditions réelles.** Les bugs les plus coûteux
ne se manifestaient que sur les VM, avec une base de données
réellement joignable. Un déploiement dès les premières semaines les
aurait révélés quand il restait du temps.

### Ce que nous referions à l'identique

**Le choix de la voie réservée** plutôt que la seule préemption des
feux. C'est ce qui fait l'intérêt du projet, et la mesure le confirme.

**L'étude comparative par ablation.** Elle transforme une affirmation
en démonstration, et c'est elle qui donne de la valeur à nos chiffres.

**La séparation stricte des rôles.** Un seul composant décide, les
autres transmettent et affichent. Cette discipline a rendu le découpage
sur deux machines presque mécanique le jour où il a fallu le faire.

---

## 3. Conclusion organisationnelle

> ⚠️ **À compléter** : la répartition réelle des tâches entre nous deux
> doit être reprise des comptes rendus hebdomadaires. Les éléments
> ci-dessous décrivent la méthode de travail, pas le détail de qui a
> fait quoi.

### Notre méthode de travail

Nous avons travaillé **en binôme sur l'ensemble des tâches**, sans
répartition par spécialité. Ce choix nous a permis de comprendre tous
les deux l'intégralité du projet, ce qui était nécessaire pour une
soutenance où chacun peut être interrogé sur n'importe quelle partie.
Son revers est que nous avons rarement travaillé en parallèle, donc
avancé moins vite que si nous nous étions répartis les modules.

Les rôles de cabinet conseil et de cabinet développement, évoqués dans
la fiche de cadrage, n'ont pas été distingués en pratique.

### L'usage de l'IA dans notre organisation

Nous avons utilisé Claude tout au long du projet. Cela a changé notre
façon de travailler : moins de temps passé à écrire du code, davantage
à spécifier ce que nous voulions, à tester, et à comprendre les
réponses obtenues. L'[IA-graphie](IAGraphie.md) détaille cet usage,
y compris ce qu'il nous a coûté.

Un effet que nous n'avions pas anticipé : notre contribution la plus
décisive a été **le test en conditions réelles**. Trois bugs qu'aucune
relecture n'aurait détectés ne sont apparus qu'en déployant sur les
machines virtuelles.

---

## 4. Analyse du planning

> ⚠️ **À compléter avant le rendu** : les volumes horaires exacts
> doivent être repris des comptes rendus hebdomadaires, qui seuls font
> foi. Le tableau ci-dessous situe les jalons à partir des traces du
> dépôt et des dates de livraison.

### Le planning prévisionnel

Le cahier des charges déposé le **24 septembre** prévoyait sept jalons
répartis des semaines 39 à 46, pour une charge estimée à **100 heures
de groupe** — 72 heures pour le périmètre *Must*, 28 pour le *Should*.

### L'écart le plus important : le volume horaire

**La charge réelle a nettement dépassé l'estimation**, et surtout elle
s'est déplacée. Les séances encadrées ont toutes été utilisées, mais
elles n'ont couvert qu'une fraction du travail : l'essentiel a été
réalisé en dehors, sur notre temps personnel.

Cet écart n'est pas un simple dépassement de quelques heures. Il
signifie que **notre estimation initiale était structurellement
fausse** : nous avions chiffré la production de code, pas la
compréhension du besoin, les allers-retours de conception, ni le temps
de mise en production, qui s'est révélé être le poste le plus coûteux.

Pourquoi cela ne s'est pas vu plus tôt : la charge supplémentaire étant
absorbée hors séances, elle n'apparaissait pas comme un retard. Les
jalons étaient tenus, mais au prix d'un volume horaire sans rapport
avec le prévisionnel. Un suivi qui n'aurait regardé que les dates de
livraison aurait conclu, à tort, que le planning était respecté.

**Ce que nous en retirons** : estimer une charge demande d'inclure ce
qui n'est pas de la production — lire un cahier des charges, revenir
sur une décision, installer, déboguer, documenter. Dans notre cas, ces
activités ont pesé plus lourd que l'écriture du code elle-même.

### Le déroulement réel

| Période | Ce qui s'est passé |
|---|---|
| Semaine du 8 sept. | Analyse du besoin, préparation des questions au client |
| Semaine du 15 sept. | Premier prototype, puis **réécriture complète** après lecture du cahier des charges imposant PyQt6 |
| 24 sept. | Dépôt du cahier des charges |
| Fin sept. – octobre | Logique métier : voie réservée, alertes anticipées, niveaux de priorité, serrage à droite |
| Octobre | Analyse critique, puis construction de l'étude comparative |
| 2 oct. | Dernières fonctionnalités : application ambulance, signature HMAC, mode dégradé |
| 8 nov. | **Répartition sur deux VM**, premier déploiement réel |
| 12 nov. | Déploiement sur les postes de l'IUT, correction des scripts |
| 13 nov. | Documentation technique, bilan, IA-graphie |
| 15 nov. | Rendu |

### Les écarts et leurs causes

**La réécriture de la mi-septembre.** Le prototype Pygame a été
entièrement refait en PyQt6 avec des sockets. La cause est
identifiable : nous avons commencé à produire du code avant d'avoir lu
et transmis le cahier des charges. La logique métier a pu être
conservée, ce qui a limité la perte, mais toute la couche technique
était à refaire.

**La répartition sur deux VM, tardive.** Elle n'est intervenue qu'au
8 novembre, alors que c'est une exigence structurante du sujet. Jusque-
là, le projet tournait sur une seule machine. Ce report a concentré en
fin de projet un travail d'architecture et de déploiement qui a révélé
des bugs — ceux-là mêmes qui nous ont pris le plus de temps. Les
découvrir en septembre aurait été nettement plus confortable.

**Le déploiement, largement sous-estimé.** Nous avions prévu
l'installation comme une formalité. Elle a occupé deux journées
entières, pour des raisons qui n'avaient rien à voir avec notre code :
profils réseau des machines virtuelles, droits `sudo`, variables
d'environnement graphiques. C'est l'enseignement principal de notre
planning : **le temps de mise en production ne se devine pas**, il
s'éprouve.

**Le temps consacré à la documentation.** Nous l'avons concentré sur
les derniers jours. Rédigée au fil de l'eau, elle aurait été plus
fidèle, notamment sur les décisions de conception dont nous avons dû
retrouver les raisons a posteriori.
