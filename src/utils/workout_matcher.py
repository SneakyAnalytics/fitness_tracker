"""
AI-Powered Workout Matching
Uses AI to intelligently match actual workouts to proposed workouts when multiple exist on same day.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import google.generativeai as genai
from google.generativeai.types import generation_types
from google.api_core import exceptions
import os


class WorkoutMatcher:
    """Uses AI to match actual workouts to proposed workouts"""
    
    # Static fallback models (used if dynamic discovery fails)
    FALLBACK_MODELS = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-flash-latest',
        'gemini-1.5-flash-002',
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b',
        'gemini-pro-latest',
    ]
    
    def __init__(self, use_dynamic_models: bool = True):
        """
        Initialize with Gemini API
        
        Args:
            use_dynamic_models: If True, dynamically discover free models. If False, use static list.
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        
        # Get model list (dynamic or static)
        self.use_dynamic_models = use_dynamic_models
        self._models_cache: Optional[List[str]] = None
    
    @property
    def MODELS(self) -> List[str]:
        """
        Get list of models to try.
        
        Uses dynamic discovery if enabled, otherwise returns static fallback.
        Caches the result to avoid repeated API calls.
        """
        if self._models_cache is not None:
            return self._models_cache
        
        if self.use_dynamic_models:
            try:
                from .gemini_model_discovery import get_best_free_models
                print("🔍 Using dynamic model discovery for workout matching...")
                models = get_best_free_models(max_models=7, force_refresh=False)
                self._models_cache = models
                return models
            except Exception as e:
                print(f"⚠️  Dynamic model discovery failed: {e}")
                print("📋 Falling back to static model list")
        
        # Use static fallback
        self._models_cache = self.FALLBACK_MODELS
        return self.FALLBACK_MODELS
    
    def match_workouts_for_day(
        self,
        actual_workouts: List[Dict[str, Any]],
        proposed_workouts: List[Dict[str, Any]],
        date: str
    ) -> Dict[int, str]:
        """
        Use AI to match actual workouts to proposed workouts.
        
        Args:
            actual_workouts: List of actual workout dicts with id, title, TSS, duration, comments
            proposed_workouts: List of proposed workout dicts with name, TSS, duration, notes
            date: The date these workouts occurred
            
        Returns:
            Dictionary mapping actual workout IDs to proposed workout names
        """
        if not actual_workouts or not proposed_workouts:
            return {}
        
        # Format data for AI
        actual_list = []
        for w in actual_workouts:
            actual_list.append({
                'id': w['id'],
                'title': w['title'],
                'tss': round(w.get('tss', 0), 1),
                'duration_min': round(w.get('duration_min', 0), 1),
                'athlete_comments': w.get('athlete_comments', ''),
                'sport': w.get('sport', 'cycling')
            })
        
        proposed_list = []
        for p in proposed_workouts:
            proposed_list.append({
                'name': p['name'],
                'type': p.get('type', 'bike'),
                'tss_range': f"{p.get('plannedTSS_min', 0)}-{p.get('plannedTSS_max', 0)}",
                'duration_min': p.get('plannedDuration', 0),
                'notes': p.get('notes', ''),
                'description': p.get('description', '')
            })
        
        prompt = f"""You are matching actual completed workouts to planned workouts for {date}.

ACTUAL WORKOUTS COMPLETED:
{json.dumps(actual_list, indent=2)}

PROPOSED WORKOUTS PLANNED:
{json.dumps(proposed_list, indent=2)}

**MATCHING INSTRUCTIONS (PRIORITY ORDER):**

1. **INTENSITY FIRST** - Match intensity characteristics before duration/TSS:
   - High TSS/short duration (40-80 TSS in 20-45min) = RACE, VO2max, or Threshold intervals
   - High TSS/long duration (100+ TSS in 90+ min) = Long endurance ride  
   - Low TSS/short duration (<15 TSS in 10-30min) = Warmup or recovery spin
   - Moderate TSS/moderate duration (40-70 TSS in 60-90min) = Tempo or Zone 2

2. **Title clues**: "Pre-Group Ride", "warmup", "recovery", "spin" vs "Race", "TTT", "Threshold", "VO2"

3. **Athlete comments**: Look for context like "pre-race warmup" or "main event" or "stopped early due to injury"

4. **Duration patterns**: 
   - 5-15min = Warmup (NOT a main workout)
   - 20-45min = Short high-intensity session OR warmup
   - 60-90min = Main workout
   - 90+ min = Long endurance

5. **Workout type in proposed name**:
   - "Zone 2", "Endurance", "Recovery" = LOW intensity, LONG duration
   - "VO2max", "Threshold", "Race" = HIGH intensity, SHORTER duration
   - "Tempo" = Moderate intensity, moderate duration

6. **Logical flow**: Warmup workouts come BEFORE main events on same day

**CRITICAL RULES TO PREVENT MISMATCHES:**

❌ **NEVER** match a short high-TSS workout (race/intervals) to a long low-intensity Zone 2 ride
❌ **NEVER** match a 10-30min workout to a 2+ hour workout (huge duration mismatch)
❌ **NEVER** match 2 short workouts to 1 long workout - they're separate events
✅ **ALWAYS** match warmups to warmup workouts (look for "warmup", "pre-", "spin" in title)
✅ **ALWAYS** check if athlete stopped early (injury/mechanical) - use TSS to match, not planned duration
✅ **ALWAYS** prioritize BACKUP/OPTION B workouts if main workout clearly didn't happen

**EXAMPLE SCENARIOS:**

- 15min, 10 TSS "Pre-race warmup" → Match to "Pre-Race Warmup" (NOT to "2hr Zone 2 Ride")
- 30min, 50 TSS "Race - stopped early" → Match to "Race" workout (NOT to "Zone 2" ride)
- 90min, 120 TSS "Sunday long ride" → Match to "Zone 2 Endurance" (NOT to "VO2max intervals")
- "BACKUP" workout exists but no matching TSS/duration → Use null (didn't do it)

**OUTPUT FORMAT:**
Return ONLY a JSON object mapping actual workout IDs to proposed workout names:
{{
  "1": "Proposed Workout Name",
  "2": "Another Proposed Workout Name"
}}

If an actual workout doesn't match any proposed workout well (like a spontaneous ride), use null:
{{
  "1": null
}}

Return ONLY the JSON, no explanation."""

        # Try each model in the list until one works
        last_error = None
        for model_name in self.MODELS:
            try:
                print(f"🤖 Attempting workout matching with model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                result_text = response.text.strip()
                
                # Clean up markdown code blocks if present
                if result_text.startswith('```'):
                    result_text = result_text.split('```')[1]
                    if result_text.startswith('json'):
                        result_text = result_text[4:]
                    result_text = result_text.strip()
                
                # Parse JSON response
                matches = json.loads(result_text)
                
                # Convert string keys to int
                result = {int(k): v for k, v in matches.items()}
                print(f"✅ Successfully matched workouts with {model_name}")
                return result
                
            except exceptions.ResourceExhausted as e:
                print(f"⚠️  Quota exceeded for {model_name}, trying next model...")
                last_error = f"Quota exceeded: {str(e)}"
                continue
            except exceptions.InvalidArgument as e:
                print(f"⚠️  Model {model_name} not available or invalid: {str(e)}")
                last_error = f"Invalid model: {str(e)}"
                continue
            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse JSON from {model_name}: {str(e)}")
                last_error = f"JSON parse error: {str(e)}"
                continue
            except Exception as e:
                print(f"⚠️  Error with {model_name}: {type(e).__name__}: {str(e)}")
                last_error = f"{type(e).__name__}: {str(e)}"
                # Try next model for any error
                continue
        
        # If we get here, all models failed
        print(f"❌ Could not match workouts - all {len(self.MODELS)} models failed.")
        print(f"Last error: {last_error}")
        print(f"Tried models: {', '.join(self.MODELS)}")
        print("📊 Falling back to TSS+duration matching...")
        # Fall back to simple TSS+duration matching
        return self._fallback_matching(actual_workouts, proposed_workouts)
    
    def _fallback_matching(
        self,
        actual_workouts: List[Dict[str, Any]],
        proposed_workouts: List[Dict[str, Any]]
    ) -> Dict[int, str]:
        """Fallback to TSS+duration matching if AI fails"""
        matches = {}
        available_proposed = proposed_workouts.copy()
        
        for actual in actual_workouts:
            best_match = None
            best_score = 999999
            
            for proposed in available_proposed:
                tss_actual = actual.get('tss', 0)
                tss_proposed_avg = (proposed.get('plannedTSS_min', 0) + proposed.get('plannedTSS_max', 0)) / 2
                dur_actual = actual.get('duration_min', 0)
                dur_proposed = proposed.get('plannedDuration', 0)
                
                tss_diff = abs(tss_actual - tss_proposed_avg)
                dur_diff = abs(dur_actual - dur_proposed)
                score = tss_diff + dur_diff
                
                if score < best_score:
                    best_score = score
                    best_match = proposed
            
            if best_match and best_score < 30:  # Reasonable threshold
                matches[actual['id']] = best_match['name']
                available_proposed.remove(best_match)
            else:
                matches[actual['id']] = None
        
        return matches
