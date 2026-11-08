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
# IP_LOCALE n'a volontairement pas de valeur par defaut : sans elle, le
# reseau de la machine est laisse intact (cas d'une VM fournie par un
# tiers, deja configuree).
if [[ "$ROLE" == "moteur" ]]; then
    BASE="carrefour_moteur_db"
    SCHEMA="schema_moteur.sql"
else
    BASE="carrefour_stats_db"
    SCHEMA="schema_passerelle.sql"
fi

DB_USER="${DB_USER:-carrefour_user}"
DB_MDP="${DB_MDP:-CarrefourDB2026!}"
PROJET="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo " Provisionnement de la VM : role $ROLE"
echo " Base    : $BASE"
echo " Projet  : $PROJET"
echo "=========================================================="

# --- 1. Paquets ------------------------------------------------------
echo "--> Installation des paquets"
apt-get update -qq
apt-get install -y -qq mariadb-server python3 python3-venv python3-pip git

# --- 2. Reseau ------------------------------------------------------
# Par defaut on NE TOUCHE PAS au reseau de la machine : sur une VM
# fournie par un tiers, il est deja configure et l'ecraser ferait plus
# de mal que de bien. On se contente de montrer les adresses, pour que
# l'operateur sache laquelle indiquer a l'autre VM.
#
# Pour fixer malgre tout une IP statique (notre propre montage), passer
# IP_LOCALE : le script detecte alors la pile reseau utilisee, car une
# Debian peut utiliser ifupdown, NetworkManager ou systemd-networkd, et
# ecrire dans le mauvais fichier serait ignore en silence.
echo "--> Reseau"
echo "    Adresses de cette machine :"
ip -brief addr show | grep -v '^lo' | sed 's/^/      /'

if [[ -n "${IP_LOCALE:-}" ]]; then
    CARTE="${CARTE:-$(ip -o -4 addr show | awk '$2!="lo"{print $2}' | tail -1)}"
    CARTE="${CARTE:-$(ls /sys/class/net | grep -E '^(en|eth)' | tail -1)}"
    echo "    IP_LOCALE demande : $IP_LOCALE sur $CARTE"

    if systemctl is-active --quiet NetworkManager; then
        nmcli con add type ethernet ifname "$CARTE" con-name carrefour-prive \
              ip4 "$IP_LOCALE/24" 2>/dev/null \
            || nmcli con mod carrefour-prive ipv4.addresses "$IP_LOCALE/24" ipv4.method manual
        nmcli con up carrefour-prive || true
        echo "    Configure via NetworkManager"
    elif [[ -d /etc/network ]]; then
        if ! grep -q "carrefour" /etc/network/interfaces 2>/dev/null; then
            cat >> /etc/network/interfaces <<EOF

# Reseau prive entre les VM du projet carrefour
auto $CARTE
iface $CARTE inet static
    address $IP_LOCALE
    netmask 255.255.255.0
EOF
        fi
        ifup "$CARTE" 2>/dev/null || systemctl restart networking || true
        echo "    Configure via ifupdown"
    else
        echo "    Pile reseau non reconnue : configurez $IP_LOCALE a la main."
    fi
else
    echo "    (reseau laisse tel quel ; passez IP_LOCALE=... pour fixer une IP)"
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
"$VENV/bin/pip" install --quiet -r "$PROJET/requirements-serveur.txt"
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

MON_IP=$(ip -o -4 addr show | awk '$2!="lo"{print $4}' | cut -d/ -f1 | tail -1)

echo
echo "=========================================================="
echo " VM '$ROLE' prete."
echo
echo " Demarrer :   ./deploiement/demarrer.sh $ROLE"
echo
if [[ "$ROLE" == "moteur" ]]; then
    echo " Cette VM ecoute sur le port 5051."
    echo " Notez son adresse : ${MON_IP:-<voir ip -brief addr>}"
    echo " C'est elle a indiquer a la VM2, via IP_MOTEUR."
else
    echo " Cette VM ecoute sur le port 5050 pour les clients."
    echo " Notez son adresse : ${MON_IP:-<voir ip -brief addr>}"
    echo " C'est elle a indiquer au client PyQt6, via"
    echo " CARREFOUR_SOCKET_SERVEUR_HOTE."
    echo
    echo " Elle joindra le moteur sur : ${IP_MOTEUR:-192.168.56.10}"
    echo " Si ce n'est pas la bonne adresse, relancez avec :"
    echo "   sudo IP_MOTEUR=<ip-de-la-vm1> bash deploiement/installer_vm.sh passerelle"
fi
echo "=========================================================="
