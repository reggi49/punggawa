#!/usr/bin/env python3
"""
Test Postiz Autopost Integration for Punggawa
Usage:
    ./venv/bin/python3 scripts/test_postiz_autopost.py
"""

import io
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
import requests
from PIL import Image, ImageDraw

API_KEY = "d59b5fb460b5b78844e9ddd597a2bf575dc034b34d87e11868d21b3406837344"
BASE_URL = "https://sosial.bogorstore.com/api/public/v1"
INTEGRATION_ID = "cmvvzqhn7000epl6yd8bp7mzz"

def create_banner():
    width, height = 1080, 1080
    img = Image.new("RGB", (width, height), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    for i in range(120):
        draw.rectangle(
            [i * 3, i * 3, width - i * 3, height - i * 3],
            outline=(30 + i, 41 + int(i * 1.5), 80 + i * 2),
        )

    card_margin = 100
    draw.rounded_rectangle(
        [card_margin, card_margin, width - card_margin, height - card_margin],
        radius=40,
        fill=(30, 41, 59),
        outline=(59, 130, 246),
        width=4,
    )

    draw.rounded_rectangle([160, 160, 480, 220], radius=15, fill=(37, 99, 235))
    draw.text((180, 180), "PUNGGAWA SYSTEM", fill=(255, 255, 255))

    draw.text((160, 280), "Punggawa Orchestrator", fill=(248, 250, 252))
    draw.text((160, 360), "Autonomous Instagram Auto-Post Test", fill=(148, 163, 184))
    draw.line([(160, 440), (width - 160, 440)], fill=(71, 85, 105), width=2)

    now_str = datetime.now().strftime("%d %B %Y - %H:%M:%S WIB")
    features = [
        "✓ Multi-Source Research Engine (Brave API)",
        "✓ Strict SOP Quality & Duplicate Validation",
        "✓ Dual-Language AI Content Generation (ID/EN)",
        "✓ Automated Social Sync via Postiz Engine",
        f"✓ Execution Time: {now_str}",
    ]
    y = 480
    for f in features:
        draw.text((160, y), f, fill=(226, 232, 240))
        y += 65

    draw.rounded_rectangle([160, 840, width - 160, 910], radius=15, fill=(16, 185, 129))
    draw.text((200, 865), "Status: Live Verified • sosial.bogorstore.com", fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf, now_str

def main():
    print("🚀 [Punggawa] Starting Postiz Instagram Autopost Test...")
    
    # 1. Generate Banner
    buf, now_str = create_banner()
    print(f"✅ Generated 1080x1080 banner with timestamp: {now_str}")

    # 2. Upload to Postiz Storage
    headers = {"Authorization": API_KEY}
    files = {"file": ("punggawa_test.jpg", buf, "image/jpeg")}
    r_upload = requests.post(f"{BASE_URL}/upload", headers=headers, files=files)
    if r_upload.status_code != 201:
        print(f"❌ Upload failed ({r_upload.status_code}): {r_upload.text}")
        return
    upload_data = r_upload.json()
    print(f"✅ Uploaded to Postiz Storage: {upload_data['path']}")

    # 3. Create Post
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = {
        "type": "now",
        "date": now_iso,
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": INTEGRATION_ID},
                "value": [
                    {
                        "content": (
                            f"Halo dari Punggawa Orchestrator! 🚀\n\n"
                            f"Postingan otomatis ini dikirim langsung melalui pipeline AI Punggawa ke Instagram.\n\n"
                            f"Waktu eksekusi: {now_str}\n\n"
                            f"#punggawa #automation #tech #ai #bogorstore"
                        ),
                        "image": [
                            {
                                "id": upload_data["id"],
                                "path": upload_data["path"],
                            }
                        ],
                    }
                ],
                "settings": {
                    "__type": "instagram",
                    "post_type": "post",
                },
            }
        ],
    }

    r_post = requests.post(f"{BASE_URL}/posts", headers=headers, json=payload)
    if r_post.status_code != 201:
        print(f"❌ Post creation failed ({r_post.status_code}): {r_post.text}")
        return
    post_res = r_post.json()
    print(f"✅ Post enqueued successfully in Postiz! Details: {post_res}")
    print("\n⏳ Worker is publishing to Meta Graph API...")

if __name__ == "__main__":
    main()

