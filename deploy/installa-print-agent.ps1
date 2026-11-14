# Installa, aggiorna o rimuove il Local Print Agent come servizio Windows.
# Eseguire in PowerShell avviato come amministratore.
#
# Installazione:
#   .\deploy\installa-print-agent.ps1 -Url "https://app.example.com" -Token "<TOKEN>"
#
# Il token si ottiene una sola volta da POST /api/v1/dispositivi con un admin.
# Viene salvato in %ProgramData%\GestLab\print-agent.env, leggibile da SYSTEM
# e dagli amministratori. Lo script non lo ristampa.
#
# Rimozione:
#   .\deploy\installa-print-agent.ps1 -Rimuovi

param(
    [string]$Url,
    [string]$Token,
    [string]$Python,
    [string]$Progetto,
    [int]$Intervallo = 5,
    [switch]$Rimuovi
)

$ErrorActionPreference = "Stop"

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Error "Eseguire PowerShell come amministratore."
    exit 1
}

if (-not $Progetto) {
    $Progetto = Split-Path -Parent $PSScriptRoot
}
if (-not $Python) {
    $Python = Join-Path $Progetto "venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "Python non trovato: $Python"
    exit 1
}

$servizio = Join-Path $Progetto "saas\print_agent_servizio.py"
$nome = "GestLabPrintAgent"

if ($Rimuovi) {
    & $Python $servizio stop
    & $Python $servizio remove
    Write-Host "Servizio $nome rimosso."
    exit 0
}

if (-not $Url -or -not $Token) {
    Write-Error "Servono -Url e -Token. Il token è quello restituito alla creazione del dispositivo."
    exit 1
}
if ($Intervallo -le 0) {
    Write-Error "-Intervallo deve essere maggiore di zero."
    exit 1
}

$cartella = Join-Path $env:ProgramData "GestLab"
New-Item -ItemType Directory -Force -Path $cartella | Out-Null
$envPath = Join-Path $cartella "print-agent.env"
$contenuto = @(
    "GESTLAB_API_URL=$Url"
    "GESTLAB_AGENT_TOKEN=$Token"
    "GESTLAB_AGENT_INTERVAL=$Intervallo"
) -join "`r`n"
Set-Content -LiteralPath $envPath -Value $contenuto -Encoding utf8

$acl = Get-Acl -LiteralPath $envPath
$acl.SetAccessRuleProtection($true, $false)
$ereditarieta = [System.Security.AccessControl.InheritanceFlags]::None
$propagazione = [System.Security.AccessControl.PropagationFlags]::None
$tipo = [System.Security.AccessControl.AccessControlType]::Allow
$acl.SetAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule(
    "SYSTEM", "FullControl", $ereditarieta, $propagazione, $tipo)))
$acl.SetAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule(
    "Administrators", "FullControl", $ereditarieta, $propagazione, $tipo)))
Set-Acl -LiteralPath $envPath -AclObject $acl

& $Python -m pip install pywin32
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$postinstall = Join-Path (Split-Path -Parent (Split-Path -Parent $Python)) "Lib\site-packages\win32\scripts\pywin32_postinstall.py"
& $Python $postinstall -install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python $servizio --startup auto install
if ($LASTEXITCODE -ne 0) {
    & $Python $servizio --startup auto update
}
& sc.exe config $nome start= delayed-auto | Out-Host
& sc.exe failure $nome reset= 86400 actions= restart/5000/restart/5000/restart/5000 | Out-Host
$ambiente = Join-Path (Split-Path -Parent (Split-Path -Parent $Python)) "Lib\site-packages"
$pythonPath = @(
    $ambiente,
    (Join-Path $ambiente "win32"),
    (Join-Path $ambiente "win32\lib"),
    $Progetto
) -join ";"
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$nome" -Name Environment -PropertyType MultiString -Value @("PYTHONPATH=$pythonPath") -Force | Out-Null
& $Python $servizio start
Start-Sleep -Seconds 2
$stato = (Get-Service $nome).Status
if ($stato -ne "Running") {
    Write-Error "Il servizio $nome risulta $stato invece che in esecuzione."
    exit 1
}
Write-Host "Servizio $nome installato con avvio automatico ritardato."
Write-Host "Configurazione: $envPath"
Write-Host "Il token non viene mostrato. Al riavvio del PC il servizio riparte da solo."
