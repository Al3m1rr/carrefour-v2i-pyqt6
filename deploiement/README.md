# Déploiement du projet

Trois parcours, selon ce dont vous disposez.

| Vous avez… | Allez à |
|---|---|
| Juste un PC, vous voulez voir le projet tourner | [A. Sans VM, en 5 minutes](#a-sans-vm-en-5-minutes) |
| **Deux VM Debian 13 vierges** | **[B. Déployer sur vos VM](#b-déployer-sur-deux-vm-debian-13-vierges)** |
| Rien, vous voulez tout créer | [C. Créer les VM de zéro](#c-créer-les-vm-de-zéro) |

---

## A. Sans VM, en 5 minutes

Les trois rôles tournent sur une seule machine et dialoguent par
sockets, exactement comme ils le feraient à travers le réseau.

```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

- **Windows** : double-cliquez sur `LANCER_TOUT.bat`
- **Linux / macOS** : `./lancer_local.sh`

MariaDB n'est pas nécessaire : en son absence la simulation tourne sans
enregistrement et le signale au démarrage.

---

## B. Déployer sur deux VM Debian 13 vierges

C'est le déploiement réel du projet : les processus et les bases sont
répartis sur deux machines.

| VM | Rôle | Port | Base |
|---|---|---|---|
| VM1 | moteur de simulation | 5051 | `carrefour_moteur_db` |
| VM2 | passerelle réseau | 5050 | `carrefour_stats_db` |

Le client PyQt6 tourne **sur votre PC**, pas sur les VM : il se connecte
à la VM2. (Vous pouvez aussi le lancer depuis une VM, à condition
qu'elle ait un environnement graphique.)

### ⚠ Le risque principal : deux VM qui ne se voient pas

C'est, de loin, la cause d'échec la plus probable — et elle n'a rien à
voir avec le projet lui-même. Une VM créée sans précaution n'a qu'une
carte **NAT**, qui donne accès à Internet mais **isole la machine** :
deux VM en NAT ne peuvent pas se joindre, même sur le même hôte. Le
déploiement réparti est alors impossible.

**Comment le savoir en 10 secondes.** Depuis la VM2 :

```bash
ping <ip-de-la-vm1>
```

Si ça ne répond pas, il manque une carte réseau commune.

**Comment le corriger.** Pour **chacune** des deux VM, dans VirtualBox :

1. VM éteinte → **Configuration** → **Réseau**
2. Laissez l'**Adaptateur 1** en *NAT* (il sert à `apt` et `git`)
3. Onglet **Adaptateur 2** → cochez **Activer la carte réseau**
4. *Attaché à* : **Réseau privé hôte** (host-only)
5. Choisissez le **même nom de réseau pour les deux VM** — c'est le
   point qui compte
6. Démarrez, puis vérifiez avec `ip -brief addr` : une seconde adresse
   doit apparaître, en général en `192.168.56.x`

> *Réseau interne* fonctionne aussi pour relier les deux VM, mais votre
> PC ne les verra pas — or le client PyQt6 tourne sur votre PC et doit
> joindre la VM2. Préférez donc **Réseau privé hôte**.

Si la seconde carte existe mais n'a pas d'adresse (`DOWN` ou sans
`inet`), c'est qu'elle n'est pas configurée côté Debian. Deux
solutions : activer le DHCP du réseau privé hôte dans VirtualBox
(*Fichier → Outils → Gestionnaire de réseau hôte*), ou laisser nos
scripts fixer une adresse :

```bash
sudo IP_LOCALE=192.168.56.10 bash deploiement/installer_vm.sh moteur
sudo IP_LOCALE=192.168.56.11 IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
```

### Prérequis

Avant de commencer, vérifiez ces trois points sur vos VM :

1. **Les deux VM se joignent entre elles.** Depuis la VM2 :
   `ping <ip-de-la-vm1>`. Si ça ne passe pas, ajoutez-leur une carte
   réseau commune dans VirtualBox (*Réseau privé hôte* ou *Réseau
   interne*, la même pour les deux).
2. **Votre PC joint la VM2**, puisque le client s'y connectera.
   Une carte *Réseau privé hôte* le permet.
3. **Les VM ont accès à Internet** (pour `apt`) et vous avez `sudo`.

> Rien n'est codé en dur : le projet s'adapte à **vos** adresses, quel
> que soit votre plan d'adressage. Les scripts ne modifient pas votre
> configuration réseau.

**Un script vérifie tout cela pour vous.** Sur chaque VM, après avoir
récupéré le projet (étape 2) :

```bash
./deploiement/verifier.sh                   # état de cette VM
./deploiement/verifier.sh 192.168.56.10     # + teste si l'autre VM répond
```

Il ne modifie rien et liste ce qui manque. Il sert aussi **après** le
déploiement, pour diagnostiquer une panne.

> **Si vos VM n'ont pas accès à Internet**, `apt` et `git clone`
> échoueront. Récupérez alors le dépôt sur une machine connectée et
> copiez le dossier sur chaque VM (dossier partagé VirtualBox, clé USB
> ou `scp`), puis installez MariaDB et Python depuis l'ISO Debian
> (`apt-cdrom add`).

### 1. Relever les adresses

Sur **chaque** VM :

```bash
ip -brief addr
```

Notez l'adresse par laquelle les deux VM se parlent. Dans les exemples
ci-dessous, `192.168.56.10` pour la VM1 et `192.168.56.11` pour la VM2 —
**remplacez-les par les vôtres**.

### 2. Récupérer le projet, sur chaque VM

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
cd carrefour-v2i-pyqt6
```

> Si `sudo` n'existe pas (installation Debian minimale avec un mot de
> passe root défini), passez root d'abord : `su -`, puis
> `apt update && apt install -y sudo git`, puis
> `usermod -aG sudo <votre-utilisateur>`, puis reconnectez-vous.

### 3. Provisionner chaque VM

Sur la **VM1** :

```bash
sudo bash deploiement/installer_vm.sh moteur
```

Sur la **VM2**, en indiquant l'adresse de la VM1 :

```bash
sudo IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
```

Le script installe MariaDB, crée la base propre à ce rôle, prépare
l'environnement Python et écrit la configuration dans
`/etc/carrefour.env`. Il **ne touche pas** à votre réseau : il se
contente d'afficher vos adresses. Il est réexécutable sans risque.

### 4. Démarrer

Sur la **VM1**, puis sur la **VM2** :

```bash
./deploiement/demarrer.sh moteur        # sur la VM1
./deploiement/demarrer.sh passerelle    # sur la VM2
```

Sur la VM2, la ligne qui prouve que les deux machines se parlent :

```
[Lien moteur] Connecte au moteur 192.168.56.10:5051
```

### 5. Lancer l'interface, depuis votre PC

```bash
export CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.56.11   # adresse de la VM2
python3 client/main_client.py
```

Sous Windows : `set CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.56.11` puis
`python client\main_client.py`. Si votre VM2 est bien en
`192.168.56.11`, `LANCER_CLIENT_VM.bat` fait cela tout seul.

Le bandeau en haut à droite doit afficher
`Connecté au serveur 192.168.56.11:5050`.

### 6. Vérifier que tout fonctionne

```bash
# Sur la VM1 : des usagers sont enregistrés en base
sudo mariadb carrefour_moteur_db -e "SELECT COUNT(*) FROM usager;"

# Sur la VM2 : une session est ouverte
sudo mariadb carrefour_stats_db -e "SELECT * FROM session_simulation;"
```

Arrêtez les services avec `Ctrl+C`. **Sur la VM2, c'est ce qui
enregistre le bilan de la session en base** (`date_fin`, nombre
d'usagers, temps moyen des urgences).

---

## C. Créer les VM de zéro

Si vous n'avez pas encore de VM, ce script les crée et les installe
sans intervention, sous VirtualBox 7.x :

```powershell
powershell -ExecutionPolicy Bypass -File deploiement\creer_vms.ps1
```

Options utiles si des VM portent déjà ces noms, ou si les ports sont
occupés :

```powershell
... -File deploiement\creer_vms.ps1 -Prefixe MonGroupe -PortSSH1 2301 -PortSSH2 2302
```

Le script télécharge l'ISO Debian 13 si besoin, crée deux VM (1,5 Go de
RAM, 20 Go de disque, carte NAT + carte réseau privé hôte) et force
l'interface privée en `192.168.56.1/24`. Comptez 30 à 45 minutes.

Identifiants créés par le script :

| | |
|---|---|
| Identifiant | `carrefour` |
| Mot de passe | `Carrefour2026!` |

> Deux pièges de saisie : le mot de passe ne s'affiche pas pendant la
> frappe (normal sous Linux), et le clavier de la VM est en **QWERTY**,
> donc le `!` n'est pas sur la touche attendue d'un clavier AZERTY.

**Après l'installation, une étape d'amorçage est obligatoire.** Deux
raisons, l'une et l'autre vérifiées sur nos propres machines :

- VirtualBox définit un mot de passe root, ce qui empêche Debian
  d'appliquer son comportement habituel — installer `sudo` et y ajouter
  le premier utilisateur ;
- la commande post-installation de VirtualBox, censée installer les
  paquets, **ne s'exécute pas réellement** sur Debian 13. Nous l'avons
  rendue silencieuse pour que l'installation se termine sans blocage,
  mais elle n'installe rien.

Résultat : la VM démarre avec SSH, mais **sans `sudo` ni `git`**.
Faites ceci une fois sur chaque VM, depuis la console :

```bash
su -                                   # même mot de passe
apt update && apt install -y sudo git
usermod -aG sudo carrefour
exit
```

Puis reprenez au point **B.2**.

---

## Dépannage

| Symptôme | Cause probable |
|---|---|
| Client en « Mode dégradé » | la passerelle (VM2) n'est pas lancée, ou mauvaise adresse dans `CARREFOUR_SOCKET_SERVEUR_HOTE` |
| VM2 répète « VM1 injoignable » | le moteur n'est pas lancé, ou `IP_MOTEUR` est fausse — relancez l'étape B.3 avec la bonne |
| « base désactivée » au démarrage | MariaDB absent ou mot de passe erroné — sans gravité, la simulation tourne quand même |
| Les deux VM ne se pingent pas | elles n'ont qu'une carte NAT, qui les isole — voir *Le risque principal* plus haut |
| La 2ᵉ carte existe mais est `DOWN` ou sans adresse | pas de DHCP sur le réseau privé hôte — utilisez `IP_LOCALE=` |
| `sudo : commande introuvable` sur une VM fraîche | étape d'amorçage non faite — `su -` puis `apt install -y sudo git` |
| `pip install` échoue | Python trop ancien : il faut **3.11 ou plus récent** (`python3 --version`) |
| `demarrer.sh: command not found` | vous n'êtes pas dans le dossier `carrefour-v2i-pyqt6` |
| `/etc/carrefour.env: Permission non accordée` | relancez `installer_vm.sh`, qui en corrige le propriétaire |
