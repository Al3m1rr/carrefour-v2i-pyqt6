# Déploiement

👉 **[Guide Proxmox](GUIDE_PROXMOX.md)** — le plus simple : une seule
commande sur le serveur, environ 5 minutes, sans configuration réseau.

👉 **[Guide de déploiement pas à pas](GUIDE_DEPLOIEMENT.md)** — deux VM
Debian 13 avec bureau, sous VirtualBox, sur un poste de l'IUT. Environ
30 minutes. La VM `Debian13_FR` est à récupérer dans le dossier réseau
**Commun** et à copier dans **temp** ; aucune VM n'est à installer
depuis zéro.

## Les scripts de ce dossier

| Script | Rôle |
|---|---|
| `proxmox.sh` | **Déploiement complet sur Proxmox** : crée les deux conteneurs LXC, installe le projet, déclare les services systemd et démarre le tout. À lancer en root sur le serveur Proxmox |
| `installer_vm.sh` | Provisionne une VM selon son rôle (`moteur` ou `passerelle`) : MariaDB, base du rôle, environnement Python, adresse privée permanente. Réexécutable sans risque |
| `demarrer.sh` | Démarre le service du rôle, en chargeant la configuration écrite par l'installateur |
| `verifier.sh` | Diagnostique une VM sans rien modifier : outils, Python, Internet, adresses, MariaDB, services |

Les dépendances des serveurs sont dans `../requirements-serveur.txt`,
celles de l'interface dans `../requirements.txt`.
