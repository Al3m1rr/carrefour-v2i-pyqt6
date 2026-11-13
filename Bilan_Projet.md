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
