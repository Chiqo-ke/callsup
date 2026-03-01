from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "Specs PR URL",
    "Module PR URL(s)",
    "Mock-first status",
    "Blockers & mitigation",
    "PR Order Confirmation",
]


def main() -> int:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH not found; skipping PR governance check.")
        return 0

    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = payload.get("pull_request")
    if not pr:
        print("No pull_request payload; skipping PR governance check.")
        return 0

    body = pr.get("body") or ""
    missing = [section for section in REQUIRED_SECTIONS if section not in body]
    if missing:
        print("PR governance check failed. Missing required PR template sections:")
        for section in missing:
            print(f"- {section}")
        return 1

    print("PR governance check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
