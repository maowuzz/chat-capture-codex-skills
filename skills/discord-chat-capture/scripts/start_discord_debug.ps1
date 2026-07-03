param(
    [int]$Port = 9333,
    [switch]$Restart
)

$ErrorActionPreference = 'Stop'
$base = Join-Path $env:LOCALAPPDATA 'Discord'
$exe = Get-ChildItem -Path $base -Directory -Filter 'app-*' -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    ForEach-Object { Join-Path $_.FullName 'Discord.exe' } |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

if (-not $exe) {
    throw "Discord.exe was not found under $base"
}

$running = Get-Process Discord -ErrorAction SilentlyContinue
if ($running -and -not $Restart) {
    Write-Output 'Discord is already running. Use -Restart to relaunch it with the debug port.'
    exit 2
}
if ($running) {
    $running | Stop-Process -Force
    Start-Sleep -Seconds 2
}

Start-Process -FilePath $exe -ArgumentList @(
    "--remote-debugging-port=$Port",
    '--remote-allow-origins=*'
)

$endpoint = "http://127.0.0.1:$Port/json/list"
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $targets = Invoke-RestMethod -Uri $endpoint -TimeoutSec 2
        Write-Output "Discord debug endpoint is ready: $endpoint (targets=$(@($targets).Count))"
        exit 0
    } catch {
        # Discord may still be applying an update or opening its renderer.
    }
}
throw "Discord started, but the debug endpoint did not become ready: $endpoint"

