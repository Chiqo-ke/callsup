# test-intelligence.ps1
# Tests the intelligence engine with simulated transcribed speech.
# Run AFTER start-all.ps1 and all 3 services show "Uvicorn running on..."

$ieUrl    = "http://127.0.0.1:8011"
$llmUrl   = "http://127.0.0.1:9100"
$audioUrl = "http://127.0.0.1:8010"

function Write-Section($title) {
    Write-Host ""
    Write-Host "══════════════════════════════════════════" -ForegroundColor DarkCyan
    Write-Host " $title" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════════" -ForegroundColor DarkCyan
}

function Test-Health($url, $name) {
    try {
        $r = Invoke-RestMethod "$url/health" -Method GET -TimeoutSec 5
        Write-Host "  [OK] $name health: $($r.status)  v$($r.version)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [FAIL] $name not reachable: $_" -ForegroundColor Red
        return $false
    }
}

# ── 1. Health checks ─────────────────────────────────────────────────────────
Write-Section "1. Service Health Checks"
$ieOk    = Test-Health $ieUrl    "Intelligence Engine (8011)"
$audioOk = Test-Health $audioUrl "Audio Engine (8010)"

try {
    $llmHealth = Invoke-RestMethod "$llmUrl/health" -Method GET -TimeoutSec 5
    Write-Host "  [OK] LLM Adapter (9100): $($llmHealth | ConvertTo-Json -Compress)" -ForegroundColor Green
    $llmOk = $true
} catch {
    # LLM adapter may not have /health — try /docs or just proceed
    Write-Host "  [WARN] LLM Adapter /health not available — will test via IE" -ForegroundColor Yellow
    $llmOk = $true
}

if (-not $ieOk) {
    Write-Host ""
    Write-Host "Intelligence Engine is not running. Start with: .\start-all.ps1" -ForegroundColor Red
    exit 1
}

# ── 2. LLM Adapter direct test ───────────────────────────────────────────────
Write-Section "2. LLM Adapter Direct Test (port 9100)"
$llmBody = @{
    messages = @(
        @{ role = "system";  content = "You are a helpful customer service assistant." },
        @{ role = "user";    content = "What are your pricing plans?" }
    )
    model = "gpt-4o"
} | ConvertTo-Json -Depth 5

try {
    $llmResp = Invoke-RestMethod "$llmUrl/v1/generate" -Method POST `
        -Body $llmBody -ContentType "application/json" -TimeoutSec 30
    Write-Host "  [OK] LLM response received:" -ForegroundColor Green
    Write-Host "       $($llmResp | ConvertTo-Json -Depth 5)" -ForegroundColor White
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
}

# ── 3. Intelligence Engine — E2E Demo (simulated transcribed speech) ──────────
Write-Section "3. Intelligence Engine E2E Demo — Simulated Transcribed Text"

$testCases = @(
    @{ audio_text = "What are your pricing plans?";           label = "Pricing inquiry"      },
    @{ audio_text = "I need help resetting my password.";     label = "Password reset request" },
    @{ audio_text = "Can I speak to a human agent please?";   label = "Escalation request"   },
    @{ audio_text = "My order number is 12345, where is it?"; label = "Order status query"   }
)

foreach ($tc in $testCases) {
    Write-Host ""
    Write-Host "  >> [$($tc.label)]" -ForegroundColor Yellow
    Write-Host "     Input: `"$($tc.audio_text)`"" -ForegroundColor Gray

    $body = @{
        business_id = "demo-business"
        conv_id     = "test-conv-$(Get-Random)"
        audio_text  = $tc.audio_text
    } | ConvertTo-Json

    try {
        $resp = Invoke-RestMethod "$ieUrl/intelligence/e2e-demo" -Method POST `
            -Body $body -ContentType "application/json" -TimeoutSec 30
        Write-Host "     Action  : $($resp.stages.step.action_type)" -ForegroundColor Cyan
        Write-Host "     Response: $($resp.stages.step.response_text)" -ForegroundColor Green
        Write-Host "     Intent  : $($resp.stages.step.nlu_intent)" -ForegroundColor Cyan
        Write-Host "     Escalate: $($resp.stages.step.escalate)" -ForegroundColor Cyan
    } catch {
        Write-Host "     [FAIL] $($_.Exception.Message)" -ForegroundColor Red
        # Show response body if available
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host "     Detail: $($reader.ReadToEnd())" -ForegroundColor DarkRed
        }
    }
}

# ── 4. Intelligence Engine — Step endpoint (raw transcript segment) ───────────
Write-Section "4. Intelligence Engine Step — Raw Transcript Segment"

$now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$stepBody = @{
    business_id   = "demo-business"
    conv_id       = "step-test-$(Get-Random)"
    session_state = @{}
    segment       = @{
        event      = "transcript.segment"
        business_id = "demo-business"
        conv_id    = "step-test-001"
        segment_id = "seg-001"
        speaker    = "customer"
        start_ts   = $now
        end_ts     = $now
        text       = "Hello, I would like to know my account balance."
        confidence = 0.95
    }
} | ConvertTo-Json -Depth 5

try {
    $stepResp = Invoke-RestMethod "$ieUrl/intelligence/step" -Method POST `
        -Body $stepBody -ContentType "application/json" -TimeoutSec 30
    Write-Host "  [OK] Step response:" -ForegroundColor Green
    Write-Host "       action_type : $($stepResp.action_type)" -ForegroundColor Cyan
    Write-Host "       response    : $($stepResp.response_text)" -ForegroundColor White
    Write-Host "       intent      : $($stepResp.nlu_intent)" -ForegroundColor Cyan
    Write-Host "       escalate    : $($stepResp.escalate)" -ForegroundColor Cyan
    Write-Host "       tts_ready   : $($stepResp.tts)" -ForegroundColor Cyan
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "  Detail: $($reader.ReadToEnd())" -ForegroundColor DarkRed
    }
}

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host " Test run complete." -ForegroundColor Green
Write-Host "══════════════════════════════════════════" -ForegroundColor DarkCyan
