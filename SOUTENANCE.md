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
