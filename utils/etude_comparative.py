"""Étude comparative des mécanismes de priorisation.

Lance la simulation sur N situations de trafic identiques (graine fixée)
avec cinq configurations différentes, et produit un tableau de résultats
ainsi qu'un graphique PNG.

Utilisation :
    python utils/etude_comparative.py [nb_situations]

Exemple :
    python utils/etude_comparative.py 20
"""

import os
import sys
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

CONFIGURATIONS = [
    {
        "nom": "1. Aucun système",
        "description": "Feux fixes, pas de priorité",
        "couloir": False,
        "serrage": False,
        "delai_alerte": 0,
    },
    {
        "nom": "2. Préemption des feux",
        "description": "Feux verts + blocage des arrivées sur sa voie",
        "couloir": True,
        "serrage": False,
        "delai_alerte": 0,
        "sans_deviation": True,
    },
    {
        "nom": "3. + Voie réservée",
        "description": "Préemption + sens interdit + déviation",
        "couloir": True,
        "serrage": False,
        "delai_alerte": 0,
    },
    {
        "nom": "4. + Serrage à droite",
        "description": "Config 3 + serrage à droite",
        "couloir": True,
        "serrage": True,
        "delai_alerte": 0,
    },
    {
        "nom": "5. + Alerte anticipée (12 s)",
        "description": "Config 4 + alerte 12 s avant (système complet)",
        "couloir": True,
        "serrage": True,
        "delai_alerte": 360,
    },
]

TICKS_MAX = 3000
NB_TICKS_TRAFIC = 600  # trafic établi avant l'ambulance


def essai(graine, conf):
    """Mesure le temps de traversée d'une ambulance N→S dans une situation de trafic donnée."""
    from simulation.moteur import MoteurSimulation
    from models.usagers_concrets import Vehicule, Pieton

    config.SERRAGE_ACTIF = conf["serrage"]
    config.DELAI_ALERTE = conf["delai_alerte"]
    config.PROBABILITE_URGENCE = 0.0

    random.seed(graine)
    m = MoteurSimulation(dao=None)

    # Désactiver la centrale V2I si "aucun système"
    if not conf["couloir"]:
        m.centrale.traiter_alertes = lambda *a, **k: None
    # Désactiver uniquement la déviation des véhicules (préemption + blocage entrée)
    elif conf.get("sans_deviation"):
        m.centrale._devier_vehicules_genants = lambda *a, **k: None

    for _ in range(NB_TICKS_TRAFIC):
        m.tick()

    amb = Vehicule("N", "S", m.carrefour.construire_route("N", "S"), urgence=True)
    m.centrale.recevoir_alerte(amb, m.tick_courant)

    # Attendre que l'alerte soit traitée (approche)
    while amb.en_approche and not amb.est_sorti:
        m.tick()

    t0 = m.tick_courant
    ticks_arret = 0
    for _ in range(TICKS_MAX):
        m.tick()
        if not isinstance(amb, Pieton) and amb.arrete:
            ticks_arret += 1
        if amb.est_sorti:
            break

    ticks_traversee = m.tick_courant - t0
    return ticks_traversee, ticks_arret, m.metriques.nb_collisions


def lancer_etude(nb_situations=20):
    print(f"\n{'='*70}")
    print(f"  ÉTUDE COMPARATIVE — {nb_situations} situations de trafic")
    print(f"{'='*70}\n")

    resultats = {conf["nom"]: [] for conf in CONFIGURATIONS}

    for conf in CONFIGURATIONS:
        print(f"  Test : {conf['nom']} ({conf['description']})")
        for g in range(1, nb_situations + 1):
            ticks, arret, collisions = essai(g, conf)
            resultats[conf["nom"]].append((ticks, arret, collisions))
            sys.stdout.write(f"\r    Progression : {g}/{nb_situations}")
            sys.stdout.flush()
        print()

    print(f"\n{'='*70}")
    print(f"  RÉSULTATS")
    print(f"{'='*70}")
    print(f"\n  {'Configuration':<35} {'Moy (s)':>8} {'Arrêt (s)':>10} {'Pire (s)':>9} {'Collisions':>11}")
    print(f"  {'-'*35} {'-'*8} {'-'*10} {'-'*9} {'-'*11}")

    base = None
    tableau_export = []

    for conf in CONFIGURATIONS:
        r = resultats[conf["nom"]]
        n = len(r)
        moy = sum(x[0] for x in r) / n / config.TICKS_PAR_SECONDE
        arret = sum(x[1] for x in r) / n / config.TICKS_PAR_SECONDE
        pire = max(x[0] for x in r) / config.TICKS_PAR_SECONDE
        col = sum(x[2] for x in r)

        if base is None:
            base = moy
            gain_txt = "référence"
        else:
            gain = (1 - moy / base) * 100
            gain_txt = f"−{gain:.0f} %"

        print(f"  {conf['nom']:<35} {moy:>6.1f} s {arret:>8.1f} s {pire:>7.1f} s {col:>9}  ({gain_txt})")
        tableau_export.append({
            "nom": conf["nom"],
            "moy": round(moy, 1),
            "arret": round(arret, 1),
            "pire": round(pire, 1),
            "collisions": col,
        })

    print(f"\n  {'='*70}\n")
    exporter_csv(tableau_export)
    exporter_graphique(tableau_export)
    return tableau_export


def exporter_csv(tableau):
    chemin = os.path.join(os.path.dirname(__file__), "resultats_comparatifs.csv")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("Configuration,Temps moyen (s),Temps a l'arret (s),Pire cas (s),Collisions\n")
        for r in tableau:
            f.write(f"{r['nom']},{r['moy']},{r['arret']},{r['pire']},{r['collisions']}\n")
    print(f"  📄 Résultats exportés : {chemin}")


def exporter_graphique(tableau):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        noms = [r["nom"].split(". ", 1)[1] if ". " in r["nom"] else r["nom"] for r in tableau]
        moyennes = [r["moy"] for r in tableau]
        pires = [r["pire"] for r in tableau]

        fig, ax = plt.subplots(figsize=(10, 5))
        x = range(len(noms))
        barres = ax.bar(x, moyennes, color=["#94A3B8", "#60A5FA", "#3B82F6", "#F59E0B", "#22C55E"], width=0.5)
        ax.plot(x, pires, "r--o", label="Pire cas", markersize=5)

        for barre, val in zip(barres, moyennes):
            ax.text(barre.get_x() + barre.get_width() / 2, barre.get_height() + 0.3,
                    f"{val:.1f} s", ha="center", va="bottom", fontsize=9, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(noms, rotation=15, ha="right", fontsize=9)
        ax.set_ylabel("Temps de traversée (s)")
        ax.set_title("Temps de traversée de l'ambulance selon les mécanismes activés")
        ax.legend()
        ax.set_ylim(0, max(pires) * 1.2)
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()

        chemin = os.path.join(os.path.dirname(__file__), "graphique_comparatif.png")
        plt.savefig(chemin, dpi=150)
        print(f"  📊 Graphique exporté  : {chemin}")
    except ImportError:
        print("  ℹ️  matplotlib non installé : graphique non généré.")
        print("     Installe-le avec : pip install matplotlib")


if __name__ == "__main__":
    nb = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    lancer_etude(nb)
