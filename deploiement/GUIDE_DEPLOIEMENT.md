# Guide de déploiement — postes de l'IUT

Ce guide déploie le projet sur **deux machines virtuelles Debian 13
dotées d'un bureau**, sous VirtualBox, sur un poste de l'IUT.

**Aucune VM n'est à installer ni à configurer depuis zéro** : la VM
`Debian13_FR` est fournie. Il suffit de la récupérer, de la cloner, puis
de déployer le projet.

Durée : **environ 30 minutes**, dont la copie de la VM.

> **Dans ce guide**, l'utilisateur est `toto` et les adresses privées
> sont `192.168.56.10` (VM1) et `192.168.56.11` (VM2). Remplacez-les par
> les vôtres si elles diffèrent, mais gardez-les cohérentes jusqu'au
> bout.

| VM | Rôle | Adresse privée | Base |
|---|---|---|---|
| VM1 | moteur de simulation | `192.168.56.10` | `carrefour_moteur_db` |
| VM2 | passerelle + interface | `192.168.56.11` | `carrefour_stats_db` |

### Trois règles qui évitent l'essentiel des erreurs

1. **Les étapes marquées « sur les DEUX VM » se font sur les deux.**
   L'erreur la plus fréquente est de corriger une seule machine, puis
   de chercher pourquoi la liaison ne marche toujours pas.
2. **Ne sautez aucun point de contrôle** (encadrés ✅). Ils prennent
   dix secondes et évitent de découvrir une erreur trois étapes plus
   loin, quand sa cause n'est plus évidente.
3. **Vérifiez sur quelle VM vous tapez.** Les deux fenêtres se
   ressemblent. L'étape 0 donne à chaque VM son nom, qui s'affiche dans
   l'invite de commande (`toto@vm1`, `toto@vm2`).

---

## Étape A — Obtenir les deux VM — 10 min

1. Dans l'explorateur de fichiers, ouvrez le dossier réseau **Commun**
   et repérez la VM **`Debian13_FR`**.
2. **Copiez-la dans le dossier `temp`** de votre poste. Elle est
   volumineuse : laissez la copie se terminer avant de continuer.
3. Ouvrez **VirtualBox** et ajoutez la VM, selon ce que contient
   `Debian13_FR` :
   - un fichier `.vbox` : menu **Machine → Ajouter…**, puis
     sélectionnez-le ;
   - un fichier `.ova` : menu **Fichier → Importer un appareil
     virtuel…**.
4. Renommez-la `VM1-Simulation` : clic droit → **Configuration →
   Général → Nom**.
5. **Créez la seconde VM par clonage.** VM1 éteinte, clic droit dessus →
   **Cloner…**
   - nom : `VM2-Passerelle`
   - **politique d'adresse MAC : générer de nouvelles adresses MAC pour
     toutes les cartes réseau** (le libellé exact varie un peu selon la
     version). C'est indispensable : sans cela, les deux VM portent la
     même adresse MAC et se perturbent mutuellement sur le réseau.
   - type de clone : **clone intégral**
6. **Vérifiez le réseau de chaque VM** : clic droit → **Configuration →
   Réseau**.

   | Onglet | Doit être |
   |---|---|
   | Adaptateur 1 | **NAT** (accès Internet) |
   | Adaptateur 2 | **Réseau privé hôte**, avec **le même nom** sur les deux VM |

   La VM fournie est normalement déjà réglée ainsi. Si l'Adaptateur 2
   manque, cochez **Activer l'interface réseau**.
7. Démarrez les deux VM et connectez-vous avec l'utilisateur `toto`.

---

## Étape 0 — Préparer les deux VM — 5 min

**À faire sur les DEUX VM.** Ouvrez un terminal et passez root :

```bash
su -
```

Réveillez la carte Internet, installez les outils, donnez les droits :

```bash
nmcli device connect enp0s3
```
```bash
apt update && apt install -y sudo curl unzip git
```
```bash
usermod -aG sudo toto
```

Donnez à chaque VM un nom distinct, pour ne pas vous tromper de machine
ensuite. Sur la **VM1** :

```bash
hostnamectl set-hostname vm1 && sed -i 's/vbox/vm1/g' /etc/hosts
```

Sur la **VM2** :

```bash
hostnamectl set-hostname vm2 && sed -i 's/vbox/vm2/g' /etc/hosts
```

Quittez root, puis ouvrez une **session neuve**. Sans cela le groupe
`sudo` n'est pas pris en compte : l'appartenance aux groupes est fixée à
l'ouverture de la session, et un nouvel onglet de terminal hérite de la
session de bureau, démarrée avant la commande.

```bash
exit
```
```bash
su - toto
```

> **✅ Contrôle 0** — sur chaque VM, ces trois commandes doivent
> réussir :
> ```bash
> sudo -v
> ```
> ```bash
> ping -c 2 deb.debian.org
> ```
> ```bash
> hostname
> ```
> Le dernier doit répondre `vm1` ou `vm2`. Si `ping` échoue, refaites
> `nmcli device connect enp0s3` en root.

---

## Étape 1 — Récupérer le projet — 2 min

**À faire sur les DEUX VM.** Deux façons, au choix : l'archive ZIP ou
`git clone`. Les deux aboutissent au même dossier
`~/carrefour-v2i-pyqt6`, et la suite du guide est identique.

### Option A — par l'archive ZIP (recommandé)

C'est ce que propose GitHub avec le bouton vert **Code → Download ZIP**.
Depuis le terminal de la VM, tout se fait en une fois :

```bash
cd ~
```
```bash
curl -L -o carrefour.zip https://github.com/Al3m1rr/carrefour-v2i-pyqt6/archive/refs/heads/main.zip
```
```bash
unzip -q carrefour.zip && mv carrefour-v2i-pyqt6-main carrefour-v2i-pyqt6
```
```bash
cd carrefour-v2i-pyqt6 && chmod +x deploiement/*.sh
```

> **Le renommage n'est pas un détail** : GitHub nomme le dossier extrait
> `carrefour-v2i-pyqt6-main`, avec le suffixe de la branche. Le renommer
> évite d'avoir à adapter toutes les commandes qui suivent.
>
> Le `chmod` est une précaution : l'archive conserve bien les droits
> d'exécution, mais certains extracteurs graphiques les perdent.

**Vous avez téléchargé le ZIP avec le navigateur de la VM ?** Il est
alors dans `~/Téléchargements`. Remplacez les deux premières commandes
par :

```bash
cd ~ && unzip -q ~/Téléchargements/carrefour-v2i-pyqt6-main.zip
```

**Vous refaites le déploiement ?** Supprimez d'abord l'ancien dossier,
sinon `mv` échouera :

```bash
rm -rf ~/carrefour-v2i-pyqt6
```

### Option B — par git

```bash
cd ~ && git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
```
```bash
cd carrefour-v2i-pyqt6
```

> **✅ Contrôle 1** — quelle que soit l'option :
> ```bash
> ls deploiement/
> ```
> doit afficher `demarrer.sh`, `installer_vm.sh`, `verifier.sh` et les
> deux guides.

---

## Étape 2 — Provisionner — 5 min

Cette étape installe MariaDB, crée la base du rôle, prépare
l'environnement Python des serveurs et fixe l'adresse privée de façon
**permanente**.

> **Pourquoi une adresse fixe plutôt que le DHCP ?** Ces VM n'ont qu'un
> seul profil réseau, lié à aucune carte : NetworkManager le déplace
> d'une carte à l'autre, et celle qu'il quitte perd son adresse. Le
> script crée donc un profil par carte, désactive le profil flottant et
> impose les adresses. Elles sont ainsi connues d'avance, ne changent
> plus, et survivent au redémarrage.

La commande **diffère selon la VM**. Sur la **VM1** :

```bash
sudo IP_LOCALE=192.168.56.10 bash deploiement/installer_vm.sh moteur
```

Sur la **VM2** :

```bash
sudo IP_LOCALE=192.168.56.11 IP_MOTEUR=192.168.56.10 bash deploiement/installer_vm.sh passerelle
```

> **✅ Contrôle 2** — chaque VM doit afficher, avec sa propre adresse :
> ```
> Carte Internet enp0s3 : profil carrefour-nat (DHCP)
> Configure via NetworkManager (profil carrefour-prive, permanent)
> OK : enp0s8 porte 192.168.56.10
> ```
> Si vous lisez `ECHEC`, la VM n'a pas de seconde carte réseau :
> revoyez l'étape A.6.

**Vous vous êtes trompé de rôle sur une VM ?** Relancez la bonne
commande, puis supprimez la base en trop, sinon la preuve de répartition
de l'étape 6 ne tiendra plus. Sur la VM1 :

```bash
sudo mariadb -e "DROP DATABASE IF EXISTS carrefour_stats_db;"
```

Sur la VM2 : même commande avec `carrefour_moteur_db`.

---

## Étape 3 — Vérifier la liaison — 1 min

Depuis la **VM2** :

```bash
ping -c 3 192.168.56.10
```

> **✅ Contrôle 3** — trois réponses, en 1 à 2 ms.
>
> `Destination Host Unreachable` signifie, 9 fois sur 10, que l'étape 2
> n'a été faite **que sur une seule VM**. Vérifiez l'autre.

---

## Étape 4 — Démarrer les services — 2 min

La VM1 d'abord. Sur la **VM1** :

```bash
cd ~/carrefour-v2i-pyqt6 && ./deploiement/demarrer.sh moteur
```

Puis sur la **VM2** :

```bash
cd ~/carrefour-v2i-pyqt6 && ./deploiement/demarrer.sh passerelle
```

> **✅ Contrôle 4** — la VM2 affiche :
> ```
> [Lien moteur] Connecte au moteur 192.168.56.10:5051
> ```
> Si elle répète `VM1 injoignable`, le moteur n'est pas lancé. Inutile
> de relancer la passerelle : elle réessaie toutes les 3 secondes et se
> connectera seule.

**Laissez ces deux fenêtres ouvertes** : chaque service occupe son
terminal.

---

## Étape 5 — Lancer l'interface — 5 min

Dans la **VM2**, ouvrez un **nouvel onglet de terminal** : le premier
est pris par la passerelle.

Le client a besoin de son propre environnement Python. Celui des
serveurs ne contient pas PyQt6, volontairement, pour ne pas installer Qt
là où il ne sert pas.

```bash
sudo apt install -y libxcb-cursor0 python3-venv
```
```bash
cd ~/carrefour-v2i-pyqt6
```
```bash
python3 -m venv venv-client && venv-client/bin/pip install -r requirements.txt
```

Une à deux minutes. Puis :

```bash
CARREFOUR_SOCKET_SERVEUR_HOTE=127.0.0.1 venv-client/bin/python client/main_client.py
```

> ⚠ **Lancez-le depuis un terminal ouvert sur le bureau**, jamais après
> un `su -` ou un `su - toto` : ces commandes ouvrent une session qui
> **perd la variable `DISPLAY`**, et Qt échoue avec
> `qt.qpa.xcb: could not connect to display`. Le message suivant, à
> propos de `libxcb-cursor0`, est trompeur : il s'affiche même quand le
> paquet est installé.
>
> En cas de doute, `echo $DISPLAY` doit répondre `:0` ou `:1`. Si la
> réponse est vide, tapez `exit` pour revenir au terminal du bureau, ou
> en dernier recours `export DISPLAY=:0`.

> **✅ Contrôle 5** — la fenêtre s'ouvre et affiche en haut à droite
> `Connecté au serveur 127.0.0.1:5050`.

---

## Étape 6 — Vérifier le projet — 3 min

**Le mécanisme central.** Dans l'interface, cliquez sur le **+** de la
ligne **Urgences**. L'axe du véhicule passe en rouge, deux panneaux
*SAUF URGENCES* s'allument, un compte à rebours annonce son arrivée et
la voie se vide devant lui.

**Le résultat mesuré.** Sur la **VM1**, dans un nouvel onglet :

```bash
sudo mariadb carrefour_moteur_db -e "SELECT type_usager, COUNT(*) AS nb, ROUND(AVG(temps_parcours),2) AS temps_moyen_s FROM usager WHERE temps_parcours IS NOT NULL GROUP BY type_usager ORDER BY temps_moyen_s;"
```

Les véhicules d'urgence doivent apparaître en tête, avec un temps de
traversée très inférieur à celui des véhicules ordinaires.

**La preuve de la répartition.** Sur **chaque** VM :

```bash
sudo mariadb -e "SHOW DATABASES;"
```

La VM1 a `carrefour_moteur_db` mais **pas** `carrefour_stats_db`, et
l'inverse sur la VM2 : les données ne sont pas centralisées.

**Le boîtier ambulance (facultatif).** Il simule le véhicule d'urgence
et émet une alerte V2I signée. Dans la **VM2**, depuis la racine du
projet :

```bash
python3 ambulance/main_ambulance.py 127.0.0.1 5050 1 N
```

Les arguments sont l'adresse de la passerelle, son port, la priorité
(1 à 3) et la branche d'entrée (`N`, `S`, `E`, `W`).

---

## Étape 7 — Tout arrêter

1. Fermez la fenêtre de l'interface.
2. Sur la **VM2** : `Ctrl + C`. Vous devez lire
   `[DB:passerelle] Bilan de session enregistre.` — **c'est cette étape
   qui écrit le bilan en base**, ne la sautez pas.
3. Sur la **VM1** : `Ctrl + C`.
4. Sur chaque VM : `sudo poweroff`.

Pour consulter le bilan, sur la VM2 :

```bash
sudo mariadb carrefour_stats_db -e "SELECT * FROM session_simulation;"
```

Pour relancer plus tard, reprenez directement à l'**étape 4** : le
provisionnement est permanent.

---

## Si ça coince

Ces trois commandes disent presque tout. Lancez-les sur chaque VM avant
de chercher plus loin :

```bash
ip -brief addr
```
```bash
ip route
```
```bash
./deploiement/verifier.sh 192.168.56.10
```

| Ce que vous voyez | Solution |
|---|---|
| `n'est pas dans le fichier sudoers` | Étape 0, puis ouvrez une **session neuve** avec `su - toto` : un nouvel onglet ne suffit pas |
| `Could not resolve host: github.com` | La carte Internet n'a plus d'adresse : en root, `nmcli device connect enp0s3` |
| Une carte `UP` mais sans adresse IPv4 | Refaites l'étape 2 avec `IP_LOCALE` sur cette VM |
| `192.168.56.x` présent sur `enp0s3` | Adresse privée posée sur la carte Internet : refaites l'étape 2, le script répare |
| `Destination Host Unreachable` | L'étape 2 n'a été faite que sur une VM. Sinon, les deux VM n'ont pas le même réseau privé (étape A.6) ou la même adresse MAC (étape A.5) |
| `could not connect to display` | Vous êtes dans une session `su` : tapez `exit`, ou `export DISPLAY=:0` |
| `VM1 injoignable` en boucle | Le moteur n'est pas lancé sur la VM1 |
| Les deux VM ont la même adresse MAC | Elles ont été copiées au lieu d'être clonées avec de nouvelles adresses MAC : refaites l'étape A.5 |
| `demarrer.sh: command not found` | Mauvais dossier : `cd ~/carrefour-v2i-pyqt6` |
| Ce que je tape ne fait rien | Un service occupe ce terminal : ouvrez un nouvel onglet |
| « base désactivée » au démarrage | MariaDB absent ou arrêté. La simulation tourne mais n'enregistre rien |
| Les deux VM portent des bases en trop | Voir *Vous vous êtes trompé de rôle*, étape 2 |
