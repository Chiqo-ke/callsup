# Load .env from project root so OPENAI_API_KEY and RapidAPI keys are available
$envFile = 'C:\Users\nyaga\Documents\callsup\.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#\s][^=]*)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
}
$env:CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT = 'false'
$env:CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP    = 'true'
$env:CALLSUP_AUDIO_ENGINE_DATA_DIR               = 'data'
Set-Location 'C:\Users\nyaga\Documents\callsup'
& 'C:\Users\nyaga\Documents\.venv\Scripts\python.exe' -m uvicorn 'app.main:create_app' --factory --host 127.0.0.1 --port 8010
Read-Host 'Press Enter to close'
