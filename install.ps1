<#
    LernApp - Schnellinstallation fuer Windows 11

        iex (irm https://raw.githubusercontent.com/Larslllllll/Lernapp/main/install.ps1)

    Das Skript laedt die aktuelle Setup-Datei, prueft ihre Pruefsumme und
    installiert still nach %LOCALAPPDATA%. Es braucht keine Adminrechte und
    fasst vorhandene Nutzerdaten unter %USERPROFILE%\.lernapp nie an.

    Bewusst ohne Umlaute geschrieben: die Datei wird auch lokal mit
    Windows PowerShell 5.1 ausgefuehrt, das UTF-8 ohne BOM falsch dekodiert.
#>
[CmdletBinding()]
param(
    # Basis-URL des Release-Repos. Ueberschreibbar zum Testen gegen eine
    # Kopie, ohne das Skript zu aendern.
    [string]$Quelle = $env:LERNAPP_INSTALL_QUELLE,

    # Desktop-Verknuepfung anlegen (im Startmenue liegt LernApp immer).
    [switch]$Desktopverknuepfung,

    # Auch installieren, wenn dieselbe Version schon vorhanden ist.
    [switch]$Erzwingen,

    # Nach der Installation nicht starten.
    [switch]$NichtStarten,

    # Alles pruefen und melden, aber nichts herunterladen und nichts
    # installieren. Fuer Tests und zum Nachsehen, was passieren wuerde.
    [switch]$Probelauf
)

$ErrorActionPreference = 'Stop'
# Ohne das zeigt Invoke-WebRequest fuer jeden Block einen Fortschrittsbalken
# und wird dadurch um ein Vielfaches langsamer.
$ProgressPreference = 'SilentlyContinue'

# Diese GUID steht auch in packaging/lernapp.iss und identifiziert das
# Produkt ueber alle Versionen hinweg. Weichen die beiden voneinander ab,
# findet das Skript eine vorhandene Installation nicht mehr.
$AppId = '{7C4C1A62-8E3F-4C51-9C2B-0A5D3E7F1B94}'
$StandardQuelle = 'https://raw.githubusercontent.com/Larslllllll/Lernapp/main'

function Schreibe([string]$Text) { Write-Host "  $Text" }
function Melde([string]$Text)    { Write-Host "  $Text" -ForegroundColor Cyan }
function Gelungen([string]$Text) { Write-Host "  $Text" -ForegroundColor Green }
function Abbruch([string]$Text) {
    Write-Host ""
    Write-Host "  Abbruch: $Text" -ForegroundColor Red
    Write-Host ""
    exit 1
}

function Pruefe-Umgebung {
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Abbruch "PowerShell 5 oder neuer noetig, gefunden $($PSVersionTable.PSVersion)."
    }
    if ([Environment]::OSVersion.Platform -ne 'Win32NT') {
        Abbruch "Dieses Skript ist fuer Windows. Fuer macOS gibt es LernApp noch nicht."
    }
    if (-not [Environment]::Is64BitOperatingSystem) {
        Abbruch "LernApp gibt es nur fuer 64-Bit-Windows."
    }
    # Aeltere Systeme sprechen ohne Nachhilfe kein TLS 1.2 und scheitern
    # dann an GitHub statt an etwas Verstaendlichem.
    try {
        [Net.ServicePointManager]::SecurityProtocol =
            [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    } catch { }
}

function Laufende-App {
    # SilentlyContinue: "kein Prozess" ist hier keine Stoerung, sondern der
    # Normalfall.
    return @(Get-Process -Name 'LernApp' -ErrorAction SilentlyContinue)
}

function Hole-Manifest([string]$Basis) {
    $url = "$Basis/latest.json"
    try {
        $roh = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
    } catch {
        Abbruch "$url ist nicht erreichbar. Internetverbindung pruefen. ($($_.Exception.Message))"
    }
    try {
        $manifest = $roh.Content | ConvertFrom-Json
    } catch {
        Abbruch "$url enthaelt kein gueltiges JSON."
    }
    foreach ($feld in 'version', 'url', 'sha256') {
        if (-not $manifest.$feld) { Abbruch "Im Manifest fehlt das Feld '$feld'." }
    }
    if ($manifest.sha256 -notmatch '^[0-9a-fA-F]{64}$') {
        Abbruch "Die Pruefsumme im Manifest ist keine SHA-256-Angabe."
    }
    if ($manifest.url -notmatch '^https://') {
        Abbruch "Die Download-Adresse im Manifest ist kein HTTPS."
    }
    return $manifest
}

function Vorhandene-Installation {
    # Inno Setup legt ohne Adminrechte unter HKCU an, mit Adminrechten unter
    # HKLM. Beide Wege sind moeglich, also beide lesen.
    $pfade = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1"
    )
    foreach ($pfad in $pfade) {
        $eintrag = Get-ItemProperty -Path $pfad -ErrorAction SilentlyContinue
        if ($eintrag) { return $eintrag }
    }
    return $null
}

function Lade-Datei([string]$Url, [string]$Ziel) {
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Ziel -UseBasicParsing -TimeoutSec 600
    } catch {
        Abbruch "Download fehlgeschlagen: $($_.Exception.Message)"
    }
    if (-not (Test-Path $Ziel)) { Abbruch "Die heruntergeladene Datei fehlt." }
}

function Pruefe-Pruefsumme([string]$Datei, [string]$Erwartet) {
    $tatsaechlich = (Get-FileHash -Path $Datei -Algorithm SHA256).Hash
    if ($tatsaechlich -ne $Erwartet.ToUpperInvariant()) {
        Remove-Item $Datei -Force -ErrorAction SilentlyContinue
        Abbruch @"
Die Pruefsumme stimmt nicht.

  erwartet   $($Erwartet.ToUpperInvariant())
  bekommen   $tatsaechlich

Die Datei wurde geloescht und nicht ausgefuehrt. Das kann an einem
abgebrochenen Download liegen - oder daran, dass unterwegs jemand die
Datei ausgetauscht hat. Bitte den Befehl noch einmal ausfuehren und, falls
es wieder passiert, Lars Bescheid geben.
"@
    }
}

# ---------------------------------------------------------------- Ablauf

Write-Host ""
Write-Host "  LernApp - Installation" -ForegroundColor White
Write-Host ""

Pruefe-Umgebung

if (-not $Quelle) { $Quelle = $StandardQuelle }
$Quelle = $Quelle.TrimEnd('/')
if ($env:LERNAPP_INSTALL_DESKTOP -eq '1') { $Desktopverknuepfung = $true }

Melde "Version nachschlagen ..."
$manifest = Hole-Manifest $Quelle
Schreibe "verfuegbar: $($manifest.version)"

$installiert = Vorhandene-Installation
if ($installiert) {
    Schreibe "installiert: $($installiert.DisplayVersion)"
    if ($installiert.DisplayVersion -eq $manifest.version -and -not $Erzwingen) {
        Write-Host ""
        Gelungen "LernApp $($manifest.version) ist bereits aktuell. Nichts zu tun."
        Write-Host ""
        exit 0
    }
}

if ((Laufende-App).Count -gt 0) {
    Abbruch @"
LernApp laeuft gerade noch.

Bitte das Fenster schliessen und den Befehl danach noch einmal ausfuehren.
Solange die App laeuft, lassen sich ihre Programmdateien nicht ersetzen.
"@
}

if ($Probelauf) {
    Write-Host ""
    Melde "Probelauf - es wird nichts heruntergeladen und nichts installiert."
    Schreibe "Quelle          $Quelle/latest.json"
    Schreibe "Setup           $($manifest.url)"
    Schreibe "SHA-256         $($manifest.sha256)"
    Schreibe "Desktopsymbol   $(if ($Desktopverknuepfung) { 'ja' } else { 'nein' })"
    Write-Host ""
    exit 0
}

$arbeitsordner = Join-Path $env:TEMP "lernapp-install-$([guid]::NewGuid().ToString('N').Substring(0,8))"
New-Item -ItemType Directory -Path $arbeitsordner -Force | Out-Null
$setup = Join-Path $arbeitsordner "LernApp-Setup-$($manifest.version).exe"
$protokoll = Join-Path $arbeitsordner 'setup.log'

try {
    Melde "Setup-Datei laden ..."
    Lade-Datei $manifest.url $setup
    $mb = [math]::Round((Get-Item $setup).Length / 1MB, 1)
    Schreibe "$mb MB geladen"

    Melde "Pruefsumme vergleichen ..."
    Pruefe-Pruefsumme $setup $manifest.sha256
    Schreibe "SHA-256 stimmt"

    Melde "Installieren ..."
    # /VERYSILENT unterdrueckt den Assistenten, /SP- die Willkommensfrage,
    # /NOCANCEL verhindert einen Abbruch mitten im Kopieren.
    $argumente = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOCANCEL', '/SP-',
                   "/LOG=$protokoll")
    if ($Desktopverknuepfung) { $argumente += '/TASKS=desktopicon' }
    $lauf = Start-Process -FilePath $setup -ArgumentList $argumente -Wait -PassThru
    if ($lauf.ExitCode -ne 0) {
        # Das Inno-Protokoll ist die einzige Spur, wenn der stille Lauf
        # scheitert - deshalb aus dem Temp-Ordner herausretten, bevor
        # finally ihn loescht.
        $gerettet = Join-Path $env:TEMP 'lernapp-setup-fehler.log'
        if (Test-Path $protokoll) { Copy-Item $protokoll $gerettet -Force }
        Abbruch @"
Der Installer endete mit Code $($lauf.ExitCode).

Das Protokoll liegt unter:
  $gerettet

Bitte diese Datei an Lars schicken.
"@
    }
} finally {
    Remove-Item $arbeitsordner -Recurse -Force -ErrorAction SilentlyContinue
}

$jetzt = Vorhandene-Installation
if (-not $jetzt) { Abbruch "Nach der Installation ist kein Registry-Eintrag auffindbar." }
$ordner = $jetzt.InstallLocation
$exe = Join-Path $ordner 'LernApp.exe'

Write-Host ""
Gelungen "LernApp $($manifest.version) ist installiert."
Write-Host ""
Schreibe "Programm     $ordner"
Schreibe "Deine Daten  $(Join-Path $env:USERPROFILE '.lernapp')"
Schreibe "Start        Startmenue -> LernApp"
Write-Host ""

if (-not $NichtStarten -and (Test-Path $exe)) {
    Melde "Starten ..."
    Start-Process -FilePath $exe -WorkingDirectory $ordner
    Write-Host ""
}
