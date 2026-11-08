#!/bin/bash
# Provisionne une des deux VM Debian 13 du projet "Carrefour intelligent".
#
# A executer DANS la VM concernee, apres une installation Debian 13
# standard (voir deploiement/creer_vms.ps1 pour la creation des VM).
#
# Usage :
#     sudo bash deploiement/installer_vm.sh moteur       # sur la VM1
#     sudo bash deploiement/installer_vm.sh passerelle   # sur la VM2
#
# Le script est idempotent : on peut le relancer sans casser l'existant.

set -euo pipefail

ROLE="${1:-}"
if [[ "$ROLE" != "moteur" && "$ROLE" != "passerelle" ]]; then
    echo "Usage : sudo bash $0 [moteur|passerelle]" >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit etre lance avec sudo." >&2
    exit 1
fi

# --- Parametres propres a chaque role --------------------------------
if [[ "$ROLE" == "moteur" ]]; then
    IP_LOCALE="${IP_LOCALE:-192.168.56.10}"
    BASE="carrefour_moteur_db"
    SCHEMA="schema_moteur.sql"
else
    IP_LOCALE="${IP_LOCALE:-192.168.56.11}"
    BASE="carrefour_stats_db"
    SCHEMA="schema_passerelle.sql"
fi

DB_USER="${DB_USER:-carrefour_user}"
DB_MDP="${DB_MDP:-CarrefourDB2026!}"
PROJET="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo " Provisionnement de la VM : role $ROLE"
echo " Base    : $BASE"
echo " IP      : $IP_LOCALE (reseau prive hote)"
echo " Projet  : $PROJET"
echo "=========================================================="

# --- 1. Paquets ------------------------------------------------------
echo "--> Installation des paquets"
apt-get update -qq
apt-get install -y -qq mariadb-server python3 python3-venv python3-pip git

# --- 2. Reseau prive entre les deux VM -------------------------------
# La seconde carte reseau (reseau prive hote) n'est pas configuree par
# l'installateur Debian : on lui fixe une IP statique pour que les deux
# VM se joignent toujours a la meme adresse.
echo "--> Configuration du reseau prive"
CARTE=$(ls /sys/class/net | grep -E '^(en|eth)' | sed -n 2p || true)
if [[ -z "$CARTE" ]]; then
    echo "    Aucune seconde carte reseau detectee, etape ignoree."
    echo "    Verifiez que la VM a bien 2 cartes (NAT + reseau prive hote)."
else
    if ! grep -q "$CARTE" /etc/network/interfaces; then
        cat >> /etc/network/interfaces <<EOF

# Reseau prive entre les VM du projet carrefour
auto $CARTE
iface $CARTE inet static
    address $IP_LOCALE
    netmask 255.255.255.0
EOF
        echo "    Carte $CARTE fixee a $IP_LOCALE"
    else
        echo "    Carte $CARTE deja configuree"
    fi
    ifup "$CARTE" 2>/dev/null || systemctl restart networking || true
fi

# --- 3. Base de donnees locale ---------------------------------------
echo "--> Creation de la base $BASE"
mariadb < "$PROJET/database/$SCHEMA"
mariadb -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_MDP';
            GRANT ALL PRIVILEGES ON $BASE.* TO '$DB_USER'@'localhost';
            FLUSH PRIVILEGES;"
echo "    Base prete, utilisateur $DB_USER cree"

# --- 4. Environnement Python -----------------------------------------
# Les serveurs n'ont pas besoin de PyQt6 : seul le poste client en a
# l'usage. On installe donc uniquement le connecteur MariaDB, ce qui
# evite de tirer tout Qt sur une VM sans interface graphique.
echo "--> Environnement Python"
VENV="$PROJET/venv"
if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet mysql-connector-python
chown -R "${SUDO_USER:-root}:${SUDO_USER:-root}" "$VENV"

# --- 5. Variables d'environnement ------------------------------------
echo "--> Fichier d'environnement"
ENVFILE="/etc/carrefour.env"
if [[ "$ROLE" == "moteur" ]]; then
    cat > "$ENVFILE" <<EOF
CARREFOUR_DB_MOTEUR_USER=$DB_USER
CARREFOUR_DB_MOTEUR_PASSWORD=$DB_MDP
CARREFOUR_DB_MOTEUR_NAME=$BASE
CARREFOUR_MOTEUR_ECOUTE=0.0.0.0
CARREFOUR_MOTEUR_PORT=5051
EOF
else
    cat > "$ENVFILE" <<EOF
CARREFOUR_DB_PASSERELLE_USER=$DB_USER
CARREFOUR_DB_PASSERELLE_PASSWORD=$DB_MDP
CARREFOUR_DB_PASSERELLE_NAME=$BASE
CARREFOUR_MOTEUR_HOTE=${IP_MOTEUR:-192.168.56.10}
CARREFOUR_MOTEUR_PORT=5051
CARREFOUR_SOCKET_ECOUTE=0.0.0.0
CARREFOUR_SOCKET_PORT=5050
EOF
fi
# Le fichier contient le mot de passe de la base : lisible par son seul
# proprietaire. On le donne a l'utilisateur du projet, sinon lui seul ne
# pourrait pas le lire et devrait lancer les services en root.
chown "${SUDO_USER:-root}:${SUDO_USER:-root}" "$ENVFILE"
chmod 600 "$ENVFILE"

# --- 6. Pare-feu -----------------------------------------------------
# Seul le port reellement utilise par le role est ouvert : la VM1
# n'expose que la liaison interne, la VM2 que la facade client.
if command -v ufw >/dev/null 2>&1; then
    echo "--> Pare-feu"
    if [[ "$ROLE" == "moteur" ]]; then
        ufw allow 5051/tcp >/dev/null
    else
        ufw allow 5050/tcp >/dev/null
    fi
    ufw allow 22/tcp >/dev/null
fi

echo
echo "=========================================================="
echo " VM '$ROLE' prete."
echo
if [[ "$ROLE" == "moteur" ]]; then
    echo " Lancer le moteur :"
    echo "   set -a && . /etc/carrefour.env && set +a"
    echo "   $VENV/bin/python serveur/main_moteur.py"
else
    echo " Lancer la passerelle :"
    echo "   set -a && . /etc/carrefour.env && set +a"
    echo "   $VENV/bin/python serveur/main_passerelle.py"
fi
echo "=========================================================="
