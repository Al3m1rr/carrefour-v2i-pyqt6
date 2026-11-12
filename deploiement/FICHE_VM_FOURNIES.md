# Fiche de déploiement — VM Debian fournies toutes prêtes

Fiche linéaire, à dérouler de haut en bas, pour deux VM Debian 13
**déjà installées et dotées d'un bureau** (cas des postes de l'IUT).
Comptez **25 minutes**.

Vous devez créer les VM vous-même ? Prenez plutôt le
[guide complet](GUIDE_COMPLET.md).

> **Dans cette fiche**, l'utilisateur est `toto` et les adresses privées
> sont `192.168.56.10` (VM1) et `192.168.56.11` (VM2). Remplacez-les par
> les vôtres si elles diffèrent, mais gardez-les cohérentes jusqu'au
> bout.

| VM | Rôle | Adresse privée | Base |
|---|---|---|---|
| VM1 | moteur de simulation | `192.168.56.10` | `carrefour_moteur_db` |
| VM2 | passerelle + interface | `192.168.56.11` | `carrefour_stats_db` |

**Avant de commencer**, vérifiez dans VirtualBox que **chaque** VM a
deux cartes réseau : *Adaptateur 1* en **NAT**, *Adaptateur 2* en
**Réseau privé hôte**, avec le **même nom de réseau** sur les deux VM.

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
apt update && apt install -y sudo git
```
```bash
usermod -aG sudo toto
```
```bash
exit
```

Ouvrez ensuite une **session neuve**, sinon le groupe `sudo` ne sera pas
pris en compte :

```bash
su - toto
```

> **✅ Contrôle 0** — ces deux commandes doivent réussir :
> ```bash
> sudo -v
> ```
> ```bash
> ping -c 2 deb.debian.org
> ```
> Si `ping` échoue, refaites `nmcli device connect enp0s3` en root.

---

## Étape 1 — Récupérer le projet — 2 min

**À faire sur les DEUX VM** :

```bash
git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git
```
```bash
cd carrefour-v2i-pyqt6
```

---

## Étape 2 — Provisionner — 5 min

Installe MariaDB, crée la base du rôle, fixe l'adresse privée de façon
**permanente**. Attention, la commande diffère selon la VM.

Sur la **VM1** :

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
> revoyez sa configuration dans VirtualBox.

**Vous vous êtes trompé de rôle ?** Relancez la bonne commande, puis
supprimez la base en trop, sinon la preuve de répartition ne tiendra
plus :

```bash
sudo mariadb -e "DROP DATABASE IF EXISTS carrefour_stats_db;"   # sur la VM1
```

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

**Laissez ces deux fenêtres ouvertes**, les services les occupent.

---

## Étape 5 — Lancer l'interface — 5 min

Dans la **VM2**, ouvrez un **nouvel onglet de terminal** : le premier
est pris par la passerelle.

Le client a besoin de son propre environnement Python, car celui des
serveurs ne contient pas PyQt6 — volontairement, pour ne pas installer
Qt sur une machine sans écran.

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
> un `su -`. Ces commandes perdent la variable `DISPLAY` et Qt échoue
> avec `could not connect to display` ; le message suivant, à propos de
> `libxcb-cursor0`, est trompeur.
>
> En cas de doute : `echo $DISPLAY` doit répondre `:0` ou `:1`. Si la
> réponse est vide, tapez `exit` pour revenir au terminal du bureau.

> **✅ Contrôle 5** — la fenêtre s'ouvre et affiche en haut à droite
> `Connecté au serveur 127.0.0.1:5050`.

---

## Étape 6 — Vérifier le projet — 3 min

**Le mécanisme central** : dans l'interface, cliquez sur le **+** de la
ligne **Urgences**. L'axe du véhicule passe en rouge, deux panneaux
*SAUF URGENCES* s'allument, un compte à rebours annonce son arrivée et
la voie se vide devant lui.

**Le résultat mesuré**, sur la VM1 (nouvel onglet) :

```bash
sudo mariadb carrefour_moteur_db -e "SELECT type_usager, COUNT(*) AS nb, ROUND(AVG(temps_parcours),2) AS temps_moyen_s FROM usager WHERE temps_parcours IS NOT NULL GROUP BY type_usager ORDER BY temps_moyen_s;"
```

Les véhicules d'urgence doivent apparaître en tête, très loin devant
les véhicules ordinaires.

**La preuve de la répartition**, sur **chaque** VM :

```bash
sudo mariadb -e "SHOW DATABASES;"
```

La VM1 a `carrefour_moteur_db` mais **pas** `carrefour_stats_db`, et
l'inverse sur la VM2. Les données ne sont donc pas centralisées.

---

## Étape 7 — Tout arrêter

1. Fermez la fenêtre de l'interface.
2. Sur la **VM2** : `Ctrl + C`. Vous devez lire
   `[DB:passerelle] Bilan de session enregistre.` — **c'est cette étape
   qui écrit le bilan en base**, ne la sautez pas.
3. Sur la **VM1** : `Ctrl + C`.
4. Sur chaque VM : `sudo poweroff`.

Pour relancer plus tard, reprenez directement à l'**étape 4** : le
provisionnement est permanent.

---

## Si ça coince

| Ce que vous voyez | Solution |
|---|---|
| `n'est pas dans le fichier sudoers` | Étape 0, et ouvrez une **session neuve** avec `su - toto` : un nouvel onglet ne suffit pas |
| `Could not resolve host: github.com` | La carte Internet dort : `sudo nmcli device connect enp0s3` |
| Une carte `UP` mais sans adresse | Refaites l'étape 2 avec `IP_LOCALE` sur cette VM |
| `Destination Host Unreachable` | L'étape 2 n'a été faite que sur une VM |
| `could not connect to display` | Vous êtes dans une session `su` : tapez `exit`, ou `export DISPLAY=:0` |
| `VM1 injoignable` en boucle | Le moteur n'est pas lancé sur la VM1 |
| `demarrer.sh: command not found` | `cd ~/carrefour-v2i-pyqt6` |

Un diagnostic complet, sans rien modifier :

```bash
./deploiement/verifier.sh 192.168.56.10
```
