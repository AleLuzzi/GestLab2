<#
.SYNOPSIS
  Elimina l'istanza Lightsail di test e lo Static IP associato.

.EXAMPLE
  .\deploy\destroy-lightsail.ps1

.EXAMPLE
  .\deploy\destroy-lightsail.ps1 -Force
#>
[CmdletBinding()]
param(
    [string]$Region = "eu-central-1",
    [string]$InstanceName = "gestlab-test",
    [string]$StaticIpName = "",
    [switch]$Force,
    [switch]$DeleteKeyPair
)

$ErrorActionPreference = "Stop"
if (-not $StaticIpName) { $StaticIpName = "$InstanceName-ip" }
$KeyPairName = "$InstanceName-key"

function Invoke-AwsAllowFail {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
    $output = & aws @AwsArgs --region $Region --output json 2>&1
    return @{ Code = $LASTEXITCODE; Output = $output }
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI non trovato."
}

if (-not $Force) {
    $msg = "Questa operazione elimina l'istanza '$InstanceName' e lo Static IP '$StaticIpName' nella regione $Region. Continuare? [s/N]"
    $answer = Read-Host $msg
    if ($answer -notin @("s", "S", "y", "Y")) {
        Write-Host "Annullato."
        exit 0
    }
}

Write-Host "Eliminazione istanza $InstanceName ..."
$r = Invoke-AwsAllowFail lightsail delete-instance --instance-name $InstanceName
if ($r.Code -ne 0) { Write-Warning "delete-instance: $($r.Output)" } else { Write-Host "Istanza eliminata (operazione avviata)." }

Start-Sleep -Seconds 3

Write-Host "Rilascio Static IP $StaticIpName ..."
$r = Invoke-AwsAllowFail lightsail release-static-ip --static-ip-name $StaticIpName
if ($r.Code -ne 0) { Write-Warning "release-static-ip: $($r.Output)" } else { Write-Host "Static IP rilasciato." }

if ($DeleteKeyPair) {
    Write-Host "Eliminazione key pair $KeyPairName ..."
    $r = Invoke-AwsAllowFail lightsail delete-key-pair --key-pair-name $KeyPairName
    if ($r.Code -ne 0) { Write-Warning "delete-key-pair: $($r.Output)" }
}

Write-Host "Controllare Billing e Cost Explorer dopo qualche ora."
Write-Host "Eventuali snapshot e record DNS vanno rimossi a mano."
