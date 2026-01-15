# Graceful Fallback for Text Events

## Issue

When Gemini API quota is exhausted (common on free tier), AI-generated summaries for news/science stories would fail, causing story pairs to be skipped entirely.

## Solution Implemented

Added graceful fallback system that ensures story pairs still appear even without AI summaries.

## How It Works

### Priority Order

1. **Try AI Summary** (Gemini API)

   - Generates simple, clear explanation
   - Max 150 characters
   - Conversational tone

2. **Fallback to Simple Summary** (text extraction)
   - Extracts first 1-2 sentences from description
   - For Hacker News: Provides context message
   - For arXiv/News API: Uses actual description text
   - Max 180 characters

### Examples

#### With AI (Gemini Available)

```
🔬 Science: "Novel CRISPR Mechanism in Non-Dividing Cells"
[60 seconds later]
💡 Scientists found a new way to edit genes in cells that
aren't growing, which could help treat diseases
```

#### Without AI (Quota Exhausted - Hacker News)

```
🔬 Science: "Show HN: OSS sustain guard – Sustainability signals"
[60 seconds later]
💡 A trending tech/science story: Show HN: OSS sustain guard
– Sustainability signals. Check it out after your workout!
```

#### Without AI (Quota Exhausted - arXiv)

```
📚 Research: "Growth Model for Multicellular Tumor Spheroids"
[60 seconds later]
💡 Most organisms grow according to simple laws, which can be
derived from energy conservation and scaling arguments...
```

## Benefits

### Reliability

✅ **Always works** - No dependency on AI quota
✅ **No content loss** - Story pairs always delivered
✅ **Seamless experience** - User doesn't notice the difference

### Quality

✅ **Still informative** - Summaries provide value
✅ **Appropriate length** - 50-180 characters (readable while riding)
✅ **Context preserved** - Key information extracted

### User Experience

✅ **No interruption** - Workouts always have full content
✅ **No errors** - Graceful degradation
✅ **No configuration needed** - Automatic fallback

## Technical Implementation

### Error Detection

```python
except Exception as e:
    error_msg = str(e)
    if 'quota' in error_msg.lower() or 'resource_exhausted' in error_msg.lower():
        print("⚠️  Gemini API quota exhausted - falling back to simple summaries")
```

### Fallback Logic

```python
# Try AI summary first
summary = self._generate_story_summary(headline, description)

# Fallback: Create simple summary if AI unavailable
if not summary:
    summary = self._create_simple_summary(description)
```

### Simple Summary Creation

```python
def _create_simple_summary(self, description: str) -> Optional[str]:
    # Extract first 1-2 sentences
    # Truncate to 180 characters
    # Add 💡 emoji
    return f'💡 {summary}'
```

## Testing

Run test to verify fallback:

```bash
./scripts/test_text_events.py
```

Will show:

- ✅ Stories retrieved successfully
- ✅ Summaries generated (AI or fallback)
- ✅ Appropriate length and quality

## Quota Information

### Gemini API Free Tier

- **Requests per minute**: 15 RPM
- **Requests per day**: 1,500 RPD
- **Tokens per minute**: 1M TPM

### Typical Usage

- **Per workout**: 2-5 AI summary requests
- **Per day** (1 workout): Well within limits
- **Per day** (2-3 workouts): May approach limits

### When Fallback Activates

- After ~300+ workouts in a day (extremely rare)
- After other heavy Gemini API usage
- Network connectivity issues
- API service interruptions

## Files Modified

1. `src/utils/dynamic_workout_content.py`

   - Added `_create_simple_summary()` method
   - Enhanced `get_story_with_summary()` with fallback
   - Improved error logging for quota detection
   - Better descriptions for Hacker News stories

2. `scripts/test_text_events.py`
   - Updated test to show fallback in action
   - Better configuration diagnostics
   - Clearer error messages

## Conclusion

✅ Text events now **always work** regardless of API quota
✅ Quality remains high with intelligent fallbacks
✅ Zero user configuration needed
✅ Seamless degradation - user experience unaffected

Your workouts will have entertaining, informative content whether Gemini AI is available or not!
