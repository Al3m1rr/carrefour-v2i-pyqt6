# Déploiement du projet

Deux façons de faire tourner le projet, selon ce que vous voulez vérifier.

## A. Tout sur un seul PC — pour voir le projet fonctionner (5 minutes)

C'est le chemin recommandé si vous voulez simplement tester
l'application. Les trois rôles (moteur, passerelle, client) tournent en
local et dialoguent par sockets exactement comme ils le feraient à
travers le réseau.

```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Puis :

- **Windows** : double-cliquez sur `LANCER_TOUT.bat`
- **Linux / macOS** : `./lancer_local.sh`

MariaDB n'est pas nécessaire : en son absence la simulation tourne sans
enregistrement et l'indique au démarrage.

## B. Sur deux VM Debian 13 — l'architecture réelle du projet

C'est le déploiement décrit dans le cahier des charges : les processus
et les bases sont répartis sur deux machines distinctes.

### 1. Créer les deux VM

Depuis le PC hôte, avec VirtualBox 7.x installé :

```powershell
powershell -ExecutionPolicy Bypass -File deploiement\creer_vms.ps1
```

Le script télécharge l'ISO Debian 13 si besoin, crée les deux VM
(1,5 Go de RAM, 20 Go de disque, deux cartes réseau chacune) et lance
une installation sans intervention. Comptez 20 à 40 minutes.

Chaque VM reçoit deux cartes réseau :

| Carte | Type | Rôle |
|---|---|---|
| 1 | NAT | accès Internet (apt) + redirection SSH vers l'hôte |
| 2 | Réseau privé hôte | dialogue entre les deux VM, en 192.168.56.x |

### 2. Provisionner chaque VM

Une fois l'installation terminée, connectez-vous et déployez le projet :

```bash
# VM1 — moteur de simulation
ssh -p 2201 carrefour@127.0.0.1
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
sudo bash deploiement/installer_vm.sh moteur
```

```bash
# VM2 — passerelle réseau
ssh -p 2202 carrefour@127.0.0.1
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
sudo bash deploiement/installer_vm.sh passerelle
```

Le script installe MariaDB, crée la base propre à la VM, fixe son IP sur
le réseau privé, prépare l'environnement Python et ouvre le seul port
dont ce rôle a besoin.

### 3. Démarrer

```bash
# Sur la VM1
set -a && . /etc/carrefour.env && set +a
venv/bin/python serveur/main_moteur.py
```

```bash
# Sur la VM2
set -a && . /etc/carrefour.env && set +a
venv/bin/python serveur/main_passerelle.py
```

```bash
# Sur le PC hôte — l'interface graphique
export CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.56.11
python3 client/main_client.py
```

### Personnaliser les adresses

Rien n'est codé en dur. Si votre réseau privé hôte n'est pas en
192.168.56.x, passez vos propres valeurs :

```bash
sudo IP_LOCALE=10.0.0.10 bash deploiement/installer_vm.sh moteur
sudo IP_LOCALE=10.0.0.11 IP_MOTEUR=10.0.0.10 bash deploiement/installer_vm.sh passerelle
```

La liste complète des variables d'environnement est dans le README
principal.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| Le client affiche « Mode dégradé » | la passerelle (VM2) n'est pas lancée, ou mauvaise IP dans `CARREFOUR_SOCKET_SERVEUR_HOTE` |
| La passerelle répète « VM1 injoignable » | le moteur n'est pas lancé sur la VM1, ou le port 5051 est filtré |
| « base désactivée » au démarrage | MariaDB n'est pas installé — sans gravité, la simulation tourne quand même |
| Les deux VM ne se voient pas | elles ne sont pas sur le même réseau privé hôte dans VirtualBox |
