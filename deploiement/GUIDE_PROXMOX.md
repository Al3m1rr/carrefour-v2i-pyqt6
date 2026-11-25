# Déploiement sur Proxmox — une seule commande

**SAÉ 3.02 — Groupe « Python Mayo »** — Atakan Gocer · Louise Halter-Tisler

C'est la façon la plus simple de faire tourner le projet. Comptez
**5 minutes**, dont l'essentiel en attente.

Rien à configurer : pas de clonage de machine, pas d'adresse IP à
choisir, pas de carte réseau à régler. Proxmox adresse les conteneurs,
le script lit les adresses obtenues et relie les deux machines
lui-même.

> L'autre procédure, sur deux VM VirtualBox, reste disponible dans
> [GUIDE_DEPLOIEMENT.md](GUIDE_DEPLOIEMENT.md). Elle demande une
> trentaine de minutes et une configuration réseau manuelle.

---

## Ce qu'il vous faut

- Un serveur **Proxmox VE 8 ou 9**, avec un accès **root à son shell**
  (en SSH, ou par la console du nœud dans l'interface web : sélectionner
  le nœud, puis *Shell*).
- Le serveur doit avoir **accès à Internet** : le script télécharge le
  modèle Debian et le projet.
- Un **PC** pour l'interface, qui doit pouvoir joindre le serveur sur le
  réseau.

---

## Étape 1 — Lancer le déploiement

Sur le shell du serveur Proxmox, en root :

```bash
curl -fsSLO https://raw.githubusercontent.com/Al3m1rr/carrefour-v2i-pyqt6/main/deploiement/proxmox.sh && bash proxmox.sh
```

C'est tout. Le script affiche son avancement, puis se termine par un
encadré qui donne les adresses et la commande à taper ensuite.

**Ce qu'il fait**, dans l'ordre :

1. vérifie qu'il tourne bien sur un serveur Proxmox ;
2. récupère le modèle Debian 13 s'il n'est pas déjà présent ;
3. crée deux conteneurs LXC, `carrefour-moteur` et `carrefour-passerelle`,
   avec deux numéros libres ;
4. installe dans chacun MariaDB, sa base de données et l'environnement
   Python du projet ;
5. indique à la passerelle l'adresse du moteur ;
6. déclare les deux serveurs en services `systemd`, puis les démarre ;
7. contrôle que les services tournent et que la passerelle joint bien le
   moteur.

À la fin, vous devez lire `Le projet tourne.`

---

## Étape 2 — Lancer l'interface sur votre PC

Le script a affiché l'adresse de la passerelle. Sur le PC, dans le
dossier du projet :

```bash
pip install -r requirements.txt
```

Puis, sous **Linux ou macOS** (remplacez l'adresse par celle affichée) :

```bash
CARREFOUR_SOCKET_SERVEUR_HOTE=192.168.1.121 python client/main_client.py
```

Sous **Windows**, dans PowerShell :

```bash
$env:CARREFOUR_SOCKET_SERVEUR_HOTE='192.168.1.121'; python client/main_client.py
```

La fenêtre s'ouvre sur le carrefour en mouvement. Les boutons **+** et
**−** ajoutent et retirent des usagers ; le menu « Priorité alerte »
suivi du **+** des urgences déclenche une ambulance.

Sous Linux, si Qt refuse de démarrer, il manque une bibliothèque
système :

```bash
sudo apt install -y libxcb-cursor0
```

---

## Commandes utiles

Les numéros des conteneurs sont ceux affichés à la fin du script.

| Pour | Commande, sur le serveur Proxmox |
|---|---|
| Voir les conteneurs | `pct list` |
| Suivre les messages du moteur | `pct exec 300 -- journalctl -u carrefour -f` |
| Redémarrer un service | `pct exec 300 -- systemctl restart carrefour` |
| Tout arrêter | `pct stop 300 && pct stop 301` |
| Tout relancer | `pct start 300 && pct start 301` |
| Recommencer de zéro | `bash proxmox.sh --recreer` |

Les deux conteneurs redémarrent seuls avec le serveur, et les services
repartent seuls avec les conteneurs.

---

## Si ça coince

| Message | Cause et solution |
|---|---|
| `la commande 'pct' est introuvable` | Vous êtes dans une VM, pas sur le serveur Proxmox. Ouvrez le shell du **nœud** |
| `stockage 'local-lvm' inconnu` | Votre serveur nomme ses stockages autrement. Le message liste les noms valables : relancez avec `STOCKAGE=<nom> bash proxmox.sh` |
| `aucun modele Debian 13 disponible` | Le serveur n'a pas accès à Internet, ou son catalogue est vide. Lancez `pveam update` puis réessayez |
| `n'a pas obtenu d'adresse IP` | Le pont réseau ne distribue pas de DHCP. Indiquez le bon pont : `PONT=vmbr1 bash proxmox.sh` |
| `le conteneur 300 existe deja` | Relancez avec `bash proxmox.sh --recreer`, ou donnez d'autres numéros : `CTID_MOTEUR=310 CTID_PASSERELLE=311 bash proxmox.sh` |
| `SERVICE ARRETE` | Le script affiche alors le journal du service, qui donne la cause |
| L'interface reste en rouge | La passerelle n'est pas joignable depuis le PC. Vérifiez l'adresse, puis que le PC et le serveur sont bien sur le même réseau |

---

## Si vous n'avez pas le shell du serveur

Avec l'interface web seule, la procédure reste courte. Deux fois, une
pour chaque rôle :

1. **Create CT**, modèle `debian-13-standard`, réseau **DHCP**,
   4 Go de disque, 1 Go de mémoire. Nommez le premier
   `carrefour-moteur`, le second `carrefour-passerelle`.
2. Ouvrez la **Console** du conteneur et lancez :

```bash
apt update && apt install -y git && git clone https://github.com/Al3m1rr/carrefour-v2i-pyqt6.git /opt/carrefour
```

3. Sur le conteneur **moteur** :

```bash
bash /opt/carrefour/deploiement/installer_vm.sh moteur && hostname -I
```

Notez l'adresse affichée, puis sur le conteneur **passerelle** :

```bash
IP_MOTEUR=<adresse-du-moteur> bash /opt/carrefour/deploiement/installer_vm.sh passerelle
```

4. Démarrez les serveurs, le moteur d'abord :

```bash
/opt/carrefour/deploiement/demarrer.sh moteur
```

```bash
/opt/carrefour/deploiement/demarrer.sh passerelle
```

5. Lancez l'interface comme à l'étape 2, avec l'adresse de la
   passerelle (`hostname -I` dans son conteneur).

---

## Pourquoi des conteneurs plutôt que des machines virtuelles

L'architecture du projet est inchangée : **deux machines distinctes**,
chacune avec son processus et sa propre base de données, reliées par un
socket TCP. Le conteneur LXC apporte seulement une mise en œuvre plus
légère : il démarre en quelques secondes, reçoit son adresse de Proxmox,
et n'a pas besoin d'un bureau graphique puisque l'interface tourne sur
le PC de l'utilisateur.

C'est d'ailleurs plus fidèle à la réalité visée : dans un vrai carrefour,
le poste de supervision n'est pas dans l'armoire de commande.
