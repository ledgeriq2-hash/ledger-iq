param(
    [string]$Container,
    [string]$Database,
    [string]$User,
    [string]$BackupDir = "backups"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $root

try {
    if (-not $Container) {
        $Container = $env:POSTGRES_CONTAINER
    }

    if (-not $Container) {
        $containerId = (docker compose ps -q postgres 2>$null)
        if ($containerId) {
            $Container = $containerId.Trim()
        }
    }

    if (-not $Container) {
        $Container = "ledgeriq-postgres-1"
    }

    if (-not $Database) {
        $Database = $env:POSTGRES_DB
    }
    if (-not $Database) {
        $Database = "ledgeriq"
    }

    if (-not $User) {
        $User = $env:POSTGRES_USER
    }
    if (-not $User) {
        $User = "postgres"
    }

    $backupPath = Join-Path $root $BackupDir
    if (-not (Test-Path $backupPath)) {
        New-Item -ItemType Directory -Path $backupPath | Out-Null
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $fileName = "ledgeriq_${timestamp}.sql"
    $fullPath = Join-Path $backupPath $fileName

    Write-Host "Creating backup for '$Database' from container '$Container'..."
    docker exec -i $Container pg_dump -U $User -d $Database | Set-Content -Path $fullPath -Encoding utf8

    Write-Host "Backup created at $fullPath"
}
finally {
    Pop-Location
}
