# start-all.ps1
# Starts all 3 CALLSUP backend services in separate windows.
# Run from any directory — paths are absolute.

$venv = "C:\Users\nyaga\Documents\.venv\Scripts\python.exe"
$root = "C:\Users\nyaga\Documents\callsup"

Write-Host "Starting CALLSUP services..." -ForegroundColor Cyan

# Write temporary launch scripts to avoid quoting issues
$llmScript = "$root\_launch_llm.ps1"
$audioScript = "$root\_launch_audio.ps1"
$ieScript = "$root\_launch_ie.ps1"

Set-Content -Path $llmScript -Value @"
Set-Location '$root\svc-llm-adapter'
& '$venv' -m uvicorn main:app --host 127.0.0.1 --port 9100
Read-Host 'Press Enter to close'
"@

Set-Content -Path $audioScript -Value @"
`$env:CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT = 'false'
`$env:CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP    = 'true'
`$env:CALLSUP_AUDIO_ENGINE_DATA_DIR               = 'data'
Set-Location '$root'
& '$venv' -m uvicorn 'app.main:create_app' --factory --host 127.0.0.1 --port 8010
Read-Host 'Press Enter to close'
"@

Set-Content -Path $ieScript -Value @"
`$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL = 'http://127.0.0.1:9100'
`$env:CALLSUP_INTELLIGENCE_ENGINE_MODEL           = 'gpt-4o'
`$env:PYTHONPATH                                  = 'src'
Set-Location '$root\consolidated\callsup-intelligence-engine'
& '$venv' -m uvicorn 'callsup_intelligence_engine.main:create_app' --factory --host 127.0.0.1 --port 8011
Read-Host 'Press Enter to close'
"@

# ── LLM Adapter · port 9100 ──────────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit -File `"$llmScript`"" -WindowStyle Normal

# ── Audio Engine · port 8010 ─────────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit -File `"$audioScript`"" -WindowStyle Normal

# ── Intelligence Engine · port 8011 ──────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit -File `"$ieScript`"" -WindowStyle Normal

Write-Host ""
Write-Host "3 windows launched. Wait ~5 seconds then run:" -ForegroundColor Yellow
Write-Host "  .\test-endpoints.ps1" -ForegroundColor Green
