# Shares Arthlane from this PC on a temporary public https://....trycloudflare.com link.
#   powershell -ExecutionPolicy Bypass -File deploy\share-from-pc.ps1
# Every page works for visitors. Account sign-in works once deploy\share.env has mail settings (see share.env.example).
# Keep the window open and the PC awake while sharing; press Ctrl+C to stop. The link changes on every start.

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot
$tools = Join-Path $env:USERPROFILE "tools"
$backend = Join-Path $root "arthlane-backend"
$jar = Join-Path $backend "target\arthlane-backend-0.1.0.jar"
$data = Join-Path $backend "data"
$logs = Join-Path $env:TEMP "arthlane-share"
New-Item -ItemType Directory -Force $data, $logs | Out-Null

function Listening($port) { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }

foreach ($port in 8767, 8790) { if (Listening $port) { throw "Port $port is already in use. Is another share window open?" } }
if (-not (Test-Path $jar)) { Push-Location $backend; & .\mvnw.cmd -q package -DskipTests; Pop-Location }

$secretFile = Join-Path $data "share-jwt-secret.txt"
if (-not (Test-Path $secretFile)) {
    $bytes = New-Object byte[] 48
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    [Convert]::ToBase64String($bytes) | Set-Content $secretFile
}

$settings = @{}
$settingsFile = Join-Path $PSScriptRoot "share.env"
if (Test-Path $settingsFile) {
    foreach ($line in Get-Content $settingsFile) { if ($line -match '^\s*([A-Z_]+)\s*=\s*(.+?)\s*$') { $settings[$Matches[1]] = $Matches[2] } }
}

$apiEnv = @{
    SPRING_PROFILES_ACTIVE = "prod"
    PORT                   = "8767"
    DATABASE_URL           = "jdbc:h2:file:" + ($data -replace '\\', '/') + "/public;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH"
    DATABASE_USER          = "sa"
    DATABASE_PASSWORD      = "arthlane-local"
    ARTHLANE_JWT_SECRET    = (Get-Content $secretFile -Raw).Trim()
    ARTHLANE_CORS_ORIGINS  = "https://arthlane.in"
    ARTHLANE_MAIL_FROM     = $(if ($settings.MAIL_FROM) { $settings.MAIL_FROM } else { "Arthlane <no-reply@localhost>" })
}
if ($settings.MAIL_HOST) {
    $apiEnv.SPRING_MAIL_HOST = $settings.MAIL_HOST
    $apiEnv.SPRING_MAIL_PORT = $(if ($settings.MAIL_PORT) { $settings.MAIL_PORT } else { "587" })
    $apiEnv.SPRING_MAIL_USERNAME = $settings.MAIL_USERNAME
    $apiEnv.SPRING_MAIL_PASSWORD = $settings.MAIL_PASSWORD
}

$caddyfile = Join-Path $logs "Caddyfile"
@"
{
	admin off
	auto_https off
	servers {
		trusted_proxies static private_ranges
	}
}

:8790 {
	bind 127.0.0.1
	import "$($PSScriptRoot -replace '\\', '/')/arthlane.caddy"
}
"@ | Set-Content $caddyfile -Encoding ascii

# Child processes inherit this window's environment, so each part's settings are set only while it starts.
function Start-Part($name, $file, $arguments, $environment = @{}, $directory = $root) {
    foreach ($key in $environment.Keys) { Set-Item "env:$key" $environment[$key] }
    try {
        Start-Process $file -ArgumentList $arguments -WorkingDirectory $directory -NoNewWindow -PassThru `
            -RedirectStandardOutput (Join-Path $logs "$name.log") -RedirectStandardError (Join-Path $logs "$name.err.log")
    }
    finally {
        foreach ($key in $environment.Keys) { Remove-Item "env:$key" -ErrorAction SilentlyContinue }
    }
}

$procs = @()
try {
    if (-not (Listening 8765)) {
        $procs += Start-Part "web" "python" "server.py" @{ PYTHONIOENCODING = "utf-8" } (Join-Path $root "market-oracle")
    }
    $procs += Start-Part "api" "java" @("-Xmx512m", "-jar", "`"$jar`"", "--server.address=127.0.0.1") $apiEnv
    $procs += Start-Part "caddy" (Join-Path $tools "caddy.exe") @("run", "--config", "`"$caddyfile`"", "--adapter", "caddyfile") `
        @{ WEB_UPSTREAM = "127.0.0.1:8765"; API_UPSTREAM = "127.0.0.1:8767" }

    Write-Host "Starting the account service..."
    for ($i = 0; $i -lt 120 -and -not (Listening 8767); $i++) {
        if ($procs | Where-Object HasExited) { throw "A part of the site failed to start. Logs are in $logs" }
        Start-Sleep 1
    }
    if (-not (Listening 8767)) { throw "The account service did not start. See $logs\api.log" }

    $procs += Start-Part "tunnel" (Join-Path $tools "cloudflared.exe") @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8790")
    $url = $null
    for ($i = 0; $i -lt 60 -and -not $url; $i++) {
        Start-Sleep 1
        $hit = Select-String -Path (Join-Path $logs "tunnel.err.log") -Pattern 'https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { $url = $hit.Matches[0].Value }
    }
    if (-not $url) { throw "Cloudflare did not give a link. See $logs\tunnel.err.log" }

    Write-Host ""
    Write-Host "Arthlane is public at  $url" -ForegroundColor Yellow
    Write-Host ("Account sign-in: " + $(if ($settings.MAIL_HOST) { "on (email codes)" } else { "off until deploy\share.env has mail settings" }))
    Write-Host "Keep this window open and the PC awake. Press Ctrl+C to stop sharing."
    while ($true) {
        Start-Sleep 5
        $stopped = $procs | Where-Object HasExited
        if ($stopped) { throw "A part of the site stopped. Logs are in $logs" }
    }
}
finally {
    $procs | Where-Object { -not $_.HasExited } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Stopped sharing."
}
