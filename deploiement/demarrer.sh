#!/bin/bash
# Demarre le service correspondant au role de la VM.
#
# A executer DANS la VM, depuis la racine du projet, apres l'avoir
# provisionnee avec deploiement/installer_vm.sh.
#
# Usage :
#     ./deploiement/demarrer.sh moteur       # sur la VM1
#     ./deploiement/demarrer.sh passerelle   # sur la VM2
#
# Le script charge les variables d'environnement ecrites par
# l'installateur, puis lance le service au premier plan : les messages
# s'affichent a l'ecran et Ctrl+C arrete proprement (ce qui, sur la
# VM2, enregistre le bilan de la session en base).

set -uo pipefail

ROLE="${1:-}"
if [[ "$ROLE" != "moteur" && "$ROLE" != "passerelle" ]]; then
    echo "Usage : $0 [moteur|passerelle]" >&2
    exit 1
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f /etc/carrefour.env ]]; then
    echo "Fichier /etc/carrefour.env introuvable." >&2
    echo "Lancez d'abord : sudo bash deploiement/installer_vm.sh $ROLE" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1091
. /etc/carrefour.env
set +a

PYTHON="venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="python3"

if [[ "$ROLE" == "moteur" ]]; then
    echo "Demarrage du moteur (VM1). Ctrl+C pour arreter."
    exec "$PYTHON" serveur/main_moteur.py
else
    echo "Demarrage de la passerelle (VM2). Ctrl+C pour arreter."
    exec "$PYTHON" serveur/main_passerelle.py
fi
