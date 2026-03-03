# ─────────────────────────────────────────────────────────────
#  CALLSUP  —  Start all services
#  Run from anywhere:
#      C:\Users\nyaga\Documents\callsup\start.ps1
# ─────────────────────────────────────────────────────────────

$ROOT   = "C:\Users\nyaga\Documents\callsup"
$PYTHON = "C:\Users\nyaga\Documents\.venv\Scripts\python.exe"

$PORTS  = @(9100, 8010, 8011)
$SERVICES = @(
    @{ name = "LLM Adapter  "; port = 9100; dir = "$ROOT\svc-llm-adapter";                                    args = "-m uvicorn main:app --host 127.0.0.1 --port 9100" },
    @{ name = "Audio Engine "; port = 8010; dir = "$ROOT";                                                     args = "-m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010" },
    @{ name = "Intel Engine "; port = 8011; dir = "$ROOT\consolidated\callsup-intelligence-engine";            args = "-m uvicorn callsup_intelligence_engine.main:create_app --factory --host 127.0.0.1 --port 8011" }
)

Write-Host ""
Write-Host "  CALLSUP — Starting all services" -ForegroundColor Cyan
Write-Host ""

# ── 1. Free ports ─────────────────────────────────────────────
Write-Host "  Freeing ports..." -ForegroundColor Yellow
foreach ($port in $PORTS) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "    killed PID $($conn.OwningProcess) on :$port"
    }
}
Start-Sleep -Seconds 1

# ── 2. Set environment ────────────────────────────────────────
$env:CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT = "false"
$env:CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP    = "true"
$env:CALLSUP_AUDIO_ENGINE_DATA_DIR               = "data"
$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL = "http://127.0.0.1:9100"
$env:CALLSUP_INTELLIGENCE_ENGINE_MODEL           = "gpt-4o"

# Pick up OPENAI_API_KEY from .env
if (Test-Path "$ROOT\.env") {
    Get-Content "$ROOT\.env" | Where-Object { $_ -match "^OPENAI_API_KEY=.+" } | ForEach-Object {
        $val = ($_ -split "=", 2)[1]
        $env:OPENAI_API_KEY = $val
    }
}

# ── 3. Launch each service in its own window ──────────────────
Write-Host ""
Write-Host "  Starting services..." -ForegroundColor Yellow
foreach ($svc in $SERVICES) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName  = "powershell.exe"
    $psi.Arguments = "-NoExit -Command `"Set-Location '$($svc.dir)'; `$env:CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT='false'; `$env:CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP='true'; `$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL='http://127.0.0.1:9100'; `$env:PYTHONPATH='src'; & '$PYTHON' $($svc.args)`""
    $psi.WorkingDirectory = $svc.dir
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Write-Host "    $($svc.name)  :$($svc.port)  started"
}

# ── 4. Wait for all three to be ready ────────────────────────
Write-Host ""
Write-Host "  Waiting for services to be ready..." -ForegroundColor Yellow
$ready = @{}
$deadline = (Get-Date).AddSeconds(30)
while ($ready.Count -lt 3 -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    foreach ($svc in $SERVICES) {
        if (-not $ready[$svc.port]) {
            try {
                $r = Invoke-RestMethod "http://127.0.0.1:$($svc.port)/health" -TimeoutSec 2 -ErrorAction Stop
                $ready[$svc.port] = $true
            } catch {}
        }
    }
}

# ── 5. Status summary ─────────────────────────────────────────
Write-Host ""
Write-Host "  -------------------------------------------------" -ForegroundColor DarkGray
foreach ($svc in $SERVICES) {
    if ($ready[$svc.port]) {
        Write-Host "  [UP]  $($svc.name)  http://127.0.0.1:$($svc.port)" -ForegroundColor Green
    } else {
        Write-Host "  [??]  $($svc.name)  http://127.0.0.1:$($svc.port)  (may still be starting)" -ForegroundColor Red
    }
}
Write-Host "  -------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  API docs (open in browser):" -ForegroundColor Cyan
Write-Host "    Audio Engine    ->  http://127.0.0.1:8010/docs"
Write-Host "    Intel Engine    ->  http://127.0.0.1:8011/docs"
Write-Host "    LLM Adapter     ->  http://127.0.0.1:9100/docs"
Write-Host ""
Write-Host "  Run smoke test:" -ForegroundColor Cyan
Write-Host "    $PYTHON $ROOT\smoke_test.py"
Write-Host ""
