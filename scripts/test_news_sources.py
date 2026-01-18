#!/usr/bin/env python3
"""Fetch sample news items from each source used in Zwift text events."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.dynamic_workout_content import DynamicWorkoutContent


def main() -> None:
    content = DynamicWorkoutContent()

    print("News Sources (current):")
    print("- Team RSS (Google News RSS):")
    for src in content.team_news_sources:
        print(f"  • {src['label']}: {src['rss']}")
    print("- News API (top-headlines, US)")
    print("- Hacker News (topstories)")
    print("- arXiv (recent papers: q-bio, physics, cs.AI, cs.LG)")
    print()

    print("Samples:")

    team = content._get_team_news_story()
    if team:
        headline, story_text = team
        print("\n[Team RSS]")
        print(headline)
        print(f"Story text: {story_text[:200]}")
    else:
        print("\n[Team RSS] No item found.")

    news = content._get_news_api_story()
    if news:
        headline, story_text = news
        print("\n[News API]")
        print(headline)
        print(f"Story text: {story_text[:200]}")
    else:
        print("\n[News API] No item found or NEWS_API_KEY missing.")

    hn = content._get_science_headline_full()
    if hn:
        headline, story_text = hn
        print("\n[Hacker News]")
        print(headline)
        print(f"Story text: {story_text[:200]}")
    else:
        print("\n[Hacker News] No item found.")

    arxiv = content._get_arxiv_story_full()
    if arxiv:
        headline, story_text = arxiv
        print("\n[arXiv]")
        print(headline)
        print(f"Story text: {story_text[:200]}")
    else:
        print("\n[arXiv] No item found.")


if __name__ == "__main__":
    main()
