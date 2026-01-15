# Text Event Enhancements - Quick Start

## What Changed? 🎉

Your Zwift workout text events are now **2x more frequent** and **way more informative**!

### Before vs After

| Feature                | Before                        | After                          |
| ---------------------- | ----------------------------- | ------------------------------ |
| **Frequency**          | 10-15 events/workout          | 20-30 events/workout           |
| **Spacing**            | Every 3 minutes               | Every 1-2 minutes              |
| **Science headlines**  | Just the headline (confusing) | Headline + AI summary (clear!) |
| **News stories**       | None                          | Trending news + summaries      |
| **Story explanations** | None                          | AI-generated plain language    |

## New Content Types

### 📰 Current Events (NEW!)

```
📰 News: "Major Breakthrough in Fusion Energy Announced"
[60 seconds later]
💡 A lab created more energy from fusion than it used for
the first time ever - big step toward clean unlimited power
```

### 🔬 Science Stories (ENHANCED!)

```
🔬 Science: "Novel CRISPR Mechanism Enables Precise Genome
Editing in Non-Dividing Cells"
[60 seconds later]
💡 Scientists found a new way to edit genes in cells that
aren't growing, which could help treat diseases
```

### 📚 Research Papers (ENHANCED!)

```
📚 Research: "Quantum Error Correction in Superconducting Qubits"
[60 seconds later]
💡 New method helps quantum computers fix their own errors,
making them more reliable for real-world use
```

## Setup (Optional but Recommended)

### You Already Have:

✅ Gemini AI (for summaries) - configured

### Optional Enhancement:

🆕 **News API** - Add trending news headlines

**Quick setup:**

```bash
./scripts/setup_news_api.sh
```

Or manually:

1. Get free key: https://newsapi.org/register
2. Add to environment:
   ```bash
   export NEWS_API_KEY="your_key_here"
   ```

**Free tier**: 100 requests/day (plenty for workouts)

## What You'll Experience

During your next workout, you'll see:

### More Frequent Messages

- Text event every 1-2 minutes (was 2-3 minutes)
- 20-30 total messages per workout (was 10-15)
- Better mental distraction during hard efforts

### Story Pairs (Headline + Summary)

- **Story shown** (e.g., science headline)
- **60 seconds pass** (time to read and think)
- **Summary shown** (AI explains it simply)

### Content Mix

- 📰 News stories with summaries (~15%)
- 🏆 Sports trivia Q&A (~15%)
- 💬 Quotes, jokes, facts (~70%)

## Example Workout Timeline

60-minute workout might include:

```
0:05  - 🎯 "Ready to build some power? Let's ride!"
2:00  - 💬 "Success is not final, failure is not fatal..." - Churchill
3:30  - 😄 "Why do bicycles fall over? They're two tired!"
5:00  - 🏆 Trivia: "Which cyclist won the most Tour de France titles?"
5:45  - 🏆 Answer: "Lance Armstrong (later stripped)"
7:00  - 📰 News: "Scientists Discover New Cancer Treatment"
8:00  - 💡 "Researchers found a drug that targets cancer cells..."
9:30  - 🤓 Fun Fact: "Honey never spoils. Edible honey was found..."
11:00 - 💪 "Every pedal stroke is building your future strength"
12:30 - 🔢 "42 is the answer to life, the universe, and everything"
14:00 - 📚 Research: "Machine Learning Predicts Protein Structures"
15:00 - 💡 "AI can now predict how proteins fold, helping drug discovery"
... (and so on!)
```

## Technical Details

### Content Sources (12+ APIs)

- ✅ Quotes (Quotable API)
- ✅ Jokes (icanhazdadjoke, Official Joke API)
- ✅ Fun Facts (Useless Facts API)
- ✅ Number Facts (Numbers API)
- ✅ Advice (Advice Slip)
- ✅ Affirmations (Affirmations.dev)
- ✅ Chuck Norris Facts
- ✅ Kanye Quotes
- ✅ Sports Trivia (Open Trivia DB)
- ✅ Science Headlines (Hacker News)
- ✅ Research Papers (arXiv)
- ✅ Wikipedia "On This Day"
- 🆕 News Headlines (News API - optional)

### AI Summary Generation

- Uses Gemini Flash (fast, efficient)
- Max 150 characters (quick to read while riding)
- Plain language (no jargon)
- Conversational tone

### Smart Features

- ✅ No repetition within workout
- ✅ Story pairs guaranteed (headline + summary)
- ✅ 60-second gap (time to process headline)
- ✅ Graceful fallback (works without News API)
- ✅ Error handling (skips broken APIs)

## Benefits

### Physical

- 🧠 **Mental distraction** from hard efforts
- ⏱️ **Time passes faster** with frequent content
- 💪 **Stay motivated** with varied messaging

### Mental

- 📚 **Learn while training** (science, news, facts)
- 🧩 **Engage your brain** (trivia, jokes)
- 😄 **Stay entertained** (variety prevents boredom)

## Files Modified

1. `src/utils/zwift_workout_generator.py`

   - Increased frequency (20-30 events)
   - Added story pair logic

2. `src/utils/dynamic_workout_content.py`
   - Added News API integration
   - Added AI summary generation
   - Enhanced story fetching

## Next Steps

1. **Optional**: Set up News API

   ```bash
   ./scripts/setup_news_api.sh
   ```

2. **Generate a workout** (your normal process)

   - Text events automatically enhanced
   - No code changes needed

3. **Try it out!**
   - Notice more frequent messages
   - Look for story pairs (headline → summary)
   - Enjoy the variety!

## Questions?

**Q: Can I get even MORE text events?**
A: Currently capped at 30 to avoid overwhelming you. Can adjust if desired.

**Q: Do I NEED the News API?**
A: No! Works great without it. Just falls back to HackerNews/arXiv (still excellent content).

**Q: Will summaries work without Gemini?**
A: No - Gemini API key required for AI summaries. But you already have it configured! ✅

**Q: What if I want fewer events?**
A: Easy to adjust - just let me know your preferred frequency.

## Feedback Welcome!

Let me know:

- Is the frequency good? (too much/little?)
- Are summaries helpful and clear?
- Want any other content types?
- Anything confusing?

Enjoy your enhanced workouts! 🚴‍♂️💨
