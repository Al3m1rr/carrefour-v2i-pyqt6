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
| Installation automatique | **à décocher** si la case apparaît |
| Mémoire vive | `2048` Mo |
| Processeurs | `2` |
| Disque dur | `20` Go, alloué dynamiquement |

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

## Étape 3 — Relier les deux VM (5 min)

Sans cette étape, les deux VM ne peuvent pas se parler et le projet ne
fonctionne pas. C'est la cause d'échec la plus fréquente.

Connectez-vous sur chaque VM (identifiant `carrefour`), puis :

```bash
ip -brief addr
```

Vous devez voir **deux** cartes en plus de `lo` :

```
enp0s3   UP   10.0.2.15/24         <- NAT, Internet
enp0s8   UP   192.168.56.10/24     <- réseau privé, entre les VM
```

**Notez l'adresse `192.168.56.x` de chaque VM.**

Vérifiez qu'elles se voient — depuis la **VM2**, avec l'adresse de
votre VM1 :

```bash
ping -c 3 192.168.56.10
```

Des réponses = tout va bien, passez à l'étape 4.

### Si `enp0s8` est absente, `DOWN` ou sans adresse

**Absente** : l'adaptateur 2 n'a pas été ajouté. Éteignez la VM et
reprenez l'étape 2.2.

**Présente mais sans adresse** : le serveur DHCP du réseau privé est
inactif. Soit vous l'activez une fois pour toutes dans VirtualBox
(**Fichier** → **Outils** → **Gestionnaire de réseau hôte** →
onglet **Serveur DHCP** → **Activer**, puis redémarrez les VM), soit
vous fixez les adresses à l'étape 4 avec `IP_LOCALE`.

**Le ping ne passe pas** : les deux VM ne sont pas sur le même réseau
privé. Vérifiez qu'elles ont bien le **même nom de réseau** dans
l'adaptateur 2.

---

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

Sur la **VM1** :

```bash
sudo bash deploiement/installer_vm.sh moteur
```

Sur la **VM2**, avec l'adresse privée de la VM1 :

```bash
sudo IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
```

> Si vos cartes privées n'avaient pas d'adresse automatique, ajoutez
> `IP_LOCALE` :
> ```bash
> sudo IP_LOCALE=192.168.56.10 bash deploiement/installer_vm.sh moteur
> sudo IP_LOCALE=192.168.56.11 IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
> ```

En cas de doute, un script vérifie l'état de la machine sans rien
modifier :

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
3. **VM1** : **Ctrl + C**.
4. Sur chaque VM : `sudo poweroff`

Pour relancer plus tard, reprenez directement à l'**étape 5**.

---

## En cas de problème

| Ce que vous voyez | Cause et solution |
|---|---|
| L'interface affiche « Mode dégradé » | La passerelle n'est pas lancée sur la VM2, ou mauvaise adresse dans `CARREFOUR_SOCKET_SERVEUR_HOTE` |
| La VM2 répète « VM1 injoignable » | Le moteur n'est pas lancé, ou `IP_MOTEUR` est fausse. Relancez l'étape 4.2 |
| Le `ping` entre les VM ne passe pas | Carte réseau privée absente ou différente entre les deux. Reprenez l'étape 3 |
| `sudo : commande introuvable` | Mot de passe root défini à l'installation. Voir l'encadré en 4.1 |
| `pip install` échoue | Python trop ancien, il faut **3.11+** : `python3 --version` |
| Ce que je tape ne fait rien | Un service occupe le terminal. Second écran avec **Alt + F2** |
| `demarrer.sh: command not found` | Mauvais dossier : `cd carrefour-v2i-pyqt6` |
| La souris reste bloquée | Touche **Ctrl de droite** |
| « base désactivée » au démarrage | MariaDB absent ou arrêté. La simulation tourne, mais n'enregistre rien |

Sur chaque VM, ce script diagnostique sans rien modifier :

```bash
./deploiement/verifier.sh 192.168.56.10
```
