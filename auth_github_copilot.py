"""
GitHub Copilot Device-Flow Authentication
Run this once to authenticate. No .env editing required.

Usage:
    python auth_github_copilot.py

Steps:
  1. Displays a one-time code and opens github.com/login/device
  2. You enter the code on that page and click Authorize
  3. Script polls until approved, then fetches the Copilot token
  4. Saves session to .copilot_session (read by svc-llm-adapter at runtime)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CLIENT_ID    = "Iv1.b507a08c87ecfe98"   # VS Code Copilot public OAuth App
SCOPE        = "read:user"
SESSION_FILE = Path(__file__).parent / ".copilot_session"


def _post(url: str, data: dict) -> dict:
    payload = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║        GitHub Copilot — Device Authentication        ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # ── 1. Request device + user code ────────────────────────────────────────
    device     = _post(
        "https://github.com/login/device/code",
        {"client_id": CLIENT_ID, "scope": SCOPE},
    )
    user_code  = device["user_code"]
    device_code = device["device_code"]
    verify_uri = device.get("verification_uri", "https://github.com/login/device")
    interval   = int(device.get("interval", 5))
    expires_in = int(device.get("expires_in", 900))

    # ── 2. Show the code clearly ──────────────────────────────────────────────
    print(f"  Authorization URL:  {verify_uri}")
    print()
    print(f"  ┌─────────────────────────┐")
    print(f"  │   Code:  {user_code:<13}  │")
    print(f"  └─────────────────────────┘")
    print()
    print("  Opening browser… enter the code above when prompted.")
    print()
    webbrowser.open(verify_uri)

    # ── 3. Poll silently until approved ──────────────────────────────────────
    print("  Waiting for you to authorize in the browser", end="", flush=True)
    deadline     = time.monotonic() + expires_in
    oauth_token: str | None = None

    while time.monotonic() < deadline:
        time.sleep(interval)
        result = _post(
            "https://github.com/login/oauth/access_token",
            {
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        if "access_token" in result:
            oauth_token = result["access_token"]
            print("  ✓")
            break
        err = result.get("error", "unknown")
        if err == "authorization_pending":
            print(".", end="", flush=True)
        elif err == "slow_down":
            interval += 5
            print("s", end="", flush=True)
        else:
            print(f"\n  GitHub error: {err}")
            sys.exit(1)

    if not oauth_token:
        print("\n  Timed out — please re-run the script and try again.")
        sys.exit(1)

    # ── 4. Exchange for Copilot token ─────────────────────────────────────────
    print("  Fetching Copilot API token…", end="", flush=True)
    copilot_token   = ""
    copilot_expires = ""
    try:
        copilot_resp    = _get_json(
            "https://api.github.com/copilot_internal/v2/token",
            oauth_token,
        )
        copilot_token   = copilot_resp.get("token", "")
        copilot_expires = copilot_resp.get("expires_at", "")
        print("  ✓")
    except Exception as exc:
        print(f"  (could not fetch Copilot token: {exc})")

    # ── 5. Save session (not .env) ────────────────────────────────────────────
    session = {
        "oauth_token":     oauth_token,
        "copilot_token":   copilot_token,
        "copilot_expires": copilot_expires,
        "saved_at":        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    SESSION_FILE.write_text(json.dumps(session, indent=2), encoding="utf-8")

    print()
    print(f"  Session saved to:  {SESSION_FILE.name}")
    print()
    print("  ✓  Authentication complete.")
    print()
    print("  Start the services and run:  python smoke_test.py")
    print()


if __name__ == "__main__":
    main()
