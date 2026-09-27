"""
Long-lived token refresher for the Instagram Graph API
--------------------------------------------------------
Meta lets you "refresh" a long-lived token by running the same
fb_exchange_token flow again, using your CURRENT long-lived token
as the input. This resets the ~60 day clock, as long as you do it
before the current token actually expires (and no more than once
every 24 hours).

This script:
  1. Reads your current token + its expiry date from a local JSON file
     (token_store.json), or bootstraps that file from IG_ACCESS_TOKEN
     the first time you run it.
  2. If the token is within REFRESH_THRESHOLD_DAYS of expiring,
     calls the fb_exchange_token endpoint to get a new one.
  3. Saves the new token + new expiry date back to token_store.json.

Requirements:
  export FB_APP_ID="your_app_id"
  export FB_APP_SECRET="your_app_secret"
  export IG_ACCESS_TOKEN="your_current_long_lived_token"   # only needed the first run
  pip install requests

Usage:
  python refresh_token.py

Then schedule this to run daily (e.g. via Windows Task Scheduler)
so it silently keeps your token alive indefinitely.
"""

import os
import json
import time
import requests

GRAPH_API_VERSION = "v21.0"
TOKEN_STORE_PATH = "token_store.json"
REFRESH_THRESHOLD_DAYS = 10  # refresh once fewer than this many days remain

FB_APP_ID = os.environ.get("FB_APP_ID")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET")


class TokenRefreshError(Exception):
    pass


def load_token_store() -> dict:
    """
    Load the stored token + expiry timestamp. If the file doesn't exist yet,
    bootstrap it from the IG_ACCESS_TOKEN environment variable, treating it
    as if it expires 60 days from now (Meta's standard long-lived duration).
    """
    if os.path.exists(TOKEN_STORE_PATH):
        with open(TOKEN_STORE_PATH, "r") as f:
            return json.load(f)

    bootstrap_token = os.environ.get("IG_ACCESS_TOKEN")
    if not bootstrap_token:
        raise TokenRefreshError(
            "No token_store.json found and IG_ACCESS_TOKEN is not set. "
            "Set IG_ACCESS_TOKEN once to bootstrap the token store."
        )

    store = {
        "access_token": bootstrap_token,
        # Assume ~60 days remaining if we don't actually know when it was issued
        "expires_at": time.time() + (60 * 24 * 60 * 60),
    }
    save_token_store(store)
    print("Bootstrapped token_store.json from IG_ACCESS_TOKEN.")
    return store


def save_token_store(store: dict) -> None:
    with open(TOKEN_STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)


def days_until_expiry(store: dict) -> float:
    seconds_remaining = store["expires_at"] - time.time()
    return seconds_remaining / (24 * 60 * 60)


def refresh_long_lived_token(current_token: str) -> dict:
    """
    Exchanges the current long-lived token for a fresh one, resetting
    the ~60 day expiry clock.
    """
    if not FB_APP_ID or not FB_APP_SECRET:
        raise TokenRefreshError("Set FB_APP_ID and FB_APP_SECRET environment variables.")

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "fb_exchange_token": current_token,
    }

    resp = requests.get(url, params=params)
    if not resp.ok:
        print(f"Meta API error response: {resp.text}")
    resp.raise_for_status()

    data = resp.json()
    new_token = data["access_token"]
    expires_in_seconds = data.get("expires_in", 60 * 24 * 60 * 60)  # fallback: 60 days

    return {
        "access_token": new_token,
        "expires_at": time.time() + expires_in_seconds,
    }


def main():
    store = load_token_store()
    remaining = days_until_expiry(store)
    print(f"Current token has {remaining:.1f} days remaining.")

    if remaining > REFRESH_THRESHOLD_DAYS:
        print("No refresh needed yet.")
        return

    print("Refreshing token...")
    new_store = refresh_long_lived_token(store["access_token"])
    save_token_store(new_store)

    new_remaining = days_until_expiry(new_store)
    print(f"Refreshed! New token valid for {new_remaining:.1f} more days.")
    print(f"New token saved to {TOKEN_STORE_PATH}.")
    print(
        "Remember to update IG_ACCESS_TOKEN wherever your posting script "
        "reads it from (or point that script at token_store.json directly)."
    )


if __name__ == "__main__":
    try:
        main()
    except TokenRefreshError as e:
        print(f"Token refresh failed: {e}")
