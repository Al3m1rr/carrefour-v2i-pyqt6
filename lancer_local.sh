#!/bin/bash
# Demarre les trois roles du projet sur une seule machine (Linux / macOS).
#
# Equivalent de LANCER_TOUT.bat sous Windows. C'est le chemin le plus
# rapide pour voir le projet fonctionner sans monter les deux VM : les
# trois processus tournent en local et dialoguent par sockets, comme ils
# le feraient a travers le reseau.
#
# Les bases MariaDB ne sont pas necessaires ici : si elles sont absentes,
# la simulation tourne sans enregistrement et le signale au demarrage.
#
# Usage :
#     ./lancer_local.sh
#     Ctrl+C pour tout arreter.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON="${PYTHON:-python3}"

export CARREFOUR_MOTEUR_ECOUTE=127.0.0.1
export CARREFOUR_MOTEUR_HOTE=127.0.0.1
export CARREFOUR_MOTEUR_PORT=5051
export CARREFOUR_SOCKET_ECOUTE=127.0.0.1
export CARREFOUR_SOCKET_SERVEUR_HOTE=127.0.0.1
export CARREFOUR_SOCKET_PORT=5050

pids=()
arreter() {
    echo
    echo "Arret des processus..."
    for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
    wait 2>/dev/null
    exit 0
}
trap arreter INT TERM

echo "--> VM1 : moteur de simulation"
$PYTHON serveur/main_moteur.py &
pids+=($!)
sleep 2

echo "--> VM2 : passerelle reseau"
$PYTHON serveur/main_passerelle.py &
pids+=($!)
sleep 2

echo "--> Client PyQt6"
$PYTHON client/main_client.py &
pids+=($!)

echo
echo "Les trois roles tournent. Ctrl+C pour tout arreter."
echo "Pour declencher une alerte ambulance depuis un autre terminal :"
echo "    $PYTHON ambulance/main_ambulance.py 127.0.0.1 5050 1 N"
wait
