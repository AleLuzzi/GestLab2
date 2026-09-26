<#
.SYNOPSIS
  Crea (se manca) un'istanza Amazon Lightsail e pubblica GestLab SaaS.

.DESCRIPTION
  Orchestrazione da Windows: AWS CLI + SSH/SCP.
  I segreti restano in deploy/gestlab.env (non committare).

.EXAMPLE
  .\deploy\publish-lightsail.ps1 -AdminEmail "tu@example.com"

.EXAMPLE
  .\deploy\publish-lightsail.ps1 -Source Git -GitRef main -Domain gestlab.example.com -Https
#>
[CmdletBinding()]
param(
    [string]$Region = "eu-west-3",
    [string]$InstanceName = "gestlab-test",
    [string]$StaticIpName = "",
    [string]$BundleId = "nano_3_0",
    [string]$BlueprintId = "ubuntu_24_04",
    [string]$AvailabilityZone = "",
    [string]$KeyPairName = "",
    [string]$KeyPemPath = "",
    [ValidateSet("Local", "Git")]
    [string]$Source = "Local",
    [string]$GitRepo = "https://github.com/AleLuzzi/GestLab2.git",
    [string]$GitRef = "main",
    [string]$EnvFile = "",
    [string]$AdminEmail = "",
    [string]$AdminPassword = "",
    [string]$TenantNome = "Laboratorio Test AWS",
    [string]$Domain = "",
    [switch]$Https,
    [switch]$SkipCreate,
    [switch]$UpdateOnly,
    [int]$SshTimeoutSec = 420
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $StaticIpName) { $StaticIpName = "$InstanceName-ip" }
if (-not $KeyPairName) { $KeyPairName = "$InstanceName-key" }
if (-not $EnvFile) { $EnvFile = Join-Path $PSScriptRoot "gestlab.env" }
if (-not $KeyPemPath) { $KeyPemPath = Join-Path $PSScriptRoot "$KeyPairName.pem" }

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando non trovato: $Name. Installarlo e riprovare."
    }
}

function Invoke-Aws {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
    $output = & aws @AwsArgs --region $Region --output json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI non riuscito: aws $($AwsArgs -join ' ')`n$output"
    }
    if ($output) {
        return ($output | Out-String | ConvertFrom-Json)
    }
    return $null
}

function Get-AwsText {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
    $output = & aws @AwsArgs --region $Region --output text 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI non riuscito: aws $($AwsArgs -join ' ')`n$output"
    }
    return [string]$output
}

function New-RandomSecret {
    param([int]$Bytes = 36)
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return [Convert]::ToBase64String($buffer).TrimEnd("=")
}

function Protect-PrivateKeyFile {
    param([string]$Path)
    icacls $Path /inheritance:r | Out-Null
    icacls $Path /grant:r "$($env:USERNAME):(R)" | Out-Null
}

function Get-EnvMap {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $idx = $line.IndexOf("=")
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        $map[$key] = $val
    }
    return $map
}

function Write-EnvFile {
    param([string]$Path, [hashtable]$Map)
    $lines = @(
        "DB_HOST=$($Map.DB_HOST)",
        "DB_PORT=$($Map.DB_PORT)",
        "DB_NAME=$($Map.DB_NAME)",
        "DB_USER=$($Map.DB_USER)",
        "DB_PWD=$($Map.DB_PWD)",
        "JWT_SECRET=$($Map.JWT_SECRET)",
        "GESTLAB_ADMIN_EMAIL=$($Map.GESTLAB_ADMIN_EMAIL)",
        "GESTLAB_ADMIN_PASSWORD=$($Map.GESTLAB_ADMIN_PASSWORD)",
        "GESTLAB_TENANT_NOME=$($Map.GESTLAB_TENANT_NOME)"
    )
    if ($Map.ContainsKey("LETSENCRYPT_EMAIL") -and $Map.LETSENCRYPT_EMAIL) {
        $lines += "LETSENCRYPT_EMAIL=$($Map.LETSENCRYPT_EMAIL)"
    }
    Set-Content -Path $Path -Value $lines -Encoding ascii
}

function Invoke-Remote {
    param(
        [string]$Ip,
        [string]$RemoteCommand
    )
    & ssh -i $KeyPemPath -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes -o ConnectTimeout=10 `
        "ubuntu@$Ip" $RemoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "SSH non riuscito su ubuntu@${Ip}"
    }
}

function Copy-ToRemote {
    param(
        [string]$Ip,
        [string]$LocalPath,
        [string]$RemotePath
    )
    & scp -i $KeyPemPath -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes `
        $LocalPath "ubuntu@${Ip}:$RemotePath"
    if ($LASTEXITCODE -ne 0) {
        throw "SCP non riuscito: $LocalPath -> ubuntu@${Ip}:$RemotePath"
    }
}

function Wait-Ssh {
    param([string]$Ip)
    $deadline = (Get-Date).AddSeconds($SshTimeoutSec)
    do {
        & ssh -i $KeyPemPath -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes -o ConnectTimeout=8 `
            "ubuntu@$Ip" "echo ok" 2>$null
        if ($LASTEXITCODE -eq 0) { return }
        Write-Host "In attesa di SSH su $Ip ..."
        Start-Sleep -Seconds 10
    } while ((Get-Date) -lt $deadline)
    throw "Timeout SSH verso $Ip"
}

Assert-Command aws
Assert-Command ssh
Assert-Command scp
Assert-Command tar

Write-Host "Regione: $Region"
Write-Host "Istanza: $InstanceName"
Write-Host "Sorgente codice: $Source"

$envMap = Get-EnvMap $EnvFile
if (-not $envMap.ContainsKey("DB_HOST") -or -not $envMap.DB_HOST) { $envMap.DB_HOST = "127.0.0.1" }
if (-not $envMap.ContainsKey("DB_PORT") -or -not $envMap.DB_PORT) { $envMap.DB_PORT = "3306" }
if (-not $envMap.ContainsKey("DB_NAME") -or -not $envMap.DB_NAME) { $envMap.DB_NAME = "gestlab" }
if (-not $envMap.ContainsKey("DB_USER") -or -not $envMap.DB_USER) { $envMap.DB_USER = "gestlab_app" }
if (-not $envMap.ContainsKey("DB_PWD") -or -not $envMap.DB_PWD) { $envMap.DB_PWD = New-RandomSecret }
if (-not $envMap.ContainsKey("JWT_SECRET") -or -not $envMap.JWT_SECRET) { $envMap.JWT_SECRET = New-RandomSecret -Bytes 48 }
if ($AdminEmail) { $envMap.GESTLAB_ADMIN_EMAIL = $AdminEmail }
if ($AdminPassword) { $envMap.GESTLAB_ADMIN_PASSWORD = $AdminPassword }
if ($TenantNome) { $envMap.GESTLAB_TENANT_NOME = $TenantNome }
if (-not $envMap.ContainsKey("GESTLAB_ADMIN_EMAIL") -or -not $envMap.GESTLAB_ADMIN_EMAIL) {
    throw "Specificare -AdminEmail oppure GESTLAB_ADMIN_EMAIL in $EnvFile"
}
if (-not $envMap.ContainsKey("GESTLAB_ADMIN_PASSWORD") -or -not $envMap.GESTLAB_ADMIN_PASSWORD) {
    $envMap.GESTLAB_ADMIN_PASSWORD = New-RandomSecret -Bytes 18
}
if ($Domain) {
    $envMap.LETSENCRYPT_EMAIL = $envMap.GESTLAB_ADMIN_EMAIL
}
Write-EnvFile -Path $EnvFile -Map $envMap
Write-Host "File env aggiornato: $EnvFile"

$instanceExists = $false
try {
    $null = Invoke-Aws lightsail get-instance --instance-name $InstanceName
    $instanceExists = $true
} catch {
    $instanceExists = $false
}

if ($UpdateOnly -and -not $instanceExists) {
    throw "Istanza $InstanceName non trovata. Eseguire prima un deploy completo."
}

if (-not $SkipCreate -and -not $UpdateOnly -and -not $instanceExists) {
    if (-not $AvailabilityZone) {
        $AvailabilityZone = (Get-AwsText lightsail get-regions --include-availability-zones `
            --query "regions[?name=='$Region'].availabilityZones[0].zoneName").Trim()
        if (-not $AvailabilityZone) {
            throw "Impossibile determinare la zona di disponibilita' per $Region"
        }
    }

    $keyExists = $false
    try {
        $null = Invoke-Aws lightsail get-key-pair --key-pair-name $KeyPairName
        $keyExists = $true
    } catch {
        $keyExists = $false
    }

    if (-not $keyExists) {
        Write-Host "Creazione key pair Lightsail: $KeyPairName"
        $kp = Invoke-Aws lightsail create-key-pair --key-pair-name $KeyPairName
        $pem = [string]$kp.privateKeyBase64
        if (-not $pem) { throw "create-key-pair non ha restituito privateKeyBase64" }
        if ($pem -match "BEGIN ") {
            $pemText = $pem
        } else {
            $pemText = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($pem))
        }
        Set-Content -Path $KeyPemPath -Value $pemText -Encoding ascii
        Protect-PrivateKeyFile $KeyPemPath
        Write-Host "Chiave privata salvata in $KeyPemPath"
    } elseif (-not (Test-Path $KeyPemPath)) {
        throw "La key pair $KeyPairName esiste gia' ma manca il file $KeyPemPath. Specificare -KeyPemPath."
    } else {
        Protect-PrivateKeyFile $KeyPemPath
    }

    Write-Host "Creazione istanza Lightsail (blueprint $BlueprintId, bundle $BundleId, AZ $AvailabilityZone)"
    try {
        $null = Invoke-Aws lightsail create-instances `
            --instance-names $InstanceName `
            --availability-zone $AvailabilityZone `
            --blueprint-id $BlueprintId `
            --bundle-id $BundleId `
            --key-pair-name $KeyPairName
    } catch {
        Write-Host $_
        Write-Host "Elenca blueprint e bundle validi con:"
        Write-Host "  aws lightsail get-blueprints --region $Region --query blueprints[].blueprintId --output text"
        Write-Host "  aws lightsail get-bundles --region $Region --query bundles[].bundleId --output text"
        throw
    }

    Write-Host "Attesa stato running..."
    $deadline = (Get-Date).AddMinutes(8)
    do {
        Start-Sleep -Seconds 8
        $state = (Get-AwsText lightsail get-instance-state --instance-name $InstanceName --query state.name).Trim()
        Write-Host "  stato: $state"
    } while ($state -ne "running" -and (Get-Date) -lt $deadline)
    if ($state -ne "running") { throw "Istanza non in running (stato: $state)" }

    $ipExists = $false
    try {
        $null = Invoke-Aws lightsail get-static-ip --static-ip-name $StaticIpName
        $ipExists = $true
    } catch {
        $ipExists = $false
    }
    if (-not $ipExists) {
        Write-Host "Allocazione Static IP: $StaticIpName"
        $null = Invoke-Aws lightsail allocate-static-ip --static-ip-name $StaticIpName
    }
    $null = Invoke-Aws lightsail attach-static-ip --static-ip-name $StaticIpName --instance-name $InstanceName

    $null = Invoke-Aws lightsail open-instance-public-ports `
        --instance-name $InstanceName `
        --port-info fromPort=80,toPort=80,protocol=TCP
    $null = Invoke-Aws lightsail open-instance-public-ports `
        --instance-name $InstanceName `
        --port-info fromPort=443,toPort=443,protocol=TCP
} else {
    if (-not (Test-Path $KeyPemPath)) {
        throw "File chiave SSH non trovato: $KeyPemPath"
    }
    Protect-PrivateKeyFile $KeyPemPath
}

$publicIp = $null
try {
    $publicIp = (Get-AwsText lightsail get-static-ip --static-ip-name $StaticIpName --query staticIp.ipAddress).Trim()
} catch {
    $publicIp = $null
}
if (-not $publicIp) {
    $publicIp = (Get-AwsText lightsail get-instance --instance-name $InstanceName --query instance.publicIpAddress).Trim()
}
if (-not $publicIp) { throw "Impossibile ottenere l'IP pubblico dell'istanza." }
Write-Host "IP pubblico: $publicIp"

Wait-Ssh -Ip $publicIp

$bundlePath = Join-Path $env:TEMP "gestlab-src.tgz"
if ($Source -eq "Local") {
    Write-Host "Creazione archivio del workspace locale..."
    if (Test-Path $bundlePath) { Remove-Item $bundlePath -Force }
    Push-Location $RepoRoot
    try {
        & tar -czf $bundlePath `
            --exclude=venv --exclude=.venv --exclude=__pycache__ --exclude=.env `
            --exclude=config.ini --exclude=deploy/gestlab.env --exclude="*.pem" `
            --exclude=deploy/*.tgz --exclude=.git `
            -C $RepoRoot .
        if ($LASTEXITCODE -ne 0) { throw "Creazione archivio tar non riuscita" }
    } finally {
        Pop-Location
    }
    Copy-ToRemote -Ip $publicIp -LocalPath $bundlePath -RemotePath "/tmp/gestlab-src.tgz"
}

Copy-ToRemote -Ip $publicIp -LocalPath (Join-Path $PSScriptRoot "setup-server.sh") -RemotePath "/tmp/setup-server.sh"
Copy-ToRemote -Ip $publicIp -LocalPath (Join-Path $PSScriptRoot "update-server.sh") -RemotePath "/tmp/update-server.sh"
Copy-ToRemote -Ip $publicIp -LocalPath $EnvFile -RemotePath "/tmp/gestlab.env"
Invoke-Remote -Ip $publicIp -RemoteCommand "chmod 600 /tmp/gestlab.env && chmod 755 /tmp/setup-server.sh /tmp/update-server.sh"

$serverName = if ($Domain) { $Domain } else { $publicIp }
$httpsArg = ""
if ($Https) {
    if (-not $Domain) { throw "-Https richiede -Domain" }
    $httpsArg = "--https"
}

if ($UpdateOnly) {
    $sourceArg = if ($Source -eq "Local") { "local" } else { "git" }
    $cmd = "sudo bash /tmp/update-server.sh --source $sourceArg --ref $GitRef --bundle /tmp/gestlab-src.tgz"
    Write-Host "Aggiornamento applicazione..."
    Invoke-Remote -Ip $publicIp -RemoteCommand $cmd
} else {
    $sourceArg = if ($Source -eq "Local") { "local" } else { "git" }
    $cmd = "sudo bash /tmp/setup-server.sh --source $sourceArg --repo `"$GitRepo`" --ref $GitRef --bundle /tmp/gestlab-src.tgz --server-name $serverName --env-src /tmp/gestlab.env $httpsArg"
    Write-Host "Esecuzione setup sul server (puo' richiedere diversi minuti)..."
    Invoke-Remote -Ip $publicIp -RemoteCommand $cmd
}

$healthUrl = if ($Https -and $Domain) { "https://$Domain/health" } else { "http://$publicIp/health" }
Write-Host "Verifica $healthUrl"
try {
    $health = Invoke-RestMethod -Uri $healthUrl -Method Get
    Write-Host ($health | ConvertTo-Json -Compress)
} catch {
    Write-Warning "Health check HTTP non riuscito: $_"
}

Write-Host ""
Write-Host "Deploy terminato."
Write-Host "  Console:  http://$publicIp/"
if ($Domain) { Write-Host "  Dominio:  http://$Domain/" }
Write-Host "  Swagger:  http://$publicIp/docs"
Write-Host "  Admin:    $($envMap.GESTLAB_ADMIN_EMAIL)"
Write-Host "  Segreti:  $EnvFile"
Write-Host "Non committare $EnvFile ne' $KeyPemPath."
