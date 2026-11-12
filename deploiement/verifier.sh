#!/bin/bash
# Verifie qu'une VM remplit les conditions pour heberger un role du
# projet, et diagnostique les pannes apres deploiement.
#
# A lancer AVANT le provisionnement pour reperer ce qui manque, ou
# APRES pour comprendre pourquoi quelque chose ne demarre pas.
#
# Usage :
#     ./deploiement/verifier.sh                      # etat de cette VM
#     ./deploiement/verifier.sh 192.168.56.10        # + joint-on la VM1 ?
#
# Le script ne modifie rien.

cd "$(dirname "${BASH_SOURCE[0]}")/.."

IP_AUTRE="${1:-}"
problemes=0

titre()  { echo; echo "=== $1 ==="; }
ok()     { echo "  [ OK ]   $1"; }
souci()  { echo "  [ A VOIR ] $1"; problemes=$((problemes + 1)); }

titre "Systeme"
if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    ok "$PRETTY_NAME"
else
    souci "Distribution inconnue"
fi
echo "  Machine : $(hostname)"

titre "Outils de base"
for outil in python3 git sudo; do
    if command -v "$outil" >/dev/null; then
        ok "$outil present"
    else
        souci "$outil absent  ->  apt install $outil (en root : su -)"
    fi
done

titre "Version de Python"
if command -v python3 >/dev/null; then
    V=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
        ok "Python $V (3.11+ requis)"
    else
        souci "Python $V : il faut 3.11 ou plus recent"
    fi
fi

titre "Acces reseau"
if ping -c 1 -W 3 deb.debian.org >/dev/null 2>&1; then
    ok "Internet joignable (necessaire pour apt)"
else
    souci "Pas d'acces Internet : apt et git clone echoueront"
fi

echo "  Adresses de cette machine :"
ip -brief addr show 2>/dev/null | grep -v '^lo' | sed 's/^/    /'

# Une carte UP sans adresse IPv4 est le symptome typique d'un profil
# NetworkManager absent ou partage entre deux cartes : chaque
# "nmcli device connect" le deplace sur la carte demandee et l'autre
# perd son adresse. Sur une VM a deux cartes, les deux doivent en avoir.
for carte in $(ls /sys/class/net 2>/dev/null | grep -E '^(en|eth)'); do
    if ! ip -4 addr show "$carte" 2>/dev/null | grep -q 'inet '; then
        souci "$carte est active mais n'a aucune adresse IPv4  ->  refaites l'etape 2 du guide avec IP_LOCALE (un profil NetworkManager par carte)"
    fi
done

if [[ -n "$IP_AUTRE" ]]; then
    if ping -c 2 -W 3 "$IP_AUTRE" >/dev/null 2>&1; then
        ok "$IP_AUTRE joignable"
    else
        souci "$IP_AUTRE injoignable : les deux VM doivent partager une carte reseau"
    fi
fi

titre "Base de donnees"
if command -v mariadb >/dev/null || command -v mysql >/dev/null; then
    ok "client MariaDB present"
    if systemctl is-active --quiet mariadb 2>/dev/null; then
        ok "service mariadb demarre"
    else
        souci "service mariadb arrete  ->  sudo systemctl start mariadb"
    fi
else
    echo "  (MariaDB pas encore installe : installer_vm.sh s'en charge)"
fi

titre "Deploiement du projet"
if [[ -f /etc/carrefour.env ]]; then
    if [[ -r /etc/carrefour.env ]]; then
        ok "/etc/carrefour.env lisible"
        echo "    Configuration active :"
        grep -v PASSWORD /etc/carrefour.env | sed 's/^/      /'
    else
        souci "/etc/carrefour.env existe mais n'est pas lisible par $USER"
    fi
else
    echo "  (pas encore provisionnee : lancez installer_vm.sh)"
fi

if [[ -x venv/bin/python ]]; then
    ok "environnement Python present"
    if venv/bin/python -c "import mysql.connector" 2>/dev/null; then
        ok "connecteur MariaDB installe"
    else
        souci "connecteur MariaDB absent de l'environnement"
    fi
else
    echo "  (environnement Python pas encore cree)"
fi

titre "Services en cours"
for motif in "[m]ain_moteur.py:moteur (VM1)" "[m]ain_passerelle.py:passerelle (VM2)"; do
    p="${motif%%:*}"; nom="${motif##*:}"
    if pgrep -f "$p" >/dev/null; then ok "$nom en cours d'execution"; fi
done
command -v ss >/dev/null && ss -ltn 2>/dev/null | grep -E ':(5050|5051)' | sed 's/^/    /'

echo
if [[ $problemes -eq 0 ]]; then
    echo "=========================================================="
    echo " Aucun probleme detecte."
    echo "=========================================================="
else
    echo "=========================================================="
    echo " $problemes point(s) a corriger, voir [ A VOIR ] ci-dessus."
    echo " Le tableau de depannage de deploiement/README.md detaille"
    echo " les causes les plus frequentes."
    echo "=========================================================="
fi
