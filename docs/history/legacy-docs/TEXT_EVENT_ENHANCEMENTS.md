# Zwift Text Event Enhancements

## Summary of Changes

Enhanced the text events in Zwift workout files to be more entertaining, informative, and frequent.

## Key Improvements

### 1. **Increased Frequency** 📈

- **Before**: 10-15 text events per workout (one every ~3 minutes)
- **After**: 20-30 text events per workout (one every ~1-2 minutes)
- **Benefit**: More entertainment, keeps your mind engaged during tough intervals

### 2. **Science Headlines with AI Summaries** 🔬💡

- **Before**: Just showed the headline (often confusing)
- **After**: Shows headline as title, then follows with AI-generated plain-language summary 60 seconds later
- **Example**:
  ```
  🔬 Science: "Novel CRISPR Mechanism Enables Precise Genome Editing in Non-Dividing Cells"
  [60 seconds later]
  💡 Scientists found a new way to edit genes in cells that aren't growing, which could help treat diseases like muscular dystrophy
  ```

### 3. **Current Events/News Stories** 📰

- **New**: Added trending news headlines with AI summaries
- **Sources**:
  - News API (top headlines, high-traffic stories)
  - Hacker News (tech/science focus)
  - arXiv research papers
- **Example**:
  ```
  📰 News: "Major Breakthrough in Fusion Energy Announced"
  [60 seconds later]
  💡 A lab created more energy from fusion than it used for the first time ever - big step toward clean unlimited power
  ```

### 4. **Story Pairing System** 🎯

- Every 6th text event is now a "story" (headline + summary)
- Guarantees the summary follows the headline
- 60-second gap gives you time to read and process the headline
- Stories cover:
  - Current events (if News API key provided)
  - Science research
  - Tech breakthroughs
  - Academic papers (with simple explanations)

## Content Mix

Your workout now includes:

1. **Stories with summaries** (~15-20% of events)

   - News headlines → AI summary
   - Science headlines → AI summary
   - Research papers → AI summary

2. **Sports trivia** (~15-20% of events)

   - Question → Answer (45 seconds apart)
   - Keeps format you already liked

3. **Varied entertainment** (~60-70% of events)
   - Inspirational quotes
   - Dad jokes
   - Fun facts
   - AI-generated encouragement
   - Chuck Norris facts
   - Kanye quotes
   - Number facts
   - Advice
   - Affirmations
   - Wikipedia "On This Day"
   - Plus more!

## API Setup

### Required (Already Have)

✅ **GEMINI_API_KEY** - For AI summaries and encouragement

- You already have this configured

### Optional (Recommended)

🆕 **NEWS_API_KEY** - For trending current events

Get a free News API key:

1. Go to: https://newsapi.org/register
2. Sign up (free tier: 100 requests/day)
3. Copy your API key
4. Add to your environment:
   ```bash
   export NEWS_API_KEY="your_key_here"
   ```

**Without News API**: System will fall back to Hacker News and arXiv (still great content, just less general news)

**With News API**: You get trending headlines from major news sources (CNN, BBC, NYT, etc.)

## Example Workout Flow

Here's what a 60-minute workout might look like now:

```
0:05  - 🎯 Welcome message
2:00  - 💬 Inspirational quote
3:30  - 😄 Dad joke
5:00  - 🏆 Trivia question
5:45  - 🏆 Trivia answer
7:00  - 📰 News headline
8:00  - 💡 News summary (AI-generated)
9:30  - 🤓 Fun fact
11:00 - 💪 AI encouragement
12:30 - 🔢 Number fact
14:00 - 📚 Research paper title
15:00 - 💡 Research summary (AI-generated)
16:30 - 💥 Chuck Norris fact
18:00 - 🎤 Kanye quote
19:30 - ✨ Affirmation
21:00 - 🏆 Trivia question
21:45 - 🏆 Trivia answer
23:00 - 📖 Wikipedia "On This Day"
... (continues with more variety)
57:00 - 🔬 Science headline
58:00 - 💡 Science summary (AI-generated)
59:50 - 🎉 Closing message
```

## Technical Details

### Story Generation Flow

1. **Fetch Story**: Try News API → Hacker News → arXiv
2. **Check Uniqueness**: Skip if already used in this workout
3. **Generate Summary**: Send headline + description to Gemini AI
4. **Simplify**: AI creates 1-2 sentence plain-language explanation (max 150 chars)
5. **Format**: Add emoji indicators (💡 for summaries)
6. **Pair**: Schedule summary 60 seconds after headline

### AI Summary Prompt

```
Explain this story in simple, clear language that someone
exercising can understand:

Headline: [headline]
Description: [description]

Provide a 1-2 sentence summary (max 150 characters) explaining
what this story means in simple terms. Make it conversational
and easy to understand while riding a bike.
```

### Deduplication

- Tracks used messages in `used_messages` set
- Tracks used story headlines in `used_stories` set
- Prevents repetition within a single workout
- Resets between workouts

## Files Modified

1. **src/utils/zwift_workout_generator.py**

   - Increased `num_messages` calculation (20-30 events)
   - Changed message interval (90 seconds instead of 180)
   - Added story pair handling (every 6th message)
   - Adjusted trivia frequency (every 5th instead of 4th)

2. **src/utils/dynamic_workout_content.py**
   - Added `used_stories` tracking
   - Added `get_story_with_summary()` method
   - Added `_get_news_api_story()` for News API integration
   - Added `_get_science_headline_full()` for enhanced science stories
   - Added `_get_arxiv_story_full()` for research papers with abstracts
   - Added `_generate_story_summary()` for AI summarization
   - Updated `reset_used_messages()` to clear story tracking

## Benefits

### For You:

✅ **More entertainment** - Double the text events means less boredom
✅ **Better understanding** - AI summaries make complex stories accessible
✅ **Stay informed** - Learn about current events while training
✅ **Mental distraction** - More content = less focus on suffering
✅ **Variety** - 12+ content sources ensure fresh content every workout

### Technical:

✅ **No repetition** - Deduplication ensures unique content per workout
✅ **Graceful fallback** - Works without News API key
✅ **Smart timing** - 60-second gap for story pairs (read → understand)
✅ **Rate limiting** - Respects API quotas
✅ **Error handling** - Falls back to other sources if one fails

## Testing

To test the enhancements, generate a new workout:

```bash
# Your normal workout generation command
# Will automatically include enhanced text events
```

You should see:

- More frequent text events (every 1-2 minutes)
- Science headlines followed by summaries
- News stories followed by explanations
- All existing content types still working

## Future Enhancement Ideas

Want even more? Consider:

- 🏋️ Workout tips during intervals
- 📊 Personal PR reminders
- 🎵 Song lyrics or music facts
- 🌍 Geographic facts
- 🍕 Food/nutrition tips
- 📅 Historical events
- 🎬 Movie quotes

Let me know what sounds interesting!

## Troubleshooting

**Q: Not seeing news stories?**

- Check if `NEWS_API_KEY` is set
- Free tier limited to 100 requests/day
- Will fallback to Hacker News/arXiv automatically

**Q: Summaries seem generic?**

- Ensure `GEMINI_API_KEY` is configured
- Check API quota hasn't been exceeded
- System will skip summary if AI unavailable

**Q: Want even more text events?**

- Currently capped at 30 max to avoid overwhelming
- Can adjust in code if desired

**Q: Stories repeating?**

- Deduplication is per-workout only
- Will see same stories across different workouts (that's expected)
- Stories rotate based on what's trending/recent
