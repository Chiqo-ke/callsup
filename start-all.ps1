# start-all.ps1
# Starts all CALLSUP backend services in separate windows.
# Run from any directory — paths are absolute.
#
# Architecture:
#   port 9100  — LLM Adapter (internal only, called by the gateway)
#   port 8010  — Unified Gateway (Audio Engine + Intelligence Engine combined)
#                Frontend Vite proxy routes everything here.

$venv = "C:\Users\nyaga\Documents\.venv\Scripts\python.exe"
$root = "C:\Users\nyaga\Documents\callsup"

Write-Host "Starting CALLSUP services..." -ForegroundColor Cyan

# Write temporary launch scripts to avoid quoting issues
$llmScript     = "$root\_launch_llm.ps1"
$gatewayScript = "$root\_launch_gateway.ps1"

Set-Content -Path $llmScript -Value @"
Set-Location '$root\svc-llm-adapter'
& '$venv' -m uvicorn main:app --host 127.0.0.1 --port 9100
Read-Host 'Press Enter to close'
"@

Set-Content -Path $gatewayScript -Value @"
# Load .env from project root so OPENAI_API_KEY and RapidAPI keys are available
`$envFile = '$root\.env'
if (Test-Path `$envFile) {
    Get-Content `$envFile | ForEach-Object {
        if (`$_ -match '^([^#\s][^=]*)=(.*)`$') {
            [System.Environment]::SetEnvironmentVariable(`$matches[1].Trim(), `$matches[2].Trim())
        }
    }
}
`$env:CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT = 'false'
`$env:CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP    = 'true'
`$env:CALLSUP_AUDIO_ENGINE_DATA_DIR               = 'data'
`$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL = 'http://127.0.0.1:9100'
`$env:CALLSUP_INTELLIGENCE_ENGINE_MODEL           = 'gpt-4o'
# Add the Intelligence Engine package to the Python path
`$env:PYTHONPATH = 'consolidated\callsup-intelligence-engine\src'
Set-Location '$root'
& '$venv' -m uvicorn 'gateway:create_app' --factory --host 127.0.0.1 --port 8010
Read-Host 'Press Enter to close'
"@

# ── LLM Adapter · port 9100 ──────────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit -File `"$llmScript`"" -WindowStyle Normal

# ── Unified Gateway · port 8010 ──────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit -File `"$gatewayScript`"" -WindowStyle Normal

Write-Host ""
Write-Host "2 windows launched. Wait ~5 seconds then run:" -ForegroundColor Yellow
Write-Host "  .\test-endpoints.ps1" -ForegroundColor Green
