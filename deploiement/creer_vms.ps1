# Cree et installe automatiquement les deux VM Debian 13 du projet.
#
# A executer sur le PC hote (Windows), depuis la racine du projet :
#     powershell -ExecutionPolicy Bypass -File deploiement\creer_vms.ps1
#
# Si des VM portent deja ces noms sur votre poste, changez le prefixe :
#     ... -File deploiement\creer_vms.ps1 -Prefixe MonGroupe -PortSSH1 2301 -PortSSH2 2302
#
# Prerequis : VirtualBox 7.x installe. Le script telecharge l'ISO Debian
# si elle est absente, cree les deux VM, et lance une installation sans
# intervention. Comptez 20 a 40 minutes selon la connexion.
#
# Une fois les VM installees, provisionnez-les avec :
#     deploiement/installer_vm.sh  (voir le README)

param(
    # Prefixe des noms de VM, pour ne pas ecraser des machines existantes.
    [string]$Prefixe = "Carrefour",
    # Ports de l'hote rediriges vers le SSH de chaque VM.
    [int]$PortSSH1 = 2201,
    [int]$PortSSH2 = 2202,
    # Memoire par VM, en Mo. 1536 suffit pour une Debian sans bureau.
    [int]$RamMo = 1536
)

$ErrorActionPreference = "Stop"

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path $vbox)) {
    throw "VBoxManage introuvable. Installez VirtualBox depuis https://www.virtualbox.org"
}

# --- Parametres ------------------------------------------------------
$isoUrl   = "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-13.7.0-amd64-netinst.iso"
$isoPath  = Join-Path $env:USERPROFILE "Downloads\debian-13.7.0-amd64-netinst.iso"
$utilisateur = "carrefour"
$motDePasse  = "Carrefour2026!"     # VM de test locale uniquement
$ramMo    = $RamMo
$disqueMo = 20000

$machines = @(
    @{ Nom = "$Prefixe-VM1-Simulation"; Hote = "vm1.carrefour.lan"; PortSSH = $PortSSH1 },
    @{ Nom = "$Prefixe-VM2-Passerelle"; Hote = "vm2.carrefour.lan"; PortSSH = $PortSSH2 }
)

# --- 1. ISO Debian ---------------------------------------------------
if (-not (Test-Path $isoPath)) {
    Write-Host "Telechargement de l'ISO Debian 13 (environ 750 Mo)..."
    Invoke-WebRequest -Uri $isoUrl -OutFile $isoPath
} else {
    Write-Host "ISO Debian deja presente : $isoPath"
}

# --- 2. Reseau prive hote --------------------------------------------
# Les deux VM ont besoin d'un reseau prive pour se parler, et le PC hote
# doit etre sur le meme sous-reseau pour que le client PyQt6 joigne la
# passerelle.
#
# Important : on FORCE l'interface en 192.168.56.1/24. Sans cela, un
# poste dont l'interface host-only est deja en 192.168.57.x se
# retrouverait avec des VM configurees en 192.168.56.x par
# installer_vm.sh : elles ne verraient ni l'hote ni l'autre VM.
$hostonly = (& $vbox list hostonlyifs | Select-String '^Name:' | Select-Object -First 1)
if ($hostonly) {
    $nomReseau = ($hostonly -split ':', 2)[1].Trim()
    Write-Host "Reseau prive hote existant : $nomReseau"
} else {
    Write-Host "Creation d'un reseau prive hote..."
    & $vbox hostonlyif create
    $nomReseau = ((& $vbox list hostonlyifs | Select-String '^Name:' | Select-Object -First 1) -split ':', 2)[1].Trim()
}
& $vbox hostonlyif ipconfig $nomReseau --ip 192.168.56.1 --netmask 255.255.255.0
Write-Host "Interface $nomReseau fixee a 192.168.56.1/24"

# --- 3. Creation et installation des VM ------------------------------
$dossierVM = ((& $vbox list systemproperties | Select-String 'Default machine folder') -split ':', 2)[1].Trim()

foreach ($m in $machines) {
    $nom = $m.Nom

    if ((& $vbox list vms) -match [regex]::Escape($nom)) {
        Write-Host "$nom existe deja, on passe."
        continue
    }

    Write-Host "=== Creation de $nom ==="
    & $vbox createvm --name $nom --ostype Debian_64 --register
    & $vbox modifyvm $nom --memory $ramMo --cpus 2 --vram 16 `
            --graphicscontroller vmsvga --audio-driver none --boot1 dvd --boot2 disk
    & $vbox modifyvm $nom --nic1 nat --nictype1 virtio `
            --nic2 hostonly --nictype2 virtio --hostonlyadapter2 $nomReseau
    & $vbox modifyvm $nom --natpf1 "ssh,tcp,127.0.0.1,$($m.PortSSH),,22"

    $disque = Join-Path $dossierVM "$nom\$nom.vdi"
    & $vbox createmedium disk --filename $disque --size $disqueMo --format VDI
    & $vbox storagectl $nom --name "SATA" --add sata --controller IntelAhci --portcount 2
    & $vbox storageattach $nom --storagectl "SATA" --port 0 --device 0 --type hdd --medium $disque
    & $vbox storageattach $nom --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium emptydrive

    Write-Host "=== Installation sans intervention de $nom ==="
    # Chaque etape tolere l'echec et le script se termine par exit 0.
    # Sans cela, le programme d'installation affiche en fin de parcours
    # un dialogue bloquant "Echec de la commande preconfiguree" qui
    # suspend l'installation automatique.
    # A noter : VirtualBox definit un mot de passe root, ce qui empeche
    # Debian d'appliquer son comportement par defaut (installer sudo et
    # y ajouter le premier utilisateur). D'ou l'etape d'amorcage
    # decrite dans deploiement/README.md.
    $postInstall = "apt-get update || true; " +
                   "DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server sudo git python3-venv python3-pip || true; " +
                   "usermod -aG sudo $utilisateur || true; " +
                   "exit 0"
    & $vbox unattended install $nom `
            --iso=$isoPath --user=$utilisateur --password=$motDePasse `
            --full-user-name="Projet Carrefour" --hostname=$($m.Hote) `
            --locale=fr_FR --country=FR --time-zone=Europe/Paris `
            --post-install-command=$postInstall `
            --start-vm=headless
}

Write-Host ""
Write-Host "=========================================================="
Write-Host " Installation lancee sur les deux VM (sans fenetre)."
Write-Host ""
Write-Host " Pour suivre : ouvrez VirtualBox, selectionnez une VM,"
Write-Host " puis cliquez sur 'Afficher'."
Write-Host ""
Write-Host " Quand l'installation est finie, connectez-vous :"
Write-Host "   ssh -p $PortSSH1 $utilisateur@127.0.0.1    # $Prefixe-VM1-Simulation"
Write-Host "   ssh -p $PortSSH2 $utilisateur@127.0.0.1    # $Prefixe-VM2-Passerelle"
Write-Host ""
Write-Host " Puis provisionnez chaque VM avec deploiement/installer_vm.sh"
Write-Host "=========================================================="
