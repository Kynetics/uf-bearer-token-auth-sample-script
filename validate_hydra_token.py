#!/usr/bin/env python3
# Copyright (c) 2026 Kynetics Inc. All rights reserved.
# Licensed under the MIT License. See the LICENSE file for details.
"""
Hydra Token Validation Script

Validates the OAuth 2.0 client_credentials flow end-to-end:
  1. Exchanges API client credentials (name + secret) for a Bearer token
     via the Mgmt API token proxy endpoint.
  2. Uses the Bearer token to authenticate a call to a Mgmt API endpoint.

Usage:
    python3 validate_hydra_token.py \
        --mgmt-url https://mgmt.business.test.updatefactory.io \
        --tenant my_tenant \
        --client-name my-api-client \
        --client-secret <secret>

Requirements:
    Python 3.7+, requests library (pip install requests)
"""

import argparse
import base64
import json
import sys
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Install with: pip install requests")


def _redact(s: str, visible: int = 4) -> str:
    """Show only the last `visible` characters of a string."""
    if len(s) <= visible:
        return s
    return "*" * (len(s) - visible) + s[-visible:]


def exchange_token(mgmt_base_url: str, tenant: str, client_name: str, client_secret: str) -> str:
    """
    Step 1: Exchange client credentials for a Bearer token.

    Calls: POST /rest/v1/tenants/{tenant}/oauth2/token?grant_type=client_credentials
    Auth:  Basic <base64(client_name:client_secret)>
    """
    path = f"/rest/v1/tenants/{tenant}/oauth2/token"
    url = urljoin(mgmt_base_url, path)

    credentials = f"{client_name}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
    }
    params = {"grant_type": "client_credentials"}

    print(f"[1/2] Requesting Bearer token")
    print(f"      POST {url}")
    print(f"      tenant: {tenant}, client_name: {client_name}")

    try:
        resp = requests.post(url, headers=headers, params=params, timeout=30)
    except requests.RequestException as e:
        sys.exit(f"      FAILED — network error: {e}")

    if not resp.ok:
        sys.exit(
            f"      FAILED — HTTP {resp.status_code}\n"
            f"      Response: {resp.text[:500]}"
        )

    body = resp.json()
    access_token = body.get("access_token")
    if not access_token:
        sys.exit(
            f"      FAILED — no access_token in response\n"
            f"      Body: {json.dumps(body, indent=2)}"
        )

    print(f"      OK — token obtained")
    print(f"      token_type: {body.get('token_type')}, expires_in: {body.get('expires_in')}s")
    print(f"      token: {_redact(access_token)}")
    return access_token


def call_api(mgmt_base_url: str, bearer_token: str, endpoint: str) -> dict:
    """
    Step 2: Use the Bearer token to call a GET endpoint on the Mgmt API.
    """
    url = urljoin(mgmt_base_url, endpoint)
    headers = {
        "Authorization": f"Bearer {bearer_token}",
    }

    print(f"\n[2/2] Calling Mgmt API with Bearer token")
    print(f"      GET {url}")

    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        sys.exit(f"      FAILED — network error: {e}")

    if not resp.ok:
        sys.exit(
            f"      FAILED — HTTP {resp.status_code}\n"
            f"      Response: {resp.text[:500]}"
        )

    body = resp.json()
    content = body.get("content", [])
    total = body.get("total", len(content) if isinstance(content, list) else 1)

    print(f"      OK — HTTP 200")
    print(f"      items returned: {total}")

    if isinstance(content, list) and content:
        items = content[:3]
        for i, item in enumerate(items):
            summary = {k: v for k, v in item.items() if k in ("name", "id", "description", "version")}
            if not summary:
                summary = dict(list(item.items())[:3])
            print(f"      [{i}] {json.dumps(summary)}")
        if total > 3:
            print(f"      ... and {total - 3} more items")
    elif not content:
        summary = {k: v for k, v in body.items() if k in ("name", "id", "description", "version")}
        if not summary:
            summary = dict(list(body.items())[:5])
        print(f"      {json.dumps(summary, indent=2)[:500]}")

    return body


def main():
    parser = argparse.ArgumentParser(
        description="UF-1454: Validate Hydra OAuth 2.0 token flow via Mgmt API"
    )
    parser.add_argument("--mgmt-url", required=True, help="Mgmt API base URL (e.g. https://mgmt.business.test.updatefactory.io)")
    parser.add_argument("--tenant", required=True, help="Tenant name")
    parser.add_argument("--client-name", required=True, help="API client name (suffix, without tenant prefix)")
    parser.add_argument("--client-secret", required=True, help="API client secret")
    parser.add_argument(
        "--endpoint",
        default="/rest/v1/distributionsets",
        help="Mgmt API GET endpoint to call with the Bearer token (default: /rest/v1/distributionsets)",
    )
    args = parser.parse_args()

    mgmt_url = args.mgmt_url.rstrip("/")

    print("=" * 60)
    print("UF-1454 Hydra Token Validation")
    print(f"Mgmt API: {mgmt_url}")
    print("=" * 60)

    token = exchange_token(mgmt_url, args.tenant, args.client_name, args.client_secret)
    call_api(mgmt_url, token, args.endpoint)

    print("\n" + "=" * 60)
    print("VALIDATION PASSED — token exchange and Bearer auth both work.")
    print("=" * 60)


if __name__ == "__main__":
    main()
