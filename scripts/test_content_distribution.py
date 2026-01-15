#!/usr/bin/env python3
"""Test content distribution to ensure variety"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.dynamic_workout_content import DynamicWorkoutContent
from collections import Counter

print("Testing Content Distribution")
print("=" * 70)

content = DynamicWorkoutContent()

# Simulate getting 20 messages (typical workout)
content_types = []

for i in range(20):
    msg = content.get_fresh_content("general")
    
    # Identify content type by emoji
    if '💬' in msg:
        content_types.append('quote')
    elif '😄' in msg:
        content_types.append('joke')
    elif '🤓' in msg:
        content_types.append('fact')
    elif '💪' in msg:
        content_types.append('encouragement')
    elif '🔢' in msg:
        content_types.append('number')
    elif '💡' in msg:
        content_types.append('advice')
    elif '✨' in msg:
        content_types.append('affirmation')
    elif '💥' in msg:
        content_types.append('chuck_norris')
    elif '🎤' in msg:
        content_types.append('kanye')
    elif '🔬' in msg:
        content_types.append('science')
    elif '📚' in msg:
        content_types.append('research')
    elif '📅' in msg or '📖' in msg:
        content_types.append('wikipedia')

# Count distribution
distribution = Counter(content_types)

print("\nContent Distribution (20 messages):")
print("-" * 70)
for content_type, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
    bar = "█" * count
    print(f"{content_type:15} ({count:2}): {bar}")

print("\nInternal tracking:")
print(content.content_type_counts)

# Check for balance
max_count = max(distribution.values()) if distribution else 0
if max_count > 3:
    worst = distribution.most_common(1)[0]
    print(f"\n⚠️  '{worst[0]}' appears {worst[1]} times (should be ≤3)")
else:
    print(f"\n✅ Good variety! Max per type: {max_count}")
