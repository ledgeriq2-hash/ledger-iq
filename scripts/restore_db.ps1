param(
    [Parameter(Mandatory = $true)][string]$InputFile,
    [string]$Container,
    [string]$Database,
    [string]$User
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $InputFile)) {
    throw "Backup file not found: $InputFile"
}

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

    Write-Host "Restoring '$Database' into container '$Container' from $InputFile..."
    Get-Content -Raw $InputFile | docker exec -i $Container psql -v ON_ERROR_STOP=1 -U $User -d $Database

    Write-Host "Restore completed."
}
finally {
    Pop-Location
}
