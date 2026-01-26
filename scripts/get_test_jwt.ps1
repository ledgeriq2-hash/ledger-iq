param(
    [string]$BaseUrl,
    [string]$Email,
    [string]$Password,
    [string]$Tenant,
    [switch]$PrintExport
)

$ErrorActionPreference = "Stop"

function Mask-Token([string]$Token) {
    if (-not $Token) {
        return ""
    }
    if ($Token.Length -le 14) {
        return "***"
    }
    $prefix = $Token.Substring(0, 8)
    $suffix = $Token.Substring($Token.Length - 6, 6)
    return "$prefix...$suffix"
}

function Resolve-Value([string]$Explicit, [string[]]$EnvNames) {
    if ($Explicit) {
        return $Explicit
    }
    foreach ($name in $EnvNames) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value) {
            return $value
        }
    }
    return $null
}

$baseUrl = Resolve-Value $BaseUrl @("AI_BASE_URL", "BASE_URL", "AI_TEST_BASE_URL")
if (-not $baseUrl) {
    $baseUrl = "http://127.0.0.1:8000"
}
$baseUrl = $baseUrl.TrimEnd("/")

$email = Resolve-Value $Email @("LOGIN_EMAIL", "LEDGERIQ_ADMIN_EMAIL")
$password = Resolve-Value $Password @("LOGIN_PASSWORD", "LEDGERIQ_ADMIN_PASSWORD")
$tenant = Resolve-Value $Tenant @("LOGIN_TENANT", "TENANT_ID", "TENANT_SLUG")

if (-not $email -or -not $password -or -not $tenant) {
    Write-Error "Missing login input. Provide -Email/-Password/-Tenant or set LOGIN_EMAIL/LOGIN_PASSWORD/LOGIN_TENANT (or LEDGERIQ_ADMIN_EMAIL/LEDGERIQ_ADMIN_PASSWORD)."
    exit 1
}

$headers = @{ "Content-Type" = "application/json" }
if ($tenant -match '^[0-9a-fA-F-]{36}$') {
    $headers["X-Tenant-ID"] = $tenant
} else {
    $headers["X-Tenant-Slug"] = $tenant
}

$body = @{ email = $email; password = $password; tenant = $tenant } | ConvertTo-Json -Depth 4

$response = $null
try {
    $response = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" -Headers $headers -Body $body
} catch {
    $detail = ""
    if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $detail = $reader.ReadToEnd()
    }
    if ($detail -match "csrf_failed") {
        if ($tenant -notmatch '^[0-9a-fA-F-]{36}$') {
            Write-Error "csrf_failed detected. Provide a tenant UUID via -Tenant or TENANT_ID."
            exit 1
        }
        $cwd = Get-Location
        try {
            Set-Location -Path (Join-Path $cwd "backend")
            $issueOutput = & python -m app.management.issue_test_jwt --tenant-id $tenant --email $email --print-full 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Error "issue_test_jwt failed:"
                Write-Error $issueOutput
                exit 1
            }
        } finally {
            Set-Location -Path $cwd
        }

        $tokenMatch = [regex]::Match($issueOutput, '\$env:AI_TEST_JWT="([^"]+)"')
        $tenantMatch = [regex]::Match($issueOutput, '\$env:AI_TEST_TENANT_ID="([^"]+)"')
        if (-not $tokenMatch.Success) {
            Write-Error "Failed to parse AI_TEST_JWT from issue_test_jwt output."
            exit 1
        }
        $token = $tokenMatch.Groups[1].Value
        $env:AI_TEST_JWT = $token
        if ($tenantMatch.Success) {
            $env:AI_TEST_TENANT_ID = $tenantMatch.Groups[1].Value
        }
        $masked = Mask-Token $token
        Write-Host "AI_TEST_JWT set in current session (token=$masked)"
        if ($tenantMatch.Success) {
            Write-Host "AI_TEST_TENANT_ID set in current session ($($tenantMatch.Groups[1].Value))"
        }
        Write-Host "Next: run python verify_sprint16_ai_ingest.py"
        if ($PrintExport) {
            Write-Output "Set-Item Env:AI_TEST_JWT '$token'"
            if ($tenantMatch.Success) {
                Write-Output "Set-Item Env:AI_TEST_TENANT_ID '$($tenantMatch.Groups[1].Value)'"
            }
        }
        exit 0
    }

    Write-Error "Login failed: $($_.Exception.Message)"
    if ($detail) {
        Write-Error $detail
    }
    exit 1
}

$token = $null
if ($response -and $response.tokens -and $response.tokens.access_token) {
    $token = $response.tokens.access_token
} elseif ($response.access_token) {
    $token = $response.access_token
} elseif ($response.token) {
    $token = $response.token
} elseif ($response.jwt) {
    $token = $response.jwt
}

if (-not $token) {
    Write-Error "Login succeeded but no token field found in response."
    exit 1
}

$env:AI_TEST_JWT = $token
$masked = Mask-Token $token
Write-Host "AI_TEST_JWT set in current session (token=$masked)"

$tenantId = $null
if ($response -and $response.tenant -and $response.tenant.id) {
    $tenantId = $response.tenant.id
    $env:AI_TEST_TENANT_ID = $tenantId
    Write-Host "AI_TEST_TENANT_ID set in current session ($tenantId)"
} else {
    Write-Host "AI_TEST_TENANT_ID not found in login response. Use /api/v1/dev/tenants or DB query to locate it."
}

Write-Host "Next: run python verify_sprint16_ai_ingest.py"

$isDotSourced = $MyInvocation.InvocationName -eq '.'
if (-not $isDotSourced) {
    Write-Host "Tip: dot-source to persist: . .\scripts\get_test_jwt.ps1"
    if ($PrintExport) {
        Write-Output "Set-Item Env:AI_TEST_JWT '$token'"
        if ($tenantId) {
            Write-Output "Set-Item Env:AI_TEST_TENANT_ID '$tenantId'"
        }
    }
}
