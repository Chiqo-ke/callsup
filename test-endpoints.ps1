# test-endpoints.ps1
# Full endpoint test suite for CALLSUP backend.
# Run this in a terminal that is NOT running the backend services.
# Requires: start-all.ps1 to have been run first (all 3 services up).

$base    = "http://127.0.0.1:8010"
$pass    = 0
$fail    = 0
$token   = $null
$bizId   = $null
$itemId  = $null

function Pass([string]$label) {
    Write-Host "  PASS  $label" -ForegroundColor Green
    $script:pass++
}
function Fail([string]$label, [string]$detail = "") {
    Write-Host "  FAIL  $label  $detail" -ForegroundColor Red
    $script:fail++
}
function Section([string]$title) {
    Write-Host ""
    Write-Host "── $title ──" -ForegroundColor Cyan
}

# ─────────────────────────────────────────────────────────────────────────────
Section "1. Health checks"

# Audio Engine
try {
    $h = Invoke-RestMethod "$base/health" -TimeoutSec 5
    if ($h.status -eq "ok") { Pass "GET $base/health → status=ok" }
    else                     { Fail "GET $base/health → unexpected: $($h | ConvertTo-Json -Compress)" }
} catch { Fail "GET $base/health" "$_" }

# Intelligence Engine (optional — may not be running)
try {
    $h2 = Invoke-RestMethod "http://127.0.0.1:8011/health" -TimeoutSec 3
    Pass "GET :8011/health → $($h2 | ConvertTo-Json -Compress)"
} catch { Write-Host "  SKIP  :8011/health (intelligence engine not running)" -ForegroundColor DarkGray }

# ─────────────────────────────────────────────────────────────────────────────
Section "2. Auth — Register"

$regBody = '{"username":"testuser","email":"test@callsup.io","password":"Test1234!"}'
try {
    $reg = Invoke-RestMethod "$base/auth/register" -Method POST `
        -ContentType "application/json" -Body $regBody -TimeoutSec 10
    if ($reg.access_token -and $reg.business_id) {
        $token  = $reg.access_token
        $bizId  = $reg.business_id
        Pass "POST /auth/register → business_id=$bizId"
    } else {
        Fail "POST /auth/register → missing fields: $($reg | ConvertTo-Json -Compress)"
    }
} catch {
    $errBody = $_.ErrorDetails.Message
    # 409 = user already exists — try login instead
    if ($_.Exception.Response.StatusCode -eq 409 -or $errBody -match "already") {
        Write-Host "  INFO  user already exists, skipping register" -ForegroundColor DarkGray
    } else {
        Fail "POST /auth/register" "$errBody"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
Section "3. Auth — Login"

$loginBody = '{"username":"testuser","password":"Test1234!"}'
try {
    $login = Invoke-RestMethod "$base/auth/login" -Method POST `
        -ContentType "application/json" -Body $loginBody -TimeoutSec 10
    if ($login.access_token) {
        $token = $login.access_token
        $bizId = $login.business_id
        Pass "POST /auth/login → token received, business_id=$bizId"
    } else {
        Fail "POST /auth/login → no token: $($login | ConvertTo-Json -Compress)"
    }
} catch { Fail "POST /auth/login" "$($_.ErrorDetails.Message)" }

# ─────────────────────────────────────────────────────────────────────────────
Section "4. Auth — /me"

if ($token) {
    try {
        $me = Invoke-RestMethod "$base/auth/me" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 5
        if ($me.username -eq "testuser" -and $me.business_id -eq $bizId) {
            Pass "GET /auth/me → username=$($me.username) business_id=$($me.business_id)"
        } else {
            Fail "GET /auth/me → unexpected: $($me | ConvertTo-Json -Compress)"
        }
    } catch { Fail "GET /auth/me" "$($_.ErrorDetails.Message)" }
} else {
    Write-Host "  SKIP  /auth/me (no token — login failed)" -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────────────────────────────────
Section "5. Context — Create items"

$headers = @{ Authorization = "Bearer $token" }

if ($token) {
    # Item 1
    $body1 = '{"label":"Company Overview","content":"CALLSUP is an AI-powered call analysis platform.","type":"text","refine_with_ai":false}'
    try {
        $c1 = Invoke-RestMethod "$base/context" -Method POST `
            -ContentType "application/json" -Headers $headers -Body $body1 -TimeoutSec 10
        if ($c1.id) {
            $itemId = $c1.id
            Pass "POST /context → id=$($c1.id) label='$($c1.label)'"
        } else {
            Fail "POST /context item 1 → $($c1 | ConvertTo-Json -Compress)"
        }
    } catch { Fail "POST /context item 1" "$($_.ErrorDetails.Message)" }

    # Item 2
    $body2 = '{"label":"Objection Handling","content":"When a customer objects on price, emphasise ROI and offer a trial period.","type":"text","refine_with_ai":false}'
    try {
        $c2 = Invoke-RestMethod "$base/context" -Method POST `
            -ContentType "application/json" -Headers $headers -Body $body2 -TimeoutSec 10
        if ($c2.id) { Pass "POST /context → id=$($c2.id) label='$($c2.label)'" }
        else         { Fail "POST /context item 2" "$($c2 | ConvertTo-Json -Compress)" }
    } catch { Fail "POST /context item 2" "$($_.ErrorDetails.Message)" }
} else {
    Write-Host "  SKIP  context tests (no token)" -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────────────────────────────────
Section "6. Context — List"

if ($token) {
    try {
        $list = Invoke-RestMethod "$base/context" -Headers $headers -TimeoutSec 5
        if ($list.Count -ge 1) {
            Pass "GET /context → $($list.Count) item(s) returned"
            $list | ForEach-Object { Write-Host "       · [$($_.id)] $($_.label)" -ForegroundColor DarkGray }
        } else {
            Fail "GET /context → empty list"
        }
    } catch { Fail "GET /context" "$($_.ErrorDetails.Message)" }
} else {
    Write-Host "  SKIP  GET /context (no token)" -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────────────────────────────────
Section "7. Context — Update"

if ($token -and $itemId) {
    $updateBody = '{"label":"Company Overview (updated)","content":"CALLSUP is an AI-powered call analysis and coaching platform for sales teams.","refine_with_ai":false}'
    try {
        $upd = Invoke-RestMethod "$base/context/$itemId" -Method PUT `
            -ContentType "application/json" -Headers $headers -Body $updateBody -TimeoutSec 10
        if ($upd.label -eq "Company Overview (updated)") {
            Pass "PUT /context/$itemId → label updated"
        } else {
            Fail "PUT /context/$itemId → $($upd | ConvertTo-Json -Compress)"
        }
    } catch { Fail "PUT /context/$itemId" "$($_.ErrorDetails.Message)" }
} else {
    Write-Host "  SKIP  PUT /context (no token or item id)" -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────────────────────────────────
Section "8. Context — Delete"

if ($token -and $itemId) {
    try {
        Invoke-RestMethod "$base/context/$itemId" -Method DELETE -Headers $headers -TimeoutSec 5
        Pass "DELETE /context/$itemId → 204"
    } catch { Fail "DELETE /context/$itemId" "$($_.ErrorDetails.Message)" }
} else {
    Write-Host "  SKIP  DELETE /context (no token or item id)" -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────────────────────────────────
Section "9. Context — Verify deletion"

if ($token) {
    try {
        $final = Invoke-RestMethod "$base/context" -Headers $headers -TimeoutSec 5
        $stillThere = $final | Where-Object { $_.id -eq $itemId }
        if (-not $stillThere) {
            Pass "GET /context → deleted item no longer present ($($final.Count) item(s) remain)"
        } else {
            Fail "GET /context → deleted item still present"
        }
    } catch { Fail "GET /context (post-delete)" "$($_.ErrorDetails.Message)" }
}

# ─────────────────────────────────────────────────────────────────────────────
Section "10. Auth — Reject bad token"

try {
    Invoke-RestMethod "$base/auth/me" -Headers @{ Authorization = "Bearer invalidtoken" } -TimeoutSec 5 | Out-Null
    Fail "GET /auth/me with bad token → should have returned 401"
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 401 -or $code -eq 403) { Pass "GET /auth/me bad token → $code (expected)" }
    else { Fail "GET /auth/me bad token → unexpected status $code" }
}

# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "────────────────────────────────" -ForegroundColor White
Write-Host "  Results: $pass passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
Write-Host "────────────────────────────────" -ForegroundColor White
