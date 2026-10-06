#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from typing import Optional

# Ensure /app is on sys.path when running in container
sys.path.insert(0, "/app")

from src.utils.dynamic_workout_content import DynamicWorkoutContent


def pick_recent_item(content: DynamicWorkoutContent, source: dict) -> Optional[dict]:
    items = content._parse_rss_items(source['rss'], max_items=25)
    # prefer most recent items
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


def summarize_item(content: DynamicWorkoutContent, source: dict, item: dict) -> list[str]:
    title = item.get('title', '')
    description = item.get('description', '')
    link = item.get('link', '')
    fetched = content._fetch_article_text(link)
    story_text = ' '.join(filter(None, [description, fetched]))
    story_text = content._clean_story_text(title, story_text)
    headline = f"{source['emoji']} {source['label']}: {title}"
    summary = content._generate_story_summary(headline, story_text)
    if summary and content._is_redundant_summary(headline, summary):
        summary = None
    if not summary:
        summary = content._generate_local_summary(headline, story_text)
    if not summary:
        summary = content._create_simple_summary(story_text, headline)
    if summary and content._is_redundant_summary(headline, summary):
        summary = None
    if summary and (len(summary.strip()) < 20 or summary.strip() == '---'):
        summary = None
    messages = content._split_summary_messages(summary) if summary else []
    if link:
        return [headline, f"Link: {link}"] + messages
    return [headline] + messages


def main():
    content = DynamicWorkoutContent()
    print("=== Preview: Today/Yesterday News Stories ===")
    print(f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    print(f"Total sources: {len(content.team_news_sources)}")
    print()

    shown = 0
    for source in content.team_news_sources:
        item = pick_recent_item(content, source)
        if not item:
            continue
        messages = summarize_item(content, source, item)
        print(f"--- {source['label']} ---")
        for msg in messages:
            print(msg)
        print()
        shown += 1
        if shown >= 8:
            break

    if shown == 0:
        print("No recent items found (today/yesterday) across sources.")


if __name__ == "__main__":
    main()
