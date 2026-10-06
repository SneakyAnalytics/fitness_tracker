#!/usr/bin/env python3
import os
import sys
import importlib.util
from datetime import datetime
from typing import Optional

# Ensure repo root is on path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

# Also support container path
if os.path.isdir("/app"):
    sys.path.insert(0, "/app")

from src.utils.dynamic_workout_content import DynamicWorkoutContent

notify_path = os.path.join(repo_root, "scripts", "notify_email.py")
spec = importlib.util.spec_from_file_location("notify_email", notify_path)
notify_email = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify_email)
send_email = notify_email.send_email


def pick_recent_item(content: DynamicWorkoutContent, source: dict) -> Optional[dict]:
    items = content._parse_rss_items(source['rss'], max_items=25)
    for item in items:
        title = item.get('title', '')
        description = item.get('description', '')
        pub_raw = item.get('pub_date', '')
        pub_dt = content._parse_pub_date(pub_raw) if pub_raw else None
        if not pub_dt or not content._is_recent_date(pub_dt):
            continue
        if not title:
            continue
        if content._is_job_listing(title) or content._is_job_listing(description):
            continue
        if not content._passes_team_filters(source['label'], title, description):
            continue
        return item
    return None


def main():
    if not os.getenv('EMAIL_TO'):
        return

    content = DynamicWorkoutContent()
    lines = []
    lines.append("Daily News Links (today/yesterday)")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")

    count = 0
    for source in content.team_news_sources:
        item = pick_recent_item(content, source)
        if not item:
            continue
        title = item.get('title', '')
        link = item.get('link', '')
        lines.append(f"- {source['label']}: {title}")
        if link:
            lines.append(f"  {link}")
        count += 1
        if count >= 10:
            break

    if count == 0:
        lines.append("No recent items found.")

    subject = "Daily Zwift News Links"
    body = "\n".join(lines)
    send_email(subject, body)


if __name__ == "__main__":
    main()
