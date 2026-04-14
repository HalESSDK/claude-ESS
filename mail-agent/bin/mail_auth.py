#!/usr/bin/env python3
"""
Run once to authenticate with Microsoft Graph.
Saves token cache locally — subsequent runs refresh automatically.
"""
import msal, os, pathlib, sys

CLIENT_ID  = os.environ.get("AZURE_CLIENT_ID")
TENANT_ID  = os.environ.get("AZURE_TENANT_ID")
CACHE_PATH = pathlib.Path("/home/victor/mail-agent/.token_cache.json")
SCOPES     = ["Mail.ReadWrite", "Mail.Send"]

if not CLIENT_ID or not TENANT_ID:
    print("ERROR: AZURE_CLIENT_ID and AZURE_TENANT_ID must be set")
    sys.exit(1)

cache = msal.SerializableTokenCache()
if CACHE_PATH.exists():
    cache.deserialize(CACHE_PATH.read_text(encoding="utf-8"))

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    token_cache=cache,
)

# Try silent refresh first
accounts = app.get_accounts()
result = None
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        print("Already authenticated — token refreshed silently.")
        CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")
        sys.exit(0)

# Device code flow (one-time login)
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    print("ERROR:", flow.get("error_description", "Could not start device flow"))
    sys.exit(1)

print(flow["message"])
result = app.acquire_token_by_device_flow(flow)

if "access_token" in result:
    CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")
    print("Authenticated. Token cache saved.")
else:
    print("ERROR:", result.get("error_description", "Authentication failed"))
    sys.exit(1)
