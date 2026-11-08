# Guide complet — de zéro à la simulation qui tourne

Ce guide ne suppose aucune connaissance préalable. Il part d'un PC nu et
va jusqu'à la simulation du carrefour affichée à l'écran, en passant par
l'installation de VirtualBox et de deux machines virtuelles Debian.

**Vous avez déjà deux VM Debian 13 prêtes ?** Sautez directement à la
[partie 6](#partie-6--configurer-le-réseau-entre-les-deux-vm).

**Vous voulez juste voir le projet tourner, sans VM ?** Une version en
5 minutes existe dans le [README principal](../README.md).

---

## Ce dont vous avez besoin

| | Minimum | Confortable |
|---|---|---|
| Mémoire vive (RAM) | 8 Go | 16 Go |
| Espace disque libre | 50 Go | 60 Go |
| Connexion Internet | oui, pour les téléchargements | |

Durée totale : **1 h à 1 h 30**, dont beaucoup d'attente pendant les
installations. Si vous avez déjà les VM, comptez 20 à 30 minutes.

---

## Partie 1 — Installer VirtualBox

VirtualBox est le logiciel qui fait tourner des machines virtuelles :
des ordinateurs simulés à l'intérieur du vôtre.

1. Rendez-vous sur **https://www.virtualbox.org/wiki/Downloads**
2. Cliquez sur **Windows hosts** (ou le système de votre PC). Un fichier
   d'environ 110 Mo se télécharge.
3. Lancez le fichier téléchargé et cliquez sur **Next** à chaque étape,
   sans rien modifier, puis **Install**.
4. Windows affichera un avertissement sur l'installation de pilotes
   réseau : acceptez, ils sont nécessaires pour que les VM communiquent.
5. À la fin, VirtualBox s'ouvre. Vous pouvez le fermer pour l'instant.

---

## Partie 2 — Télécharger Debian 13

Debian est le système d'exploitation (comme Windows, mais Linux) qui
tournera dans les machines virtuelles.

1. Rendez-vous sur **https://www.debian.org/download**
2. Téléchargez l'image **netinst** pour **amd64**. Lien direct :
   https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/
3. Prenez le fichier nommé `debian-13.x.x-amd64-netinst.iso`
   (environ 750 Mo). Les chiffres après le 13 changent avec les mises à
   jour, prenez simplement la version proposée.
4. Notez où le fichier a été enregistré, en général dans
   `C:\Users\<vous>\Downloads`.

> L'image *netinst* est volontairement légère : elle télécharge le reste
> pendant l'installation. C'est pour cela qu'une connexion Internet est
> nécessaire à l'étape suivante.

---

## Partie 3 — Créer la première machine virtuelle

1. Ouvrez **VirtualBox** et cliquez sur **Nouvelle** (icône étoile bleue).
2. Remplissez :
   - **Nom** : `VM1-Simulation`
   - **Dossier** : laissez le défaut
   - **Image ISO** : cliquez sur la flèche → *Autre* → sélectionnez le
     fichier `.iso` téléchargé à la partie 2
   - **Ne cochez pas** « Skip Unattended Installation » si la case
     apparaît : décochez-la au contraire, nous voulons faire
     l'installation nous-mêmes.

   > Selon la version de VirtualBox, une case **« Installation
   > automatique »** peut apparaître. **Désactivez-la.** Elle provoque
   > des installations incomplètes.

3. Cliquez sur **Suivant**.
4. **Matériel** :
   - **Mémoire vive** : `2048` Mo
   - **Processeurs** : `2`
5. **Disque dur** : `20` Go, laissez *Alloué dynamiquement* coché.
6. Cliquez sur **Suivant**, vérifiez le récapitulatif, puis **Terminer**.

La VM apparaît dans la liste à gauche. Elle est créée mais vide.

---

## Partie 4 — Installer Debian sur la VM1

Sélectionnez `VM1-Simulation` et cliquez sur **Démarrer**. La VM démarre
sur l'image Debian.

> **Votre souris est « capturée » par la VM ?** Appuyez sur la touche
> **Ctrl de droite** pour la libérer.

Déroulez l'installateur :

| Écran | Ce qu'il faut choisir |
|---|---|
| Menu de démarrage | **Install** (version texte, la plus rapide) |
| Language | **French** |
| Pays | **France** |
| Disposition du clavier | **Français** |
| Nom de machine | `vm1` |
| Domaine | laissez vide |
| **Mot de passe root** | **LAISSEZ VIDE**, puis Continuer ⚠ |
| Nom complet | ce que vous voulez, ex. `Carrefour` |
| Identifiant | `carrefour` |
| Mot de passe | choisissez-en un, **notez-le** |
| Fuseau horaire | votre région |
| Partitionnement | **Assisté - utiliser un disque entier** |
| Disque | le seul proposé |
| Schéma | **Tout dans une seule partition** |
| Confirmer | **Terminer le partitionnement**, puis **Oui** |
| Analyser un autre support | **Non** |
| Miroir Debian | **France**, puis `deb.debian.org` |
| Mandataire (proxy) | laissez vide |
| Participer à l'étude | **Non** |

**⚠ L'écran le plus important — « Sélection des logiciels »** :

Utilisez la **barre d'espace** pour cocher et décocher :

- ❌ **Décochez** `Environnement de bureau Debian` et `GNOME`
- ✅ **Cochez** `Serveur SSH`
- ✅ **Laissez coché** `Utilitaires usuels du système`

Puis Continuer. Sans interface graphique, l'installation est bien plus
rapide et la VM consomme beaucoup moins de mémoire.

| Écran | Choix |
|---|---|
| Installer GRUB | **Oui** |
| Où installer GRUB | le disque proposé, ex. `/dev/sda` |
| Fin de l'installation | **Continuer** — la VM redémarre |

### Pourquoi laisser le mot de passe root vide ?

C'est le point qui évite le plus de problèmes. Quand le mot de passe
root est vide, Debian installe automatiquement `sudo` et y ajoute votre
utilisateur. Si vous en définissez un, `sudo` n'est pas installé du
tout et il faudra le faire à la main plus tard.

---

## Partie 5 — Créer la seconde machine virtuelle

Refaites **exactement** les parties 3 et 4, avec deux changements :

- **Nom de la VM** : `VM2-Passerelle`
- **Nom de machine** (dans l'installateur) : `vm2`

Tout le reste est identique, y compris l'identifiant `carrefour`.

> Vous pouvez aussi faire un clic droit sur la VM1 → **Cloner**, mais
> pensez alors à changer le nom de machine à l'intérieur, sinon les deux
> VM s'appelleront `vm1` et vous les confondrez.

---

## Partie 6 — Configurer le réseau entre les deux VM

**C'est l'étape la plus importante du guide.** Sans elle, les deux VM ne
peuvent pas se parler et le projet ne peut pas fonctionner.

Par défaut, une VM n'a qu'une carte **NAT** : elle accède à Internet,
mais elle est **invisible** pour les autres VM et pour votre PC. Il faut
donc lui ajouter une seconde carte.

Pour **chacune des deux VM**, machine **éteinte** :

1. Sélectionnez la VM → **Configuration** → **Réseau**
2. Onglet **Adaptateur 1** : laissez **NAT** (c'est l'accès Internet)
3. Onglet **Adaptateur 2** :
   - cochez **Activer la carte réseau**
   - *Attaché à* : **Réseau privé hôte**
   - *Nom* : choisissez le même pour les deux VM, en général
     `VirtualBox Host-Only Ethernet Adapter`
4. **OK**

Démarrez les deux VM, connectez-vous, et sur chacune tapez :

```bash
ip -brief addr
```

Vous devez voir **deux** cartes en plus de `lo`, par exemple :

```
enp0s3   UP   10.0.2.15/24          <- NAT, Internet
enp0s8   UP   192.168.56.10/24      <- réseau privé, entre VM
```

**Notez l'adresse `192.168.56.x` de chaque VM**, vous en aurez besoin.

### Si la seconde carte est `DOWN` ou sans adresse

C'est que le serveur DHCP du réseau privé n'est pas actif. Deux options.

**Option 1 — activer le DHCP** (une seule fois, sur votre PC) :
VirtualBox → menu **Fichier** → **Outils** → **Gestionnaire de réseau
hôte** → sélectionnez l'interface → onglet **Serveur DHCP** → cochez
**Activer**. Redémarrez les VM.

**Option 2 — fixer les adresses vous-même**, à l'étape 7 : ajoutez
`IP_LOCALE=...` devant la commande de provisionnement, comme indiqué
plus bas.

### Vérifier que les VM se voient

Depuis la **VM2**, remplacez par l'adresse de votre VM1 :

```bash
ping -c 3 192.168.56.10
```

Si vous obtenez des réponses, tout est bon. Sinon, reprenez cette
partie 6 : les deux VM ne sont pas sur le même réseau privé.

---

## Partie 7 — Déployer le projet sur les VM

À faire **sur les deux VM**.

### 7.1 Installer git et récupérer le projet

```bash
sudo apt update
```
```bash
sudo apt install -y git
```
```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
```
```bash
cd carrefour-v2i-pyqt6
```

> **`sudo : commande introuvable` ?** Votre installation Debian avait un
> mot de passe root. Tapez `su -`, entrez le mot de passe root, puis :
> `apt update && apt install -y sudo git`, puis
> `usermod -aG sudo carrefour`, puis `exit`. Déconnectez-vous et
> reconnectez-vous pour que ce soit pris en compte.

### 7.2 Vérifier que tout est prêt

```bash
./deploiement/verifier.sh
```

Ce script ne modifie rien. Il signale ce qui manque. Corrigez les lignes
`[ A VOIR ]` avant de continuer.

### 7.3 Provisionner chaque VM

Cette étape installe MariaDB, crée la base propre à chaque rôle et
prépare l'environnement Python. Comptez 3 à 5 minutes par VM.

Sur la **VM1** :

```bash
sudo bash deploiement/installer_vm.sh moteur
```

Sur la **VM2**, en indiquant l'adresse privée de la VM1 :

```bash
sudo IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
```

> Si vos cartes privées n'avaient pas d'adresse (cas de l'option 2 en
> partie 6), ajoutez `IP_LOCALE` :
> ```bash
> sudo IP_LOCALE=192.168.56.10 bash deploiement/installer_vm.sh moteur
> sudo IP_LOCALE=192.168.56.11 IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
> ```

---

## Partie 8 — Lancer la simulation

L'ordre compte : la VM1 d'abord, puis la VM2, puis l'interface.

### 8.1 Sur la VM1 — le moteur

```bash
cd carrefour-v2i-pyqt6 && ./deploiement/demarrer.sh moteur
```

Attendu :

```
[DB:moteur] Connexion a carrefour_moteur_db@127.0.0.1 reussie.
[Lien VM2] En ecoute sur 0.0.0.0:5051
Simulation demarree (30 ticks/s).
```

**Laissez cette fenêtre ouverte.** Le moteur occupe ce terminal : pour
taper d'autres commandes sur cette VM, ouvrez un second écran avec
**Alt + F2**, ou connectez-vous en SSH.

### 8.2 Sur la VM2 — la passerelle

```bash
cd carrefour-v2i-pyqt6 && ./deploiement/demarrer.sh passerelle
```

La ligne qui prouve que les deux VM communiquent :

```
[Lien moteur] Connecte au moteur 192.168.56.10:5051
```

### 8.3 Sur votre PC — l'interface graphique

L'interface ne tourne pas dans les VM (elles n'ont pas d'écran), mais
sur votre PC. Ouvrez un terminal **sur votre PC**, pas dans une VM :

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

Installez les dépendances :

```bash
pip install -r requirements.txt
```

Indiquez l'adresse de la VM2 et lancez — Windows :

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

**La fenêtre du carrefour s'ouvre.** En haut à droite doit s'afficher :

```
🟢 Connecté au serveur 192.168.56.11:5050
```

Vous voyez les véhicules circuler, les feux changer, et les usagers
s'arrêter aux passages piétons.

---

## Partie 9 — Vérifier que tout fonctionne vraiment

### Déclencher une urgence

Dans l'interface, à droite, cliquez sur le **+** de la ligne
**Urgences**. Observez :

- l'axe du véhicule d'urgence passe en **rouge** : c'est la voie réservée
- deux panneaux **SAUF URGENCES** s'allument à ses entrées
- un **compte à rebours** annonce son arrivée
- les véhicules ordinaires sont déviés et la voie se vide devant elle

C'est le mécanisme central du projet.

### Vérifier les bases de données

Sur la **VM1**, le résultat principal — les urgences doivent afficher un
temps de traversée nettement inférieur :

```bash
sudo mariadb carrefour_moteur_db -e "SELECT type_usager, COUNT(*) AS nb, ROUND(AVG(temps_parcours),2) AS temps_moyen_s FROM usager WHERE temps_parcours IS NOT NULL GROUP BY type_usager ORDER BY temps_moyen_s;"
```

Sur la **VM2**, le bilan des sessions :

```bash
sudo mariadb carrefour_stats_db -e "SELECT * FROM session_simulation;"
```

### Vérifier que les données sont bien réparties

Sur la VM1 :

```bash
sudo mariadb -e "SHOW DATABASES;"
```

`carrefour_moteur_db` apparaît, mais **pas** `carrefour_stats_db` — et
l'inverse sur la VM2. C'est la preuve que les données ne sont pas
centralisées sur une seule machine.

---

## Partie 10 — Tout arrêter proprement

1. Fermez la fenêtre de l'interface sur votre PC.
2. Sur la **VM2** : **Ctrl + C**.
   Vous devez voir `[DB:passerelle] Bilan de session enregistre.`
   **Cette étape écrit le bilan en base**, ne la sautez pas.
3. Sur la **VM1** : **Ctrl + C**. Elle affiche son résumé de simulation.
4. Sur chaque VM : `sudo poweroff`

Pour relancer plus tard, reprenez directement à la **partie 8**.

---

## En cas de problème

| Ce que vous voyez | Cause et solution |
|---|---|
| L'interface affiche « Mode dégradé » | La passerelle n'est pas lancée sur la VM2, ou l'adresse dans `CARREFOUR_SOCKET_SERVEUR_HOTE` est fausse |
| La VM2 répète « VM1 injoignable » | Le moteur n'est pas lancé sur la VM1, ou `IP_MOTEUR` est fausse. Relancez l'étape 7.3 avec la bonne adresse |
| `ping` entre les VM ne répond pas | Carte réseau privée manquante ou différente entre les deux VM. Reprenez la partie 6 |
| `sudo : commande introuvable` | Mot de passe root défini à l'installation. Voir l'encadré en 7.1 |
| `pip install` échoue | Python trop ancien. Il faut **3.11 ou plus récent** : `python3 --version` |
| Ce que je tape dans la VM ne fait rien | Un service tourne dans ce terminal. Ouvrez un second écran avec **Alt + F2** |
| `demarrer.sh: command not found` | Vous n'êtes pas dans le bon dossier : `cd carrefour-v2i-pyqt6` |
| La souris reste bloquée dans la VM | Appuyez sur la touche **Ctrl de droite** |
| « base désactivée » au démarrage | MariaDB absent ou arrêté. Sans gravité : la simulation tourne, mais n'enregistre rien |

Un script fait ces vérifications pour vous, sur chaque VM :

```bash
./deploiement/verifier.sh 192.168.56.10
```
