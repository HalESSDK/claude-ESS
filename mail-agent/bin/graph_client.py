#!/usr/bin/env python3
"""
Shared Microsoft Graph API client.
Loads token from cache and refreshes silently as needed.
"""
import msal, os, pathlib, sys, urllib.request, json

CLIENT_ID  = os.environ.get("AZURE_CLIENT_ID")
TENANT_ID  = os.environ.get("AZURE_TENANT_ID")
CACHE_PATH = pathlib.Path("/home/victor/mail-agent/.token_cache.json")
SCOPES     = ["Mail.ReadWrite", "Mail.Send"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_token() -> str:
    if not CLIENT_ID or not TENANT_ID:
        print("ERROR: AZURE_CLIENT_ID and AZURE_TENANT_ID must be set")
        sys.exit(1)
    if not CACHE_PATH.exists():
        print("Not authenticated. Run: python bin/mail_auth.py")
        sys.exit(1)

    cache = msal.SerializableTokenCache()
    cache.deserialize(CACHE_PATH.read_text(encoding="utf-8"))

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=cache,
    )

    accounts = app.get_accounts()
    if not accounts:
        print("No account in cache. Run: python bin/mail_auth.py")
        sys.exit(1)

    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if not result or "access_token" not in result:
        print("Token expired. Run: python bin/mail_auth.py")
        sys.exit(1)

    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")

    return result["access_token"]


def graph_request(method: str, path: str, body: dict = None) -> dict:
    token = get_token()
    url = f"{GRAPH_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}
