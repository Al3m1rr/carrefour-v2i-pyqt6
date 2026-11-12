# Guide de déploiement pas à pas — objectif 30 minutes

Ce guide part de **VirtualBox déjà installé** et va jusqu'à la
simulation du carrefour affichée à l'écran. Il ne suppose aucune
connaissance de Linux.

**Vous avez déjà deux VM Debian 13 prêtes ?** Sautez à
l'[étape 3](#étape-3--relier-les-deux-vm-5-min).

**Vous voulez juste voir le projet tourner, sans VM ?** Version en
5 minutes dans le [README principal](../README.md).

---

## Le chronométrage

| Étape | Durée | Peut se faire en parallèle |
|---|---|---|
| 1. Télécharger l'ISO Debian | 2–5 min | pendant la lecture du guide |
| 2. Créer et installer les deux VM | **15–20 min** | ✅ **les deux en même temps** |
| 3. Relier les deux VM | 5 min | |
| 4. Déployer le projet | 5 min | ✅ les deux en même temps |
| 5. Lancer et vérifier | 3 min | |
| | **≈ 30 min** | |

> **La clé pour tenir les 30 minutes** : lancez l'installation des
> **deux VM simultanément** (étape 2.4). Les faire l'une après l'autre
> double le temps total. Pendant qu'elles installent, vous n'avez rien
> à faire.

**Prérequis** : VirtualBox 7.x installé, 6 Go de RAM libres, 50 Go de
disque, une connexion Internet.

### Trois règles qui évitent l'essentiel des pertes de temps

1. **Tout se fait sur les DEUX VM.** Chaque commande de ce guide, sauf
   mention contraire, est à répéter sur l'autre machine. L'erreur la
   plus fréquente est de corriger un problème sur une seule VM et de
   chercher ensuite pourquoi ça ne marche toujours pas.
2. **Ne sautez aucun point de contrôle** (encadrés ✅). Ils prennent
   dix secondes et évitent de découvrir une erreur trois étapes plus
   loin, quand la cause n'est plus évidente.
3. **Travaillez en SSH depuis votre PC**, pas dans la fenêtre
   VirtualBox : vous gardez votre clavier et vous pouvez copier-coller
   les commandes. La marche à suivre est à l'[étape 3bis](#étape-3bis--se-connecter-en-ssh-depuis-son-pc-recommandé).

---

## Étape 1 — Télécharger Debian 13 (2–5 min)

Un seul fichier suffit pour les deux VM.

👉 **https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/**

Prenez le fichier `debian-13.x.x-amd64-netinst.iso` (environ 750 Mo).
Les chiffres après le 13 changent avec les mises à jour : prenez celui
qui est proposé.

Lancez le téléchargement maintenant et poursuivez votre lecture pendant
ce temps.

---

## Étape 2 — Créer et installer les deux VM (15–20 min)

### 2.1 Créer la première VM

Dans VirtualBox, cliquez sur **Nouvelle**.

| Champ | Valeur |
|---|---|
| Nom | `VM1-Simulation` |
| Image ISO | le fichier `.iso` téléchargé |
| Mémoire vive | `2048` Mo |
| Processeurs | `2` |
| Disque dur | `20` Go, alloué dynamiquement |

### ⚠ L'écran « Installation automatique » — à désactiver

Dès que vous sélectionnez l'ISO, VirtualBox déplie une section
**« Set up unattended guest OS installation »** (ou « Installation
automatique du système invité »), avec des champs *User Name*,
*Password*, *Host Name*…

**Cochez la case « Skip Unattended Installation »** (« Ignorer
l'installation automatique »), juste sous le champ de l'image ISO.
Toute la section se grise. C'est ce que l'on veut.

**Pourquoi ne pas s'en servir ?** Nous l'avons testée sur deux VM :

- elle définit un **mot de passe root**, ce qui empêche Debian
  d'installer `sudo` et d'y ajouter votre utilisateur ;
- sa commande post-installation **ne s'exécute pas** sur Debian 13 :
  ni `sudo`, ni `git` ne sont installés malgré ce qui est demandé.

Résultat : une VM sans `sudo` ni `git`, avec une étape de rattrapage à
faire en root. L'installation manuelle, décrite en 2.5, prend le même
temps et donne une machine propre.

> **Si vous tenez à l'utiliser quand même**, voici les valeurs
> attendues. Le champ *Host Name* s'affiche en **rouge** tant qu'il ne
> contient pas de point : VirtualBox exige un nom pleinement qualifié.
>
> | Champ | Valeur |
> |---|---|
> | User Name | `carrefour` |
> | Password / Confirm | un mot de passe, à noter |
> | Host Name | `vm1.carrefour.lan` — **le point est obligatoire** |
> | Domain Name | laissez la valeur par défaut |
> | Install Guest Additions | décoché |
>
> Il faudra ensuite faire l'étape de rattrapage décrite en 4.1
> (`su -` puis installation de `sudo` et `git`).

Cliquez sur **Terminer**.

### 2.2 Lui ajouter la carte réseau privée, tout de suite

Autant le faire maintenant plutôt que d'y revenir. VM éteinte :
**Configuration** → **Réseau** :

- **Adaptateur 1** : laissez **NAT** (accès Internet)
- **Adaptateur 2** : cochez **Activer la carte réseau**, puis
  *Attaché à* → **Réseau privé hôte**

**OK**.

### 2.3 Créer la seconde VM

Refaites 2.1 et 2.2 à l'identique, en nommant la VM
`VM2-Passerelle`. Pour l'adaptateur 2, choisissez **le même nom de
réseau** que pour la VM1 — c'est ce qui leur permettra de se parler.

### 2.4 Lancer les deux installations **en même temps**

Démarrez la VM1, puis **sans attendre**, démarrez la VM2. Les deux
installateurs tournent en parallèle. C'est ce qui permet de tenir dans
les 30 minutes.

> **Souris bloquée dans une VM ?** Touche **Ctrl de droite** pour la
> libérer. Pour passer d'une VM à l'autre, utilisez la barre des tâches.

### 2.5 Dérouler l'installateur, sur chaque VM

| Écran | Choix |
|---|---|
| Menu de démarrage | **Install** (texte, le plus rapide) |
| Language | **French** |
| Pays | **France** |
| Clavier | **Français** |
| **Interface réseau principale** | **`enp0s3`** — voir l'encadré ci-dessous ⚠ |
| Nom de machine | `vm1` — et `vm2` sur l'autre VM |
| Domaine | laissez vide |
| **Mot de passe root** | **LAISSEZ VIDE** puis Continuer ⚠ |
| Nom complet | `Carrefour` |
| Identifiant | `carrefour` |
| Mot de passe | le même sur les deux, **notez-le** |
| Fuseau horaire | votre région |
| Partitionnement | **Assisté – utiliser un disque entier** |
| Disque | le seul proposé |
| Schéma | **Tout dans une seule partition** |
| Confirmer | **Terminer le partitionnement** puis **Oui** |
| Analyser un autre support | **Non** |
| Miroir | **France** puis `deb.debian.org` |
| Proxy | laissez vide |
| Participer à l'étude | **Non** |

**⚠ Écran « Configurer le réseau » — choisir la bonne interface**

Comme vos VM ont deux cartes réseau, l'installateur demande laquelle
utiliser pendant l'installation :

```
Interface réseau principale :
    enp0s3: Intel Corporation 82540EM Gigabit Ethernet Controller
    enp0s8: Intel Corporation 82540EM Gigabit Ethernet Controller
```

**Choisissez `enp0s3`**, la première, déjà surlignée — il suffit
d'appuyer sur Entrée.

`enp0s3` est l'Adaptateur 1, le **NAT**, celui qui donne accès à
Internet : l'installateur en a besoin pour télécharger les paquets.
`enp0s8` est l'Adaptateur 2, le réseau privé entre les VM, sans accès
Internet — le choisir ferait échouer l'installation.

**⚠ Écran « Sélection des logiciels » — le plus important**

Avec la **barre d'espace** :

- ❌ **décochez** `Environnement de bureau Debian` et `GNOME`
- ✅ **cochez** `Serveur SSH`
- ✅ laissez `Utilitaires usuels du système`

Sans interface graphique, l'installation est deux fois plus rapide et
la VM consomme bien moins de mémoire.

| Écran | Choix |
|---|---|
| Installer GRUB | **Oui** |
| Où l'installer | le disque proposé (`/dev/sda`) |
| Fin | **Continuer**, la VM redémarre |

### Pourquoi laisser le mot de passe root vide ?

C'est le conseil qui évite le plus de problèmes. Mot de passe root vide
= Debian installe `sudo` et y ajoute votre utilisateur automatiquement.
Si vous en définissez un, **`sudo` n'est pas installé du tout** et il
faudra le rattraper à la main.

---

## Étape 3 — Vérifier les cartes réseau (2 min)

Connectez-vous sur chaque VM (identifiant `carrefour`) et tapez :

```bash
ip -brief addr
```

Vous devez voir **deux** cartes en plus de `lo`, et c'est normal que la
seconde soit `DOWN` :

```
enp0s3   UP     10.0.2.15/24      <- NAT, Internet : doit être UP
enp0s8   DOWN                     <- réseau privé : DOWN, c'est attendu
```

> **`enp0s8` est `DOWN` et sans adresse : c'est le comportement normal.**
> L'installateur Debian ne configure que l'interface principale, celle
> choisie pendant l'installation. La seconde est reconnue mais laissée
> éteinte.
>
> Elle sera activée et adressée automatiquement à l'étape 4.2, par le
> script de provisionnement. Vous n'avez **rien à faire maintenant**.

**Choisissez simplement les adresses** que porteront vos deux VM sur le
réseau privé. Sauf raison particulière, gardez celles-ci :

| VM | Adresse privée |
|---|---|
| VM1 (moteur) | `192.168.56.10` |
| VM2 (passerelle) | `192.168.56.11` |

Notez-les, vous les passerez au script à l'étape 4.2.

> **✅ Point de contrôle 1** — sur **chaque** VM :
> - `enp0s3` est `UP` avec une adresse en `10.0.2.x` → Internet d'accord
> - `enp0s8` apparaît, même `DOWN` → la carte privée existe
>
> Si l'un des deux manque, corrigez maintenant : la suite n'a aucune
> chance de fonctionner.

### VM déjà fournies avec un bureau (cas des postes de l'IUT)

Des VM Debian préparées avec un environnement graphique utilisent
**NetworkManager**, et leurs cartes réseau sont souvent mal déclarées.
Deux symptômes à connaître, tous deux constatés sur des VM de l'IUT :

- `enp0s3` est « déconnecté » : pas d'adresse, pas de route, donc ni
  `apt` ni `git clone` (`ping: Le réseau n'est pas accessible`) ;
- `enp0s8` est `UP` mais n'a aucune adresse : les deux VM ne se voient
  pas (`Destination Host Unreachable`).

> **Piège** : ces VM n'ont qu'un seul profil, `Wired connection 1`, qui
> n'est lié à aucune carte. Chaque `nmcli device connect` le **déplace**
> sur la carte demandée, et l'autre carte perd son adresse. Réparer une
> carte en casse alors une autre, d'où l'impression de tourner en rond.

**La correction : un profil par carte.** Sur **chaque** VM :

```bash
sudo nmcli connection add type ethernet ifname enp0s3 con-name nat ipv4.method auto
```
```bash
sudo nmcli connection add type ethernet ifname enp0s8 con-name prive ipv4.method auto ipv4.never-default yes
```
```bash
sudo nmcli connection modify "Wired connection 1" connection.autoconnect no
```
```bash
sudo nmcli connection up nat
```
```bash
sudo nmcli connection up prive
```
```bash
ip -brief addr
```

Attendu : `enp0s3` en `10.0.2.x` **et** `enp0s8` en `192.168.56.x`, sur
les deux VM en même temps. Si la troisième commande répond que le
profil n'existe pas, ignorez-la. Le DHCP du réseau privé choisit les
adresses : **utilisez celles que vous lisez**, pas celles de ce guide.

> **Si `sudo` répond « n'est pas dans le fichier sudoers »**, passez
> root avec `su -`, puis `usermod -aG sudo <votre-utilisateur>`, puis
> ouvrez une nouvelle session avec `su - <votre-utilisateur>`.

Ne communiquez jamais l'adresse `10.0.2.x` à l'autre VM : c'est celle
du NAT, identique sur toutes les VM et injoignable depuis l'extérieur.
L'adresse à donner (`IP_MOTEUR`) est celle de `enp0s8`.

### Si `enp0s8` n'apparaît pas du tout

Là, en revanche, il y a un problème : l'Adaptateur 2 n'a pas été
ajouté. Éteignez la VM et reprenez l'étape 2.2. Vérifiez aussi que les
deux VM utilisent **le même nom de réseau** dans l'Adaptateur 2, sinon
elles ne pourront pas se joindre.

### Si `enp0s3` est `DOWN`

Pas d'accès Internet : `apt` et `git clone` échoueront à l'étape 4.
Vérifiez que l'Adaptateur 1 est bien en **NAT** dans la configuration
de la VM.

---

## Étape 3bis — Se connecter en SSH depuis son PC (recommandé)

Travailler dans la fenêtre VirtualBox est pénible : clavier parfois en
QWERTY, pas de copier-coller, et une seule console à la fois. Cinq
minutes d'installation vous en feront gagner beaucoup plus.

Sur votre PC, **une fois par VM**, créez une redirection de port :

```bash
VBoxManage controlvm "VM1-Simulation" natpf1 "ssh,tcp,127.0.0.1,2401,,22"
```
```bash
VBoxManage controlvm "VM2-Passerelle" natpf1 "ssh,tcp,127.0.0.1,2402,,22"
```

> Sous Windows, si `VBoxManage` n'est pas reconnu, utilisez son chemin
> complet : `& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" ...`
> Si la VM est éteinte, remplacez `controlvm` par `modifyvm`.

Ouvrez ensuite **deux terminaux** sur votre PC :

```bash
ssh -p 2401 carrefour@127.0.0.1
```
```bash
ssh -p 2402 carrefour@127.0.0.1
```

Gardez ces deux terminaux ouverts : un par VM, pour toute la suite.

> Une fois le réseau privé opérationnel (étape 4.3), vous pourrez aussi
> vous connecter directement par l'adresse privée, sans redirection :
> `ssh carrefour@192.168.56.10`

## Étape 4 — Déployer le projet (5 min)

À faire **sur les deux VM**, elles peuvent travailler en parallèle.

### 4.1 Récupérer le projet

```bash
sudo apt update && sudo apt install -y git
```
```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
```
```bash
cd carrefour-v2i-pyqt6
```

> **`sudo : commande introuvable` ?** Vous aviez défini un mot de passe
> root. Tapez `su -`, puis
> `apt update && apt install -y sudo git`, puis
> `usermod -aG sudo carrefour`, puis `exit`. Déconnectez-vous et
> reconnectez-vous.

### 4.2 Provisionner

Installe MariaDB, crée la base du rôle et prépare Python. 3 à 5 minutes.

C'est ici que `enp0s8` est activée et reçoit son adresse, grâce au
paramètre `IP_LOCALE`.

Sur la **VM1** :

```bash
sudo IP_LOCALE=192.168.56.10 bash deploiement/installer_vm.sh moteur
```

Sur la **VM2**, qui reçoit en plus l'adresse de la VM1 :

```bash
sudo IP_LOCALE=192.168.56.11 IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
```

> Si vos VM avaient déjà une adresse sur le réseau privé — cas d'un
> DHCP actif, ou de VM fournies déjà configurées — omettez `IP_LOCALE`
> et le script ne touchera pas à votre réseau.

Dans la sortie du script, cherchez cette ligne, qui confirme que la
carte privée a bien pris son adresse :

```
OK : enp0s8 porte 192.168.56.10
```

Si vous lisez `ECHEC` à la place, la VM n'a pas de seconde carte
réseau : reprenez l'étape 2.2.

### 4.3 Vérifier que les deux VM se voient

**N'allez pas plus loin tant que cette étape n'est pas verte.** C'est
le point de bascule : tant que les VM ne se voient pas, rien d'autre ne
peut fonctionner.

Sur **chaque** VM, vérifiez d'abord que chaque carte porte **une seule**
adresse, la bonne :

```bash
ip -brief addr
```

Attendu sur la VM1 :

```
enp0s3   UP   10.0.2.15/24          <- Internet, PAS d'adresse 192.168.56.x
enp0s8   UP   192.168.56.10/24      <- réseau privé
```

> ⚠ **Si `192.168.56.x` apparaît sur `enp0s3`**, la machine a deux
> routes concurrentes vers le même réseau et devient invisible pour
> l'autre VM, tout en paraissant correctement configurée. Relancez le
> script de l'étape 4.2 : il détecte et répare ce cas, en affichant
> `Nettoyage : ... retiree de enp0s3`.

Puis, depuis la **VM2** :

```bash
ping -c 3 192.168.56.10
```

> **✅ Point de contrôle 2** — le ping répond. Vous pouvez lancer.
>
> `Destination Host Unreachable` signifie que l'autre VM ne répond pas
> à l'appel réseau. Dans 9 cas sur 10, c'est que **vous n'avez fait
> l'étape 4.2 que sur une seule des deux VM**. Vérifiez l'autre.

En cas de doute, ce script fait le tour sans rien modifier :

```bash
./deploiement/verifier.sh 192.168.56.10
```

---

## Étape 5 — Lancer et vérifier (3 min)

L'ordre compte : VM1, puis VM2, puis l'interface.

### 5.1 VM1 — le moteur

```bash
cd carrefour-v2i-pyqt6 && ./deploiement/demarrer.sh moteur
```

Attendu :

```
[DB:moteur] Connexion a carrefour_moteur_db@127.0.0.1 reussie.
[Lien VM2] En ecoute sur 0.0.0.0:5051
Simulation demarree (30 ticks/s).
```

**Laissez la fenêtre ouverte** : le moteur occupe ce terminal. Pour
taper autre chose sur cette VM, ouvrez un second écran avec
**Alt + F2**.

### 5.2 VM2 — la passerelle

```bash
cd carrefour-v2i-pyqt6 && ./deploiement/demarrer.sh passerelle
```

La ligne qui prouve que les deux VM communiquent :

```
[Lien moteur] Connecte au moteur 192.168.56.10:5051
```

> **✅ Point de contrôle 3** — vous voyez bien `Connecte au moteur`.
>
> Si à la place la VM2 répète
> `VM1 injoignable ([Errno 113] No route to host)` toutes les 3
> secondes, le réseau privé n'est pas opérationnel : revenez à
> l'étape 4.3. Inutile de lancer le client, il ne verra rien.
>
> Bonne nouvelle : la passerelle réessaie en continu. Dès que vous
> réparez le réseau, elle se connecte **toute seule**, sans rien
> relancer.

### 5.3 Votre PC — l'interface graphique

L'interface ne tourne pas dans les VM, qui n'ont pas d'écran, mais sur
votre PC. Dans un terminal **de votre PC** :

```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
```
```bash
cd carrefour-v2i-pyqt6
```
```bash
python -m venv venv
```

Activez l'environnement — Windows :

```bash
venv\Scripts\activate
```

Linux ou macOS :

```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

Puis, avec l'adresse de votre VM2 — Windows :

```bash
set CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.56.11
```
```bash
python client\main_client.py
```

Linux ou macOS :

```bash
export CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.56.11
```
```bash
python3 client/main_client.py
```

**La fenêtre du carrefour s'ouvre**, avec en haut à droite :

```
🟢 Connecté au serveur 192.168.56.11:5050
```

### 5.4 Vérifier le mécanisme central

Dans l'interface, cliquez sur le **+** de la ligne **Urgences**.
Observez :

- l'axe du véhicule d'urgence passe en **rouge** : la voie réservée
- deux panneaux **SAUF URGENCES** s'allument à ses entrées
- un **compte à rebours** annonce son arrivée
- les véhicules ordinaires sont déviés, la voie se vide devant elle

### 5.5 Vérifier les bases de données

Sur la **VM1**, le résultat principal du projet :

```bash
sudo mariadb carrefour_moteur_db -e "SELECT type_usager, COUNT(*) AS nb, ROUND(AVG(temps_parcours),2) AS temps_moyen_s FROM usager WHERE temps_parcours IS NOT NULL GROUP BY type_usager ORDER BY temps_moyen_s;"
```

Les véhicules d'urgence doivent apparaître en tête, avec un temps de
traversée nettement inférieur aux véhicules ordinaires.

Sur la **VM2** :

```bash
sudo mariadb carrefour_stats_db -e "SELECT * FROM session_simulation;"
```

Et pour constater que les données sont bien **réparties** et non
centralisées, sur chaque VM :

```bash
sudo mariadb -e "SHOW DATABASES;"
```

La VM1 a `carrefour_moteur_db` mais pas `carrefour_stats_db`, et
inversement.

---

## Tout arrêter proprement

1. Fermez la fenêtre de l'interface sur votre PC.
2. **VM2** : **Ctrl + C**. Vous devez voir
   `[DB:passerelle] Bilan de session enregistre.`
   C'est cette étape qui écrit le bilan en base, ne la sautez pas.

   > Si vous lisez plutôt `Aucun bilan a enregistrer : aucun etat recu
   > du moteur pendant cette session`, c'est que la passerelle n'a
   > jamais réussi à joindre la VM1 : il n'y avait rien à enregistrer.
   > La ligne restera à `NULL` en base, c'est normal.
3. **VM1** : **Ctrl + C**.
4. Sur chaque VM : `sudo poweroff`

Pour relancer plus tard, reprenez directement à l'**étape 5**.

---

## En cas de problème

### Les trois commandes qui disent presque tout

Lancez-les **sur chaque VM** avant de chercher plus loin :

```bash
ip -brief addr
```
```bash
ip route
```
```bash
./deploiement/verifier.sh 192.168.56.10
```

La première révèle les adresses mal placées, la deuxième les routes en
double, la troisième tout le reste.

| Ce que vous voyez | Cause et solution |
|---|---|
| `Destination Host Unreachable` au ping | **Le plus fréquent** : l'étape 4.2 n'a été faite que sur une seule VM. Faites-la sur l'autre |
| `192.168.56.x` présent sur `enp0s3` | Adresse privée posée sur la carte Internet : deux routes concurrentes, la VM devient invisible. Relancez l'étape 4.2, le script répare |
| `ip route` montre deux lignes `192.168.56.0/24` | Même cause que ci-dessus |
| L'interface affiche « Mode dégradé » | La passerelle n'est pas lancée sur la VM2, ou mauvaise adresse dans `CARREFOUR_SOCKET_SERVEUR_HOTE` |
| La VM2 répète « VM1 injoignable » | Le moteur n'est pas lancé, ou `IP_MOTEUR` est fausse. Relancez l'étape 4.2 |
| Le `ping` entre les VM ne passe pas | Carte réseau privée absente ou différente entre les deux. Reprenez l'étape 3 |
| `sudo : commande introuvable` | Mot de passe root défini à l'installation. Voir l'encadré en 4.1 |
| `pip install` échoue | Python trop ancien, il faut **3.11+** : `python3 --version` |
| Ce que je tape ne fait rien | Un service occupe le terminal. Second écran avec **Alt + F2** |
| `Host Name` en rouge à la création de la VM | VirtualBox exige un point : `vm1.carrefour.lan`. Mieux : cochez **Skip Unattended Installation** (voir 2.1) |
| VM installée mais `sudo` et `git` absents | L'installation automatique de VirtualBox a été utilisée. Rattrapage en 4.1 |
| `demarrer.sh: command not found` | Mauvais dossier : `cd carrefour-v2i-pyqt6` |
| La souris reste bloquée | Touche **Ctrl de droite** |
| « base désactivée » au démarrage | MariaDB absent ou arrêté. La simulation tourne, mais n'enregistre rien |

Sur chaque VM, ce script diagnostique sans rien modifier :

```bash
./deploiement/verifier.sh 192.168.56.10
```
