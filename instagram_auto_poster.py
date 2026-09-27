"""
Instagram Graph API auto-poster
--------------------------------
Implements Meta's two-step container publish flow:
  1. POST /{ig-user-id}/media          -> create a container
  2. Poll the container until status = FINISHED
  3. POST /{ig-user-id}/media_publish  -> publish it

Requirements:
  - Instagram Business/Creator account linked to a Facebook Page
  - Long-lived access token with instagram_basic + instagram_content_publish
  - pip install requests

Usage:
  export IG_ACCESS_TOKEN="your_long_lived_token"
  export IG_USER_ID="your_instagram_business_account_id"
  python instagram_auto_poster.py
"""

import os
import time
import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
IG_USER_ID = os.environ.get("IG_USER_ID")


class InstagramPublishError(Exception):
    pass


def check_publishing_limit():
    """
    Check how much of your 100-posts/24h quota is left before doing any work.
    Meta also returns an X-Business-Use-Case-Usage header on every call;
    in a production system, log that header too and back off if any
    metric is above ~80%.
    """
    url = f"{GRAPH_API_BASE}/{IG_USER_ID}/content_publishing_limit"
    resp = requests.get(url, params={"access_token": ACCESS_TOKEN})
    resp.raise_for_status()
    data = resp.json().get("data", [{}])[0]
    used = data.get("quota_usage", 0)
    print(f"Publishing quota used: {used}/100 in the current 24h window")
    return used


def create_media_container(image_url: str, caption: str) -> str:
    """
    Step 1: create a media container. Note this does NOT post anything yet.
    Containers expire after 24 hours, so only create one shortly before
    you intend to actually publish it.
    """
    url = f"{GRAPH_API_BASE}/{IG_USER_ID}/media"
    payload = {
        "image_url": image_url,   # must be a public URL, JPEG, 4:5 to 1.91:1 ratio
        "caption": caption,
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.post(url, data=payload)
    if not resp.ok:
        print(f"Meta API error response: {resp.text}")
    resp.raise_for_status()
    container_id = resp.json()["id"]
    print(f"Created container: {container_id}")
    return container_id


def wait_for_container_ready(container_id: str, timeout_seconds: int = 120) -> None:
    """
    Step 2: poll the container's status_code until it's FINISHED.
    Meta needs a moment to fetch and process the media internally.
    """
    url = f"{GRAPH_API_BASE}/{container_id}"
    start = time.time()

    while time.time() - start < timeout_seconds:
        resp = requests.get(
            url, params={"fields": "status_code", "access_token": ACCESS_TOKEN}
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        print(f"Container status: {status}")

        if status == "FINISHED":
            return
        if status == "ERROR":
            raise InstagramPublishError(f"Container {container_id} failed to process")

        time.sleep(5)

    raise InstagramPublishError(f"Container {container_id} timed out before FINISHED")


def publish_container(container_id: str) -> str:
    """
    Step 3: publish the finished container. This is the moment the
    post actually goes live on Instagram.
    """
    url = f"{GRAPH_API_BASE}/{IG_USER_ID}/media_publish"
    payload = {"creation_id": container_id, "access_token": ACCESS_TOKEN}
    resp = requests.post(url, data=payload)
    resp.raise_for_status()
    media_id = resp.json()["id"]
    print(f"Published! Media ID: {media_id}")
    return media_id


def post_to_instagram(image_url: str, caption: str) -> str:
    """
    Full pipeline: check quota -> create container -> wait -> publish.
    Returns the published media_id, which you should log alongside the
    container_id so a failed/retried run never double-posts.
    """
    if not ACCESS_TOKEN or not IG_USER_ID:
        raise InstagramPublishError(
            "Set IG_ACCESS_TOKEN and IG_USER_ID environment variables first."
        )

    check_publishing_limit()
    container_id = create_media_container(image_url, caption)
    wait_for_container_ready(container_id)
    media_id = publish_container(container_id)
    return media_id


if __name__ == "__main__":
    # Example call — replace with a real, publicly reachable image URL
    example_image_url = "https://raw.githubusercontent.com/genalpha1992-cloud/Pulse-Prose/main/HealthTip_cropped.jpg"
    example_caption = (
        "5 evidence-based tips for better sleep tonight 🌙\n"
        "Source: sleep research summarized in your own words.\n"
        "#sleep #healthtips #wellness"
    )

    try:
        post_to_instagram(example_image_url, example_caption)
    except InstagramPublishError as e:
        print(f"Failed to post: {e}")