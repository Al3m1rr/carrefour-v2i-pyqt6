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
