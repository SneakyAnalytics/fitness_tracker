#!/usr/bin/env python3
"""
Test script for enhanced text event functionality.
Demonstrates the new story pairs and frequency improvements.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.dynamic_workout_content import DynamicWorkoutContent

def test_story_with_summary():
    """Test the new story + summary feature"""
    print("=" * 80)
    print("Testing Story with AI Summary Feature")
    print("=" * 80)
    print()
    
    content = DynamicWorkoutContent()
    
    print("Attempting to fetch a story with summary...")
    print("(This will try News API → Hacker News → arXiv)")
    print()
    print("Note: If Gemini API quota is exhausted, will use simple text-based")
    print("      summaries as fallback (still works great!)")
    print()
    
    # Try a few times since stories might be used
    result = None
    for attempt in range(3):
        result = content.get_story_with_summary()
        if result:
            break
        if attempt < 2:
            print(f"Attempt {attempt + 1} failed, trying again...")
    
    if result:
        headline, summary = result
        print("✅ SUCCESS!")
        print()
        print("Headline (shown first):")
        print(f"  {headline}")
        print()
        print("Summary (shown 60 seconds later):")
        print(f"  {summary}")
        print()
        
        # Check if it's AI or simple summary
        if "💡" in summary:
            if len(summary) > 100:
                print("Type: Simple text-based summary (Gemini quota exhausted)")
            else:
                print("Type: AI-generated summary (Gemini available)")
        
        print()
        print("This is what will appear in your Zwift workout!")
    else:
        print("❌ No story retrieved after 3 attempts")
        print()
        print("Possible reasons:")
        print("  • Network connectivity issues")
        print("  • All story APIs unavailable")
        print("  • Story pool exhausted (rare)")
        print()
        print("Note: This is rare - workouts will still have plenty of other content!")
    
    print()

def test_content_variety():
    """Test variety of content sources"""
    print("=" * 80)
    print("Testing Content Variety (Sample Messages)")
    print("=" * 80)
    print()
    
    content = DynamicWorkoutContent()
    
    print("Fetching 10 sample messages...")
    print("(This simulates what you'd see during a workout)")
    print()
    
    for i in range(10):
        message = content.get_fresh_content("general")
        print(f"{i+1:2d}. {message}")
    
    print()

def test_trivia_pair():
    """Test trivia question + answer pairing"""
    print("=" * 80)
    print("Testing Trivia Q&A Pairing")
    print("=" * 80)
    print()
    
    content = DynamicWorkoutContent()
    
    print("Fetching trivia question + answer...")
    print()
    
    result = content.get_trivia_pair()
    
    if result:
        question, answer = result
        print("✅ SUCCESS!")
        print()
        print("Question (shown first):")
        print(f"  {question}")
        print()
        print("Answer (shown 45 seconds later):")
        print(f"  {answer}")
    else:
        print("❌ Trivia API unavailable")
    
    print()

def show_config():
    """Show current configuration"""
    import os
    
    print("=" * 80)
    print("Configuration Check")
    print("=" * 80)
    print()
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    news_key = os.getenv('NEWS_API_KEY')
    
    print("Required APIs:")
    print(f"  GEMINI_API_KEY: {'✅ Configured' if gemini_key else '❌ Not configured'}")
    if gemini_key:
        print(f"    (Key: {gemini_key[:10]}...)")
        print(f"    Status: May have quota limits - will fallback gracefully")
    
    print()
    print("Optional APIs:")
    print(f"  NEWS_API_KEY: {'✅ Configured' if news_key else '⚠️  Not configured (will use fallback)'}")
    if news_key:
        print(f"    (Key: {news_key[:10]}...)")
    
    print()
    
    if not gemini_key:
        print("⚠️  INFO: GEMINI_API_KEY not found")
        print("   AI summaries won't work, but simple text-based summaries will be used.")
        print("   Set with: export GEMINI_API_KEY='your_key'")
        print()
    else:
        print("ℹ️  NOTE: Gemini API has quota limits on free tier")
        print("   If quota exhausted, text events will use simple summaries instead.")
        print("   This is automatic - no action needed!")
        print()
    
    if not news_key:
        print("ℹ️  INFO: NEWS_API_KEY not configured")
        print("   You'll still get great content from:")
        print("     • Hacker News (tech/science)")
        print("     • arXiv (research papers)")
        print("   To add news headlines:")
        print("     ./scripts/setup_news_api.sh")
        print()

def main():
    """Run all tests"""
    show_config()
    
    print("=" * 80)
    print("Enhanced Text Events - Test Suite")
    print("=" * 80)
    print()
    print("This will test the new features:")
    print("  1. Story pairs (headline + AI summary)")
    print("  2. Content variety (12+ sources)")
    print("  3. Trivia Q&A pairing")
    print()
    input("Press Enter to continue...")
    print()
    
    # Test 1: Story with summary
    test_story_with_summary()
    
    # Test 2: Content variety
    test_content_variety()
    
    # Test 3: Trivia pair
    test_trivia_pair()
    
    print("=" * 80)
    print("Testing Complete!")
    print("=" * 80)
    print()
    print("Summary:")
    print("  • Text events will now appear every 1-2 minutes (was 2-3)")
    print("  • 20-30 total events per workout (was 10-15)")
    print("  • Stories include AI-generated summaries")
    print("  • Summaries appear 60 seconds after headlines")
    print()
    print("Next: Generate a Zwift workout to see it in action!")
    print()

if __name__ == "__main__":
    main()
