#!/usr/bin/env python3
"""Check the Discord Desktop DevTools endpoint without exposing credentials."""

from __future__ import annotations

import argparse
import json

from discord_capture_lib import CaptureError, capture_authorization, connect_discord, get_targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--check-auth", action="store_true", help="observe an API request header in memory")
    parser.add_argument("--auth-timeout", type=int, default=30)
    parser.add_argument("--no-reload", action="store_true", help="do not reload the Discord renderer")
    args = parser.parse_args()

    targets = get_targets(args.port)
    target, client = connect_discord(args.port)
    result = {
        "endpoint_ok": True,
        "target_count": len(targets),
        "discord_target": {
            "title": target.get("title", ""),
            "url": target.get("url", ""),
            "type": target.get("type", ""),
        },
        "authorization_observed": None,
    }
    try:
        if args.check_auth:
            capture_authorization(client, timeout=args.auth_timeout, reload_page=not args.no_reload)
            result["authorization_observed"] = True
    finally:
        client.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"error: {exc}")

