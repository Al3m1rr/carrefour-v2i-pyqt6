#!/bin/bash
# Deploiement du projet "Carrefour intelligent connecte" sur Proxmox.
#
#   UNE SEULE COMMANDE, a lancer en root sur le serveur Proxmox :
#
#       bash proxmox.sh
#
# Le script cree deux conteneurs LXC Debian 13 (moteur et passerelle),
# y installe le projet, cree les deux bases MariaDB, demarre les deux
# services, puis affiche la commande a taper sur le PC pour lancer
# l'interface.
#
# Il n'y a aucun reseau a configurer : Proxmox adresse les conteneurs en
# DHCP sur le pont, et le script lit les adresses obtenues pour relier
# les deux machines entre elles.
#
# Reglages possibles, en prefixant la commande :
#     CTID_MOTEUR=310 CTID_PASSERELLE=311 bash proxmox.sh
#     STOCKAGE=local-lvm PONT=vmbr0 bash proxmox.sh
#     DEPOT=https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git bash proxmox.sh
#
# Relancer avec --recreer detruit les conteneurs existants et repart de zero.

set -euo pipefail

DEPOT="${DEPOT:-https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git}"
STOCKAGE="${STOCKAGE:-local-lvm}"
STOCKAGE_MODELE="${STOCKAGE_MODELE:-local}"
PONT="${PONT:-vmbr0}"
MEMOIRE="${MEMOIRE:-1024}"
DISQUE="${DISQUE:-4}"
CHEMIN="/opt/carrefour"
RECREER="non"
[[ "${1:-}" == "--recreer" ]] && RECREER="oui"

titre() { echo; echo "=== $* ==="; }
echec() { echo "ECHEC : $*" >&2; exit 1; }

# Execute une commande DANS un conteneur.
dans() { pct exec "$1" -- bash -lc "$2"; }

# --- 1. Verifications ------------------------------------------------
titre "Verifications"
command -v pct >/dev/null 2>&1 \
    || echec "la commande 'pct' est introuvable : ce script se lance sur le SERVEUR Proxmox, pas dans une VM."
[[ $EUID -eq 0 ]] || echec "lancez ce script en root (ou avec sudo)."

if ! pvesm status 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$STOCKAGE"; then
    DISPOS=$(pvesm status 2>/dev/null | awk 'NR>1{print $1}' | tr '\n' ' ')
    echec "stockage '$STOCKAGE' inconnu. Disponibles : $DISPOS
          Relancez avec : STOCKAGE=<nom> bash $0"
fi
echo "  Proxmox detecte, stockage '$STOCKAGE', pont '$PONT'."

# --- 2. Modele Debian 13 ---------------------------------------------
# Le modele est l'image de base du conteneur. On reutilise celui qui est
# deja telecharge ; sinon on le recupere, ce qui prend une minute.
titre "Modele Debian 13"
MODELE=$(pveam list "$STOCKAGE_MODELE" 2>/dev/null | awk '{print $1}' | grep -E 'debian-13.*amd64' | head -1 || true)
if [[ -z "$MODELE" ]]; then
    echo "  Aucun modele Debian 13 en local, telechargement..."
    pveam update >/dev/null 2>&1 || true
    DISPO=$(pveam available --section system 2>/dev/null | awk '{print $2}' | grep -E '^debian-13.*amd64' | head -1 || true)
    [[ -n "$DISPO" ]] || echec "aucun modele Debian 13 disponible. Listez-les avec : pveam available --section system"
    pveam download "$STOCKAGE_MODELE" "$DISPO" >/dev/null
    MODELE=$(pveam list "$STOCKAGE_MODELE" | awk '{print $1}' | grep -E 'debian-13.*amd64' | head -1)
fi
echo "  Modele : $MODELE"

# --- 3. Identifiants des conteneurs ----------------------------------
# Sans consigne, on prend deux numeros libres : aucun risque d'ecraser
# un conteneur ou une VM deja presents sur le serveur.
titre "Conteneurs"
if [[ -z "${CTID_MOTEUR:-}" ]]; then
    CTID_MOTEUR=$(pvesh get /cluster/nextid)
    while pct status "$CTID_MOTEUR" >/dev/null 2>&1; do
        CTID_MOTEUR=$((CTID_MOTEUR + 1))
    done
    CTID_PASSERELLE=$((CTID_MOTEUR + 1))
    while pct status "$CTID_PASSERELLE" >/dev/null 2>&1; do
        CTID_PASSERELLE=$((CTID_PASSERELLE + 1))
    done
fi
CTID_PASSERELLE="${CTID_PASSERELLE:-$((CTID_MOTEUR + 1))}"
echo "  moteur = $CTID_MOTEUR, passerelle = $CTID_PASSERELLE"

creer_conteneur() {
    local id="$1" nom="$2"
    if pct status "$id" >/dev/null 2>&1; then
        if [[ "$RECREER" == "oui" ]]; then
            echo "  $nom ($id) existe : destruction demandee."
            pct stop "$id" >/dev/null 2>&1 || true
            pct destroy "$id" >/dev/null
        else
            echec "le conteneur $id existe deja.
          Relancez avec --recreer pour le remplacer, ou choisissez d'autres
          numeros : CTID_MOTEUR=<n> CTID_PASSERELLE=<n+1> bash $0"
        fi
    fi
    echo "  Creation de $nom ($id)..."
    pct create "$id" "$MODELE" \
        --hostname "$nom" \
        --cores 2 --memory "$MEMOIRE" --swap 512 \
        --rootfs "$STOCKAGE:$DISQUE" \
        --net0 "name=eth0,bridge=$PONT,ip=dhcp" \
        --features nesting=1 \
        --unprivileged 1 \
        --onboot 1 \
        --start 1 >/dev/null
}

creer_conteneur "$CTID_MOTEUR" "carrefour-moteur"
creer_conteneur "$CTID_PASSERELLE" "carrefour-passerelle"

# --- 4. Attente du reseau --------------------------------------------
# Un conteneur qui vient de demarrer n'a pas encore son bail DHCP. On
# attend l'adresse plutot que d'enchainer et d'echouer sur un apt-get.
attendre_ip() {
    local id="$1" ip=""
    for _ in $(seq 1 45); do
        ip=$(pct exec "$id" -- hostname -I 2>/dev/null | awk '{print $1}' || true)
        [[ -n "$ip" ]] && { echo "$ip"; return 0; }
        sleep 2
    done
    return 1
}

titre "Adresses reseau"
IP_MOTEUR=$(attendre_ip "$CTID_MOTEUR") \
    || echec "le conteneur moteur n'a pas obtenu d'adresse IP.
          Verifiez que le pont '$PONT' distribue bien du DHCP."
IP_PASSERELLE=$(attendre_ip "$CTID_PASSERELLE") \
    || echec "le conteneur passerelle n'a pas obtenu d'adresse IP."
echo "  moteur     : $IP_MOTEUR"
echo "  passerelle : $IP_PASSERELLE"

# --- 5. Installation du projet ---------------------------------------
installer() {
    local id="$1" role="$2" extra="${3:-}"
    echo "  [$role] paquets et recuperation du projet..."
    # iproute2 n'est pas dans le modele minimal, or l'installateur s'en
    # sert pour afficher les adresses : sans lui il s'arreterait aussitot.
    dans "$id" "export DEBIAN_FRONTEND=noninteractive
                apt-get update -qq
                apt-get install -y -qq git ca-certificates iproute2 >/dev/null
                rm -rf $CHEMIN
                git clone --depth 1 --quiet $DEPOT $CHEMIN"
    echo "  [$role] MariaDB, base de donnees et environnement Python..."
    dans "$id" "$extra bash $CHEMIN/deploiement/installer_vm.sh $role" >/dev/null
}

titre "Installation"
installer "$CTID_MOTEUR" moteur
installer "$CTID_PASSERELLE" passerelle "IP_MOTEUR=$IP_MOTEUR"

# --- 6. Services permanents ------------------------------------------
# Un service systemd plutot qu'une commande a relancer a la main : les
# deux serveurs repartent seuls au redemarrage du conteneur, et dans le
# bon ordre.
service_systemd() {
    local id="$1" role="$2" script="$3"
    local unite
    unite=$(mktemp)
    cat > "$unite" <<UNITE
[Unit]
Description=Carrefour intelligent connecte ($role)
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$CHEMIN
EnvironmentFile=/etc/carrefour.env
ExecStart=$CHEMIN/venv/bin/python -u $CHEMIN/serveur/$script
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
UNITE
    pct push "$id" "$unite" /etc/systemd/system/carrefour.service
    rm -f "$unite"
    dans "$id" "systemctl daemon-reload && systemctl enable --now carrefour.service"
}

titre "Demarrage des services"
service_systemd "$CTID_MOTEUR" moteur main_moteur.py
sleep 3
service_systemd "$CTID_PASSERELLE" passerelle main_passerelle.py
sleep 3

# --- 7. Controle -----------------------------------------------------
titre "Controle"
controle_ok="oui"
for couple in "$CTID_MOTEUR:moteur:5051" "$CTID_PASSERELLE:passerelle:5050"; do
    id="${couple%%:*}"; reste="${couple#*:}"; role="${reste%%:*}"; port="${reste##*:}"
    if dans "$id" "systemctl is-active --quiet carrefour.service"; then
        echo "  $role : service actif, port $port"
    else
        echo "  $role : SERVICE ARRETE"
        dans "$id" "journalctl -u carrefour.service -n 15 --no-pager" || true
        controle_ok="non"
    fi
done

# La passerelle doit joindre le moteur : c'est le seul lien que le
# script ne peut pas deviner, donc le seul a verifier explicitement.
if dans "$CTID_PASSERELLE" "timeout 5 bash -c 'exec 3<>/dev/tcp/$IP_MOTEUR/5051'" 2>/dev/null; then
    echo "  liaison passerelle -> moteur : OK"
else
    echo "  liaison passerelle -> moteur : INJOIGNABLE"
    controle_ok="non"
fi

# --- 8. Resume -------------------------------------------------------
echo
echo "=============================================================="
if [[ "$controle_ok" == "oui" ]]; then
    echo " Le projet tourne."
else
    echo " Deploiement termine AVEC DES ERREURS (voir ci-dessus)."
fi
echo
echo " moteur     : conteneur $CTID_MOTEUR   $IP_MOTEUR:5051"
echo " passerelle : conteneur $CTID_PASSERELLE   $IP_PASSERELLE:5050"
echo
echo " Sur le PC, pour lancer l'interface (Linux ou macOS) :"
echo
echo "   pip install -r requirements.txt"
echo "   CARREFOUR_SOCKET_SERVEUR_HOTE=$IP_PASSERELLE python client/main_client.py"
echo
echo " Sous Windows (PowerShell), la seconde ligne devient :"
echo "   \$env:CARREFOUR_SOCKET_SERVEUR_HOTE='$IP_PASSERELLE'; python client/main_client.py"
echo
echo " Journaux  : pct exec $CTID_MOTEUR -- journalctl -u carrefour -f"
echo " Arreter   : pct stop $CTID_MOTEUR && pct stop $CTID_PASSERELLE"
echo " Relancer  : pct start $CTID_MOTEUR && pct start $CTID_PASSERELLE"
echo "=============================================================="
