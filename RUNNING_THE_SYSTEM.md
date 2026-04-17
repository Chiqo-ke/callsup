# Running CALLSUP Locally

## Prerequisites

- Python venv at `C:\Users\nyaga\Documents\.venv`
- Credentials in `C:\Users\nyaga\Documents\callsup\.env` (your `OPENAI_API_KEY`)
- GitHub Copilot session at `C:\Users\nyaga\Documents\callsup\.copilot_session`

If you have not authenticated Copilot yet:
```powershell
Set-Location "C:\Users\nyaga\Documents\callsup"
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" auth_github_copilot.py
```
Follow the on-screen instructions — enter the displayed code at https://github.com/login/device.

---

## Starting the System

Open **3 separate terminal windows** and run one command per window.

### Terminal 1 — LLM Adapter (GitHub Copilot backend) · port 9100

```powershell
Set-Location "C:\Users\nyaga\Documents\callsup\svc-llm-adapter"
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 9100
```

Wait for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:9100
```

---

### Terminal 2 — Audio Engine (Whisper transcription) · port 8010

```powershell
$env:CALLSUP_AUDIO_ENGINE_ENFORCE_TLS_IN_TRANSIT = "false"
$env:CALLSUP_AUDIO_ENGINE_ALLOW_INSECURE_HTTP    = "true"
$env:CALLSUP_AUDIO_ENGINE_DATA_DIR               = "data"
Set-Location "C:\Users\nyaga\Documents\callsup"
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" -m uvicorn "app.main:create_app" --factory --host 127.0.0.1 --port 8010
```

Wait for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8010
```

---

### Terminal 3 — Intelligence Engine (call analysis) · port 8011

```powershell
$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL = "http://127.0.0.1:9100"
$env:CALLSUP_INTELLIGENCE_ENGINE_MODEL           = "gpt-4o"
$env:PYTHONPATH                                  = "src"
Set-Location "C:\Users\nyaga\Documents\callsup\consolidated\callsup-intelligence-engine"
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" -m uvicorn "callsup_intelligence_engine.main:create_app" --factory --host 127.0.0.1 --port 8011
```

Wait for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8011
```

---

### Terminal 4 — Web Dashboard (optional) · http://localhost:5173

```powershell
Set-Location "C:\Users\nyaga\Documents\callsup\callsup-web"
npm install   # first time only
npm run dev
```

Wait for:
```
  VITE v6.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

#### Dashboard at a glance

- **Stats row** — Tickets Pending, Resolved Today, Total Escalations, Services Online (X/3)
- **Service health cards** — shows name, status (online/offline), and version. Raw URLs are not displayed.
- **Task Queue** — escalation tickets raised by the Intelligence Engine or Call Simulation that need human review. Click **Resolve** to close a ticket.
- Tickets are stored in browser `localStorage` (`callsup_tickets`) and persist across page refreshes.

---

## Verifying All Services Are Up

Run this in any terminal once all three are started:

```powershell
@(9100, 8010, 8011) | ForEach-Object {
    try   { $r = Invoke-RestMethod "http://127.0.0.1:$_/health" -TimeoutSec 3; Write-Host "OK :$_  $($r | ConvertTo-Json -Compress)" }
    catch { Write-Host "DOWN :$_" }
}
```

Expected output:
```
OK :9100  {"status":"ok","backend":"github-copilot","authenticated":true}
OK :8010  {"status":"ok","version":"0.1.0"}
OK :8011  {"status":"ok","version":"0.1.0"}
```

> If `"authenticated": false` on :9100, re-run `auth_github_copilot.py`.

---

## Interactive API Docs (Test Manually in Browser)

| Service | URL |
|---------|-----|
| Audio Engine | http://127.0.0.1:8010/docs |
| Intelligence Engine | http://127.0.0.1:8011/docs |
| LLM Adapter | http://127.0.0.1:9100/docs |

The `/docs` pages provide a full interactive UI — no code needed to test endpoints.

---

## Automated Smoke Test

Runs the full call-centre business scenario end to end:

```powershell
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" "C:\Users\nyaga\Documents\callsup\smoke_test.py"
```

What it tests:
1. Health check on all 3 services
2. Direct LLM generate call through Copilot
3. Audio ingest with PII in the payload
4. Transcript retrieval — verifies PII was redacted
5. Intelligence `e2e-demo` — full pipeline (ingest → ASR → NLU → action → summary)
6. Intelligence `step` — single segment intent detection

---

## Troubleshooting

### Port already in use

If you see `[WinError 10048] only one usage of each socket address`:

```powershell
# Replace 9100 with whichever port is blocked (8010 or 8011)
$p = (netstat -ano | Select-String ":9100\s.*LISTENING" | ForEach-Object { ($_ -split "\s+")[-1] } | Select-Object -First 1)
Stop-Process -Id $p -Force
```

Then re-run the service command.

### Copilot token expired

Copilot tokens last ~30 minutes. The adapter auto-refreshes using the saved OAuth token.
If refresh fails (e.g. you revoked access), re-run:

```powershell
Set-Location "C:\Users\nyaga\Documents\callsup"
& "C:\Users\nyaga\Documents\.venv\Scripts\python.exe" auth_github_copilot.py
```

### Whisper not transcribing real audio

Check your `OPENAI_API_KEY` in `C:\Users\nyaga\Documents\callsup\.env`:
```
OPENAI_API_KEY=sk-your-real-key-here
```
If the key starts with `sk-replace-me`, Whisper falls back to the mock transcriber.

### Intelligence Engine cannot reach LLM Adapter

Ensure Terminal 1 (port 9100) is running **before** starting Terminal 3.
The `$env:CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL` must be set in the same terminal session as the Intelligence Engine.

---

## Stopping the System

Press `Ctrl+C` in each of the three terminal windows.
