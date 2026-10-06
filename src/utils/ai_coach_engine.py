"""
🤖 AI Coach Engine - Core Orchestration
========================================
Orchestrates AI coaching workflow: Analysis → Generation → Validation

🎓 EDUCATIONAL NOTE - AI Orchestration Patterns:
-------------------------------------------------

**What is Orchestration?**
Coordinating multiple AI calls and data processing steps into a workflow.

**Why Multiple Steps?**
Complex tasks need breakdown:
1. Analysis (understand situation)
2. Generation (create solution)
3. Validation (check correctness)

Single big prompt → poor quality, hard to debug
Multiple focused prompts → better results, easier to fix

**Design Patterns:**

1. **Sequential Pipeline**
   Step 1 → Step 2 → Step 3
   Each step feeds next
   Clean, predictable

2. **Parallel Fan-Out**
   Generate multiple options → Pick best
   Slower but higher quality

3. **Feedback Loop**
   Generate → Validate → If bad, regenerate
   Self-correcting

We use: Sequential + Feedback (generate, validate, fix if needed)

**Error Handling:**
- API failures (retry with backoff)
- JSON parse errors (ask AI to fix)
- Validation failures (regenerate with corrections)
- Cost tracking (prevent runaway spending)
"""

import json
import time
import random
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import re

# Import our components
try:
    from .ai_coach_config import AIModel, AICoachConfig
    from .ai_prompts import AICoachPrompts, PromptContext
    from .coaching_notes import CoachingNotesManager
    from .ai_database_queries import AICoachDatabaseQueries
except ImportError:
    from ai_coach_config import AIModel, AICoachConfig
    from ai_prompts import AICoachPrompts, PromptContext
    from coaching_notes import CoachingNotesManager
    from ai_database_queries import AICoachDatabaseQueries

# API clients
try:
    import google.generativeai as genai
    from anthropic import Anthropic, InternalServerError, APIError, RateLimitError
    APIS_AVAILABLE = True
except ImportError:
    APIS_AVAILABLE = False
    print("⚠️  Warning: google-generativeai or anthropic not installed")
    print("   Install with: pip install google-generativeai anthropic")

# GitHub Models uses the OpenAI-compatible SDK
try:
    from openai import OpenAI as _OpenAIClient
    _OPENAI_SDK_AVAILABLE = True
except ImportError:
    _OPENAI_SDK_AVAILABLE = False

import os as _os_env  # for GITHUB_MODEL env var overrides
_GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"
# Actual model IDs on GitHub Models — override via env if needed
def _github_model_id(model):
    """Return the upstream model name to pass to the GitHub Models endpoint."""
    defaults = {
        "github-gpt4o-mini": "gpt-4o-mini",
        "github-gpt4o":      "gpt-4o",
    }
    env_override = {
        "github-gpt4o-mini": _os_env.getenv("GITHUB_FAST_MODEL"),
        "github-gpt4o":      _os_env.getenv("GITHUB_BEST_MODEL"),
    }
    return env_override.get(model.value) or defaults.get(model.value, model.value)


@dataclass
class CoachingResult:
    """
    Result of a coaching session.
    
    Educational note: Why return structured data?
    - Easy to serialize/save
    - Type-safe access
    - Can track metadata (cost, time, etc.)
    """
    success: bool
    analysis: Optional[str] = None
    workout_plan: Optional[Dict] = None
    errors: Optional[List[str]] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class AICoachEngine:
    """
    Main AI coaching orchestration engine.
    
    Educational walkthrough:
    1. Initialize with model selection
    2. Load athlete data (profile, history, etc.)
    3. Analyze recent training
    4. Generate workout plan
    5. Validate and save results
    """
    
    def __init__(self, model: AIModel = AIModel.GEMINI_FREE,
                 coaching_notes_path: Optional[Path] = None):
        """
        Initialize AI coach engine.
        
        Args:
            model: Which AI model to use
            coaching_notes_path: Path to coaching notes JSON
        """
        self.model = model
        self.config = AICoachConfig()
        
        # Initialize components
        self.prompts = AICoachPrompts()
        self.db_queries = AICoachDatabaseQueries()
        self.coaching_notes = CoachingNotesManager(coaching_notes_path)
        
        # Setup API client
        self._setup_api_client()
        
        # Track costs and calls
        self.session_cost = 0.0
        self.api_calls = []
    
    def _setup_api_client(self):
        """
        Setup API client based on selected model.
        
        Educational note: API Client Patterns
        
        Different APIs, different clients:
        - Google: genai.GenerativeModel
        - Anthropic: Anthropic client
        - OpenAI: OpenAI client (if we add it)
        
        Pattern: Abstract away differences, expose simple interface
        """
        if not APIS_AVAILABLE:
            self.client = None
            print("⚠️  APIs not available - running in demo mode")
            return
        
        api_key = self.config.get_api_key(self.model)
        
        if not api_key:
            raise ValueError(f"No API key found for {self.model.value}")
        
        if self.model in [AIModel.GEMINI_FREE, AIModel.GEMINI_FLASH_LITE, AIModel.GEMINI_PRO]:
            # Google Gemini — model name comes straight from the enum, which uses
            # Google's rolling "-latest" aliases so this doesn't go stale again.
            genai.configure(api_key=api_key)
            model_name = self.model.value
            self.client = genai.GenerativeModel(model_name)
            print(f"✅ Configured {model_name}")

        elif self.model in [AIModel.CLAUDE_HAIKU, AIModel.CLAUDE_SONNET]:
            # Anthropic Claude
            self.client = Anthropic(api_key=api_key)
            print(f"✅ Configured {self.model.value}")

        elif self.model in [AIModel.GITHUB_GPT4O_MINI, AIModel.GITHUB_GPT4O]:
            # GitHub Models — OpenAI-compatible endpoint using GitHub token
            if not _OPENAI_SDK_AVAILABLE:
                raise ImportError(
                    "openai package required for GitHub Models. "
                    "Install with: pip install openai>=1.50.0"
                )
            self.client = _OpenAIClient(
                base_url=_GITHUB_MODELS_URL,
                api_key=api_key,
            )
            self._github_model_name = _github_model_id(self.model)
            print(f"✅ Configured GitHub Models → {self._github_model_name} (with Anthropic fallback if available)")

        else:
            raise ValueError(f"Unsupported model: {self.model}")
    
    def _call_api(self, prompt: str, temperature: float = 0.7,
                  max_tokens: int = 4000) -> Tuple[str, Dict]:
        """
        Make API call to LLM.
        
        Educational note: Temperature Parameter
        
        Temperature (0.0 - 2.0) controls randomness:
        - 0.0: Deterministic, same output every time
        - 0.7: Balanced creativity and consistency
        - 1.5: Very creative, more varied outputs
        
        Use low temp for: JSON generation, factual analysis
        Use high temp for: Creative writing, brainstorming
        
        Args:
            prompt: The prompt to send
            temperature: Randomness (0-2)
            max_tokens: Maximum response length
        
        Returns:
            (response_text, metadata)
        """
        if not self.client:
            # Demo mode - return mock response
            return self._mock_response(prompt), {'demo': True}
        
        start_time = time.time()
        
        try:
            if self.model in [AIModel.GEMINI_FREE, AIModel.GEMINI_FLASH_LITE, AIModel.GEMINI_PRO]:
                # Google Gemini API
                # Set safety settings to allow fitness/health content
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                response = self.client.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                    safety_settings=safety_settings
                )
                
                # Check if response was blocked
                if not response.candidates:
                    raise ValueError(f"Response blocked. Finish reason: {response.prompt_feedback}")
                
                # Get text, handling potential blocks
                try:
                    response_text = response.text
                except ValueError as e:
                    # Response was blocked - check why
                    if response.candidates:
                        finish_reason = response.candidates[0].finish_reason
                        safety_ratings = response.candidates[0].safety_ratings
                        raise ValueError(f"Response blocked. Reason: {finish_reason}, Safety: {safety_ratings}")
                    raise
                
                finish_reason = None
                if response.candidates and response.candidates[0].finish_reason:
                    finish_reason = str(response.candidates[0].finish_reason)

                # Extract token usage if available
                metadata = {
                    'model': self.model.value,
                    'latency': time.time() - start_time,
                    'prompt_tokens': len(prompt) // 4,  # Rough estimate
                    'completion_tokens': len(response_text) // 4,
                    'finish_reason': finish_reason,
                }
            
            elif self.model in [AIModel.CLAUDE_HAIKU, AIModel.CLAUDE_SONNET]:
                # Anthropic Claude API with retry logic for 500 errors
                model_name = self.model.value

                # Retry configuration for transient API errors
                max_retries = 3
                base_delay = 2  # seconds

                for attempt in range(max_retries):
                    try:
                        response = self.client.messages.create(
                            model=model_name,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            messages=[
                                {"role": "user", "content": prompt}
                            ]
                        )

                        response_text = response.content[0].text
                        finish_reason = getattr(response, 'stop_reason', None)

                        metadata = {
                            'model': self.model.value,
                            'latency': time.time() - start_time,
                            'prompt_tokens': response.usage.input_tokens,
                            'completion_tokens': response.usage.output_tokens,
                            'finish_reason': finish_reason,
                            'retries': attempt
                        }

                        break  # Success, exit retry loop

                    except InternalServerError as e:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"⚠️  Anthropic API 500 error (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                            time.sleep(delay)
                        else:
                            print(f"❌ Anthropic API failed after {max_retries} attempts")
                            raise

                    except (RateLimitError, APIError) as e:
                        print(f"❌ Anthropic API error: {type(e).__name__}: {str(e)}")
                        raise

            elif self.model in [AIModel.GITHUB_GPT4O_MINI, AIModel.GITHUB_GPT4O]:
                # GitHub Models — OpenAI-compatible endpoint, with Anthropic direct fallback
                # Hard-cap at 4000 tokens (GitHub Models limit for high-tier models)
                gh_model = self._github_model_name
                gh_max_tokens = min(max_tokens, 4000)
                try:
                    gh_response = self.client.chat.completions.create(
                        model=gh_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=gh_max_tokens,
                    )
                    finish_reason = gh_response.choices[0].finish_reason
                    # Treat a truncated response as a failure — fall through to Anthropic
                    if finish_reason == "length":
                        used = gh_response.usage.completion_tokens if gh_response.usage else "?"
                        raise RuntimeError(
                            f"GitHub Models response truncated at token limit "
                            f"(finish_reason=length, {used}/{gh_max_tokens} output tokens). "
                            f"Falling back to Anthropic for complete response."
                        )
                    response_text = gh_response.choices[0].message.content
                    usage = gh_response.usage
                    metadata = {
                        'model': f"github/{gh_model}",
                        'latency': time.time() - start_time,
                        'prompt_tokens': usage.prompt_tokens if usage else len(prompt) // 4,
                        'completion_tokens': usage.completion_tokens if usage else len(response_text) // 4,
                        'finish_reason': finish_reason,
                        'provider': 'github',
                    }
                except Exception as gh_err:
                    fallback_key = self.config.claude_api_key
                    if fallback_key:
                        print(f"⚠️  GitHub Models failed ({type(gh_err).__name__}: {gh_err}), falling back to direct Anthropic API...")
                        fb_client = Anthropic(api_key=fallback_key)
                        fb_model = "claude-sonnet-4-6"
                        fb_resp = fb_client.messages.create(
                            model=fb_model,
                            max_tokens=max_tokens,  # use original uncapped limit
                            temperature=temperature,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        response_text = fb_resp.content[0].text
                        metadata = {
                            'model': f"anthropic-fallback/{fb_model}",
                            'latency': time.time() - start_time,
                            'prompt_tokens': fb_resp.usage.input_tokens,
                            'completion_tokens': fb_resp.usage.output_tokens,
                            'finish_reason': fb_resp.stop_reason,
                            'provider': 'anthropic_fallback',
                        }
                    else:
                        raise

            else:
                raise ValueError(f"Unsupported model: {self.model}")
            
            # Calculate cost (rough estimate based on model pricing)
            # Gemini Flash: Free, Pro: ~$0.00025 per 1K tokens
            # Claude Haiku: ~$0.00025 per 1K tokens, Sonnet: ~$0.003 per 1K tokens
            total_tokens = metadata['prompt_tokens'] + metadata['completion_tokens']
            if self.model in [AIModel.GEMINI_FREE, AIModel.GEMINI_FLASH_LITE]:
                cost = 0.0  # Free tier
            elif self.model == AIModel.GEMINI_PRO:
                cost = (total_tokens / 1000) * 0.00025
            elif self.model == AIModel.CLAUDE_HAIKU:
                cost = (total_tokens / 1000) * 0.00025
            elif self.model == AIModel.CLAUDE_SONNET:
                cost = (total_tokens / 1000) * 0.003
            else:
                cost = 0.0
            
            metadata['cost'] = cost
            self.session_cost += cost
            
            # Track call
            self.api_calls.append({
                'timestamp': datetime.now().isoformat(),
                'model': self.model.value,
                'tokens': metadata['prompt_tokens'] + metadata['completion_tokens'],
                'cost': cost
            })
            
            return response_text, metadata
        
        except Exception as e:
            print(f"❌ API call failed: {e}")
            raise
    
    def _mock_response(self, prompt: str) -> str:
        """Return mock response for demo mode."""
        if "Analyze This Week's Training" in prompt:
            return """## Week Summary
Good week with consistent training. TSS accumulation appropriate for current fitness level.

## Key Observations
- Completed 6/8 planned workouts (75% compliance)
- Power trends showing improvement in endurance sessions
- Recovery workouts appropriately executed

## Performance Highlights
- Endurance power improving (steady upward trend)
- Good consistency with recovery protocol

## Areas for Attention
- Slightly lower compliance than ideal
- Could benefit from one additional threshold session

## Recommendations for Next Week
- Maintain current endurance volume
- Add one threshold session mid-week
- Keep recovery emphasis high

## Coaching Note
Athlete responding well to current training load. Continue progressive approach."""
        else:
            return '{"weekNumber": 52, "startDate": "2025-11-18", "ftp": 300, "plannedTSS": {"min": 400, "max": 500}, "notes": {"weekFocus": "Base building", "specialConsiderations": "Monitor recovery"}, "days": []}'
    
    def _call_api_streaming(self, prompt: str, temperature: float = 0.7,
                            max_tokens: int = 4000):
        """
        Streaming variant of _call_api.  Yields text chunks as a generator so
        callers can pass it directly to st.write_stream().

        Anthropic: client.messages.stream() context manager
        Gemini:    generate_content(stream=True)
        Demo mode: yields the mock response in one chunk
        """
        if not self.client:
            yield self._mock_response(prompt)
            return

        if self.model in [AIModel.GEMINI_FREE, AIModel.GEMINI_FLASH_LITE, AIModel.GEMINI_PRO]:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            response = self.client.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
                safety_settings=safety_settings,
                stream=True,
            )
            for chunk in response:
                try:
                    text = chunk.text
                    if text:
                        yield text
                except Exception:
                    pass

        elif self.model in [AIModel.CLAUDE_HAIKU, AIModel.CLAUDE_SONNET]:
            model_name = self.model.value
            max_retries = 3
            base_delay = 2
            for attempt in range(max_retries):
                try:
                    with self.client.messages.stream(
                        model=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}],
                    ) as stream:
                        for text in stream.text_stream:
                            yield text
                    break
                except InternalServerError:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"⚠️  Anthropic stream 500 error (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        raise
                except (RateLimitError, APIError):
                    raise

        elif self.model in [AIModel.GITHUB_GPT4O_MINI, AIModel.GITHUB_GPT4O]:
            # GitHub Models streaming — buffer first to detect truncation before yielding.
            # If the response is cut off at the token limit we fall back to Anthropic
            # rather than surfacing a half-formed plan to the UI.
            gh_model = self._github_model_name
            gh_max_tokens = min(max_tokens, 4000)  # hard cap at GitHub Models limit
            fallback_key = self.config.claude_api_key
            try:
                stream = self.client.chat.completions.create(
                    model=gh_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=gh_max_tokens,
                    stream=True,
                )
                buffered = []
                finish_reason = None
                for chunk in stream:
                    if chunk.choices:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            buffered.append(delta)
                        if chunk.choices[0].finish_reason:
                            finish_reason = chunk.choices[0].finish_reason

                if finish_reason == "length":
                    print(f"⚠️  GitHub Models stream hit token limit (finish_reason=length, "
                          f"{len(buffered)} chunks buffered). Falling back to Anthropic...")
                    raise RuntimeError("response_truncated")

                # No truncation — stream out the buffered chunks
                for text in buffered:
                    yield text

            except Exception as gh_err:
                if fallback_key:
                    print(f"⚠️  GitHub Models stream failed ({type(gh_err).__name__}), falling back to direct Anthropic API...")
                    fb_client = Anthropic(api_key=fallback_key)
                    fb_model = "claude-sonnet-4-6"  # always use Sonnet 4.6 for fallback quality
                    with fb_client.messages.stream(
                        model=fb_model,
                        max_tokens=max_tokens,  # use original uncapped limit
                        temperature=temperature,
                        messages=[{"role": "user", "content": prompt}],
                    ) as fb_stream:
                        for text in fb_stream.text_stream:
                            yield text
                else:
                    raise

        else:
            raise ValueError(f"Unsupported model for streaming: {self.model}")

    def analyze_week(self, weekly_summary: Dict, 
                     comprehensive_context: Optional[Dict] = None,
                     user_context: Optional[Dict] = None) -> Tuple[str, Dict]:
        """
        Analyze completed training week.
        
        Educational note: Analysis Step
        
        Purpose: Understand before acting
        - What happened this week?
        - What patterns emerged?
        - What should guide next week?
        
        Output: Human-readable analysis (not JSON)
        Used as input for generation step
        
        Args:
            weekly_summary: Summary of completed week
            comprehensive_context: Historical training data
            user_context: Dict with optional keys:
                - schedule_constraints: str (e.g., "Tuesday race, Thursday chamber")
                - training_focus: str (e.g., "Building base for gravel events")
                - week_feedback: str (e.g., "Felt strong on Tuesday")
        
        Returns:
            (analysis_text, metadata)
        """
        print("📊 Analyzing training week...")
        
        # Get comprehensive context if not provided
        if comprehensive_context is None:
            comprehensive_context = self.db_queries.get_comprehensive_context(weeks_back=4)
        
        # Load athlete profile and notes
        athlete_profile = self.coaching_notes.athlete_profile.__dict__
        coaching_notes = {
            'personality': self.coaching_notes.personality.__dict__,
            'current_training_phase': self.coaching_notes.current_training_phase,
            'next_week_focus': self.coaching_notes.next_week_focus,
            'observations': [obs.__dict__ for obs in self.coaching_notes.observations]
        }
        
        # Build context (including user_context)
        context = PromptContext(
            athlete_profile=athlete_profile,
            coaching_notes=coaching_notes,
            weekly_summary=weekly_summary,
            comprehensive_context=comprehensive_context,
            focus_topics={'periodization', 'recovery', 'training', 'endurance', 'threshold'},
            user_context=user_context or {}
        )
        
        # Build prompt
        prompt = self.prompts.build_weekly_analysis_prompt(context)
        
        print(f"  Prompt: ~{self.prompts.estimate_prompt_tokens(prompt):,} tokens")
        
        # Call API with lower temperature (more analytical)
        analysis, metadata = self._call_api(prompt, temperature=0.5, max_tokens=8000)
        
        print(f"  Response: ~{metadata.get('completion_tokens', 0):,} tokens")
        print(f"  Cost: ${metadata.get('cost', 0):.4f}")

        # Auto-update training phase based on recent distribution
        suggested_phase = self._infer_training_phase(comprehensive_context)
        if suggested_phase:
            metadata['suggested_training_phase'] = suggested_phase
            if suggested_phase != self.coaching_notes.current_training_phase:
                self.coaching_notes.update_training_phase(suggested_phase)
                metadata['training_phase_updated'] = True
            else:
                metadata['training_phase_updated'] = False
        
        return analysis, metadata

    def _infer_training_phase(self, comprehensive_context: Dict) -> Optional[str]:
        """Infer training phase from recent workout type distribution."""
        try:
            dist = (comprehensive_context or {}).get('workout_type_distribution', {}).get('distribution_pct', {})
            if not dist:
                return None

            def pct(name: str) -> float:
                try:
                    return float(dist.get(name, 0) or 0)
                except Exception:
                    return 0.0

            recovery = pct('Recovery')
            endurance = pct('Endurance')
            tempo = pct('Tempo')
            threshold = pct('Threshold')
            vo2 = pct('VO2max')
            high_intensity = threshold + vo2

            if recovery >= 40:
                return 'Recovery'
            if endurance >= 45 and high_intensity <= 25:
                return 'Base Building'
            if high_intensity >= 40 and endurance < 30:
                return 'Peak'
            if high_intensity >= 25:
                return 'Build'
            if tempo >= 30 and high_intensity < 25:
                return 'Maintenance'
            return 'Maintenance'
        except Exception:
            return None
    
    def extract_coaching_continuity(self, analysis: str, weekly_summary: Dict) -> Optional[Dict]:
        """
        Extract coaching continuity from AI's analysis for week-to-week memory.
        
        This parses the AI's analysis text to extract structured insights that
        should be remembered for next week's coaching session.
        
        Args:
            analysis: The AI-generated analysis text
            weekly_summary: The week's training data
        
        Returns:
            Dict with continuity fields, or None if extraction fails
        """
        try:
            # Create extraction prompt (truncate analysis if too long to avoid safety blocks)
            analysis_excerpt = analysis[:2000] if len(analysis) > 2000 else analysis
            
            extraction_prompt = f"""Extract key coaching insights from this analysis as JSON.

{analysis_excerpt}

Return ONLY this JSON structure:
{{
  "key_observations": ["2-3 key observations"],
  "progression_notes": ["improvements noted"],
  "areas_to_monitor": ["things to watch"],
  "next_week_priorities": ["top priorities"]
}}"""

            # Call API with low temperature for focused extraction
            print("  📝 Extracting coaching continuity...")
            response, _ = self._call_api(extraction_prompt, temperature=0.3, max_tokens=1000)
            
            # Parse JSON response using robust extraction method
            continuity_data = self._extract_json(response)
            
            # Validate required fields
            required_fields = ['key_observations', 'progression_notes', 'areas_to_monitor', 'next_week_priorities']
            for field in required_fields:
                if field not in continuity_data or not isinstance(continuity_data[field], list):
                    print(f"  ⚠️  Missing or invalid field: {field}, using empty list")
                    continuity_data[field] = []
            
            # Add week metadata
            continuity_data['week_start_date'] = weekly_summary.get('start_date', '')
            continuity_data['week_end_date'] = weekly_summary.get('end_date', '')
            continuity_data['week_number'] = weekly_summary.get('week_number', 0)
            
            print(f"  ✅ Extracted {len(continuity_data.get('key_observations', []))} observations")
            
            return continuity_data
            
        except Exception as e:
            print(f"  ⚠️  Failed to extract continuity: {e}")
            return None
    
    def generate_workout_plan(self, weekly_summary: Dict,
                             analysis: Optional[str] = None,
                             constraints: Optional[Dict] = None,
                             user_context: Optional[Dict] = None) -> Tuple[Dict, Dict]:
        """
        Generate next week's workout plan.
        
        Educational note: Generation Step
        
        Purpose: Create actionable plan
        - Based on analysis insights
        - Constrained by athlete preferences
        - Formatted as valid JSON
        
        Output: Structured JSON workout plan
        Ready for Zwift file generation
        
        Args:
            weekly_summary: Summary of completed week
            analysis: Analysis output from analyze_week()
            constraints: Athlete constraints (time, preferences, etc.)
            user_context: Dict with optional keys:
                - schedule_constraints: str
                - training_focus: str
                - week_feedback: str
        
        Returns:
            (workout_plan_json, metadata)
        """
        print("🏋️ Generating workout plan...")
        
        # Get comprehensive context
        comprehensive_context = self.db_queries.get_comprehensive_context(weeks_back=4)
        
        # Auto-update training phase based on recent distribution
        # This ensures phase is current even if analyze_week wasn't called
        suggested_phase = self._infer_training_phase(comprehensive_context)
        if suggested_phase:
            if suggested_phase != self.coaching_notes.current_training_phase:
                print(f"  📊 Updating training phase: {self.coaching_notes.current_training_phase} → {suggested_phase}")
                self.coaching_notes.update_training_phase(suggested_phase)
            else:
                print(f"  ✓ Training phase confirmed: {suggested_phase}")
        
        # Calculate next week's number and start date
        from datetime import datetime, timedelta
        import sqlite3
        
        today = datetime.now().date()
        # Find next Monday (or today if already Monday)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0 and today.weekday() != 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        next_week_start = next_monday.strftime('%Y-%m-%d')
        
        # Get the next sequential week number from the database
        # This is the athlete's training program week, not ISO calendar week
        from pathlib import Path
        db_path = Path(__file__).parent.parent.parent / 'data' / 'fitness_data.db'
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Find the highest week number in the database
        result = cursor.execute('SELECT MAX(weekNumber) FROM weekly_plans').fetchone()
        max_week = result[0] if result[0] is not None else 0
        next_week_number = max_week + 1
        
        conn.close()
        
        print(f"  Planning for Week {next_week_number} (starting {next_week_start})")
        
        # Load athlete data
        athlete_profile = self.coaching_notes.athlete_profile.__dict__
        coaching_notes = {
            'personality': self.coaching_notes.personality.__dict__,
            'current_training_phase': self.coaching_notes.current_training_phase,
            'next_week_focus': self.coaching_notes.next_week_focus,
            'observations': [obs.__dict__ for obs in self.coaching_notes.observations]
        }
        
        # Add next week info to user context
        if user_context is None:
            user_context = {}
        user_context['next_week_number'] = next_week_number
        user_context['next_week_start_date'] = next_week_start
        
        # Build context (including user_context)
        context = PromptContext(
            athlete_profile=athlete_profile,
            coaching_notes=coaching_notes,
            weekly_summary=weekly_summary,
            comprehensive_context=comprehensive_context,
            constraints=constraints,
            focus_topics={'intervals', 'periodization', 'json', 'format', 'threshold', 'vo2max'},
            user_context=user_context or {}
        )
        
        # Build prompt
        prompt = self.prompts.build_workout_generation_prompt(context, analysis)
        
        print(f"  Prompt: ~{self.prompts.estimate_prompt_tokens(prompt):,} tokens")
        
        # Call API with low temperature (precise JSON)
        # Need 8K-10K tokens for full 7-day plan with detailed intervals
        response, metadata = self._call_api(prompt, temperature=0.3, max_tokens=10000)
        
        print(f"  Response: ~{metadata.get('completion_tokens', 0):,} tokens")
        print(f"  Cost: ${metadata.get('cost', 0):.4f}")
        
        # Save raw response for debugging
        debug_dir = Path("data/ai_coach_output/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f"raw_generation_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt").write_text(response)

        # Parse JSON (with continuation fallback for truncation)
        workout_plan = None
        full_response = response

        if self._should_continue_json(full_response, metadata):
            for attempt in range(2):
                continuation = self._continue_json_response(full_response, attempt + 1)
                if not continuation:
                    break
                full_response += continuation
                try:
                    workout_plan = self._extract_json(full_response)
                    break
                except ValueError:
                    continue

            if workout_plan is not None and full_response != response:
                (debug_dir / f"raw_generation_response_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt").write_text(full_response)

        if workout_plan is None:
            workout_plan = self._extract_json(full_response)
        
        return workout_plan, metadata
    
    def _extract_json(self, text: str) -> Dict:
        """
        Extract JSON from API response.
        
        Educational note: JSON Extraction
        
        Problem: LLMs sometimes wrap JSON in markdown:
        ```json
        {...}
        ```
        
        Or add explanatory text before/after.
        
        Solution: Pattern matching to find JSON object
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        # Find JSON object (starts with {, ends with })
        start = text.find('{')
        end = text.rfind('}')
        
        if start >= 0 and end > start:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}")
                print(f"   Error context: ...{e.doc[max(0, e.pos-50):e.pos+50]}...")
                print(f"   Attempting to fix...")
                
                # Try to fix common issues
                json_str_fixed = json_str.replace("'", '"')  # Single quotes
                json_str_fixed = re.sub(r',(\s*[}\]])', r'\1', json_str_fixed)  # Trailing commas
                json_str_fixed = self._repair_truncated_json(json_str_fixed)
                
                try:
                    return json.loads(json_str_fixed)
                except json.JSONDecodeError as e2:
                    # Save the bad JSON for debugging
                    debug_dir = Path("data/ai_coach_output/debug")
                    debug_file = debug_dir / f"bad_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    debug_file.write_text(json_str)
                    print(f"   ❌ Could not fix JSON. Saved to: {debug_file}")
                    print(f"   Second error at line {e2.lineno}: {e2.msg}")
                    raise ValueError(f"Invalid JSON in AI response. Error: {e2.msg} at line {e2.lineno}. Check {debug_file}")
        
        raise ValueError("No valid JSON found in response")

    def _repair_truncated_json(self, json_str: str) -> str:
        """
        Attempt to repair truncated JSON by:
        1) Trimming trailing non-JSON characters
        2) Balancing any unclosed braces/brackets (ignoring strings)
        """
        if not json_str:
            return json_str

        # Trim trailing garbage after the last closing brace/bracket
        last_close = max(json_str.rfind('}'), json_str.rfind(']'))
        if last_close != -1:
            json_str = json_str[:last_close + 1]

        stack = []
        in_string = False
        escape = False

        for ch in json_str:
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch in '{[':
                stack.append(ch)
            elif ch in '}]':
                if stack:
                    stack.pop()

        # Append closing tokens in reverse order
        if stack:
            closing = ''.join('}' if opener == '{' else ']' for opener in reversed(stack))
            json_str = json_str + closing

        return json_str

    def _is_truncated_json(self, text: str) -> bool:
        """Detect likely truncation by checking for unbalanced braces/brackets."""
        if not text or '{' not in text:
            return False

        stack = []
        in_string = False
        escape = False

        for ch in text:
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch in '{[':
                stack.append(ch)
            elif ch in '}]':
                if stack:
                    stack.pop()

        return len(stack) > 0

    def _should_continue_json(self, response_text: str, metadata: Dict) -> bool:
        finish = str(metadata.get('finish_reason', '')).lower()
        if 'max' in finish or 'length' in finish:
            return True
        return self._is_truncated_json(response_text)

    def _continue_json_response(self, partial_response: str, attempt: int) -> str:
        """Request continuation when JSON output was truncated."""
        tail = partial_response[-2000:]
        continuation_prompt = (
            "You are continuing a JSON document that was cut off. "
            "Continue EXACTLY where it left off with valid JSON only. "
            "Do NOT repeat any existing text. Do NOT add any new opening text or markdown. "
            "Return only the continuation bytes needed to finish the JSON.\n\n"
            f"Partial JSON tail (for context):\n{tail}\n\n"
            "Continue JSON now:"
        )

        response, _ = self._call_api(continuation_prompt, temperature=0.2, max_tokens=4000)
        return response
    
    def validate_workout_plan(self, plan: Dict) -> Tuple[bool, List[str]]:
        """
        Validate workout plan against requirements.
        
        Educational note: Validation Strategies
        
        Multi-layer validation:
        1. Schema (has required fields?)
        2. Type checking (values correct type?)
        3. Business logic (TSS reasonable? FTP set?)
        4. Consistency (dates sequential? days=7?)
        
        Returns both bool and list of errors for debugging
        """
        errors = []
        
        # Check required top-level fields
        required_fields = ['weekNumber', 'startDate', 'ftp', 'plannedTSS', 'notes', 'days']
        for field in required_fields:
            if field not in plan:
                errors.append(f"Missing required field: {field}")
        
        # Check FTP is reasonable
        if plan.get('ftp'):
            ftp = plan['ftp']
            if not (150 <= ftp <= 500):
                errors.append(f"FTP {ftp}W outside reasonable range (150-500)")
        
        # Check we have 7 days
        days = plan.get('days', [])
        if len(days) != 7:
            errors.append(f"Expected 7 days, got {len(days)}")
        
        # Check day numbering
        for i, day in enumerate(days, 1):
            if day.get('dayNumber') != i:
                errors.append(f"Day {i} has incorrect dayNumber: {day.get('dayNumber')}")
        
        # Check TSS range is reasonable
        if plan.get('plannedTSS'):
            tss = plan['plannedTSS']
            if tss.get('min') and tss.get('max'):
                if not (200 <= tss['min'] <= 800 and 200 <= tss['max'] <= 800):
                    errors.append(f"TSS range {tss['min']}-{tss['max']} outside reasonable bounds")
        
        return len(errors) == 0, errors
    
    def coach_session(self, weekly_summary: Dict,
                     constraints: Optional[Dict] = None,
                     save_results: bool = True) -> CoachingResult:
        """
        Full coaching session: Analyze → Generate → Validate.
        
        Educational note: Orchestration Pattern
        
        This is the main entry point that coordinates everything:
        
        1. Analyze (understand)
        2. Generate (create)
        3. Validate (verify)
        4. Save (persist)
        
        Each step builds on previous, but isolated for testing/debugging.
        
        Args:
            weekly_summary: Summary of completed week
            constraints: Athlete constraints for next week
            save_results: Whether to save to files
        
        Returns:
            CoachingResult with analysis, plan, and metadata
        """
        print("\n🤖 Starting AI Coaching Session")
        print("=" * 80)
        
        result = CoachingResult(success=False)
        
        try:
            # Step 1: Analyze
            analysis, analysis_meta = self.analyze_week(weekly_summary)
            result.analysis = analysis
            
            print("\n✅ Analysis complete")
            print("-" * 80)
            print(analysis[:300] + "..." if len(analysis) > 300 else analysis)
            
            # Step 1.5: Extract coaching continuity from analysis
            continuity_data = self.extract_coaching_continuity(analysis, weekly_summary)
            if continuity_data:
                # Save to coaching notes for next week's context
                self.coaching_notes.add_coaching_continuity(
                    week_start_date=continuity_data.get('week_start_date', ''),
                    week_end_date=continuity_data.get('week_end_date', ''),
                    week_number=continuity_data.get('week_number', 0),
                    key_observations=continuity_data.get('key_observations', []),
                    progression_notes=continuity_data.get('progression_notes', []),
                    areas_to_monitor=continuity_data.get('areas_to_monitor', []),
                    next_week_priorities=continuity_data.get('next_week_priorities', []),
                    recurring_schedule=continuity_data.get('recurring_schedule')
                )
                print("  ✅ Coaching continuity saved for next week")
            
            # Step 2: Generate
            workout_plan, plan_meta = self.generate_workout_plan(
                weekly_summary,
                analysis,
                constraints
            )
            result.workout_plan = workout_plan
            
            print("\n✅ Workout plan generated")
            
            # Step 3: Validate
            is_valid, errors = self.validate_workout_plan(workout_plan)
            
            if not is_valid:
                print("\n⚠️  Validation errors:")
                for error in errors:
                    print(f"   - {error}")
                result.errors = errors
            else:
                print("\n✅ Validation passed")
                result.success = True
            
            # Metadata
            result.metadata = {
                'model': self.model.value,
                'total_cost': self.session_cost,
                'analysis_meta': analysis_meta,
                'plan_meta': plan_meta,
                'timestamp': datetime.now().isoformat()
            }
            
            # Step 4: Save (if requested and valid)
            if save_results and is_valid:
                self._save_results(result)
            
            print("\n" + "=" * 80)
            print(f"💰 Total session cost: ${self.session_cost:.4f}")
            
            return result
        
        except Exception as e:
            print(f"\n❌ Coaching session failed: {e}")
            result.errors = [str(e)]
            import traceback
            traceback.print_exc()
            return result
    
    def save_plan_to_database(self, workout_plan: Dict, start_date: str, 
                              output_dir: Optional[str] = None) -> Tuple[bool, str, List[str]]:
        """
        Save AI-generated workout plan to database and generate Zwift files.
        
        This integrates the AI coach with existing proposed workouts workflow:
        1. Convert AI plan JSON to database schema
        2. Save weekly plan + daily plans + workouts
        3. Generate Zwift .zwo files for cycling workouts
        
        Args:
            workout_plan: AI-generated plan (from generate_workout_plan)
            start_date: Week start date (YYYY-MM-DD)
            output_dir: Optional Zwift workouts directory path
        
        Returns:
            Tuple of (success: bool, message: str, zwift_files: List[str])
        """
        try:
            from storage.database import WorkoutDatabase
            from utils.zwift_workout_generator import generate_zwift_workouts_from_db
            from datetime import datetime, timedelta
            
            db = WorkoutDatabase()
            
            # Parse start date
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = start_dt + timedelta(days=6)
            end_date = end_dt.strftime('%Y-%m-%d')
            
            # Determine correct sequential week number.
            # The AI's weekNumber reflects its internal training-cycle numbering
            # (e.g., "week 11 of a 12-week block") which is NOT our sequential
            # folder counter (Week_57, Week_68, Week_69 …).  Always derive the
            # correct number from the database:
            #   1. If a weekly plan already exists for this exact startDate, reuse it.
            #   2. Otherwise use MAX(weekNumber)+1 when our counter has reached ≥50.
            #   3. Fall back to ISO week only if the DB is truly empty.
            import sqlite3 as _sqlite3
            week_number = None
            try:
                with _sqlite3.connect(db.db_path) as _wn_conn:
                    # Check for an existing plan on the same start date
                    existing_row = _wn_conn.execute(
                        "SELECT weekNumber FROM weekly_plans WHERE startDate = ?",
                        (start_date,)
                    ).fetchone()
                    if existing_row:
                        week_number = existing_row[0]
                    else:
                        max_row = _wn_conn.execute(
                            "SELECT MAX(weekNumber) FROM weekly_plans"
                        ).fetchone()
                        max_week = max_row[0] if max_row and max_row[0] else 0
                        if max_week >= 50:
                            # Sequential counter in use — next slot
                            week_number = max_week + 1
            except Exception as _wn_err:
                print(f"⚠️  Could not query DB for week number: {_wn_err}")
            if week_number is None:
                ai_week_number = workout_plan.get('weekNumber')
                if ai_week_number and ai_week_number > 1:
                    week_number = ai_week_number
                else:
                    week_number = start_dt.isocalendar()[1]
            ftp = workout_plan.get('ftp', 300)
            planned_tss = workout_plan.get('plannedTSS', {})
            notes = workout_plan.get('notes', '')
            
            # Convert notes to string if it's a dict
            if isinstance(notes, dict):
                notes = json.dumps(notes, indent=2)
            
            # Parse TSS range (can be dict with min/max, string "min-max", or single number)
            if isinstance(planned_tss, dict):
                tss_min = planned_tss.get('min', 0)
                tss_max = planned_tss.get('max', 0)
            elif isinstance(planned_tss, str) and '-' in planned_tss:
                tss_parts = planned_tss.split('-')
                tss_min = int(tss_parts[0])
                tss_max = int(tss_parts[1])
            else:
                tss_min = int(planned_tss) if planned_tss else 0
                tss_max = tss_min
            
            # Check if weekly plan already exists
            existing_plan = db.get_weekly_plan(week_number)
            if existing_plan:
                print(f"⚠️  Weekly plan exists for week {week_number}, deleting...")
                db.delete_weekly_plan_cascade(week_number)
            
            # Create weekly plan
            print(f"💾 Creating weekly plan for week {week_number}...")
            db.create_weekly_plan(
                weekNumber=week_number,
                startDate=start_date,
                plannedTSS_min=tss_min,
                plannedTSS_max=tss_max,
                notes=notes,
                ftp=ftp
            )
            
            # Create daily plans and workouts
            days = workout_plan.get('days', [])
            if not days:
                return False, "No workouts in plan", []
            
            print(f"💾 Saving {len(days)} daily workouts...")
            daily_plan_ids = []
            
            for day in days:
                day_num = day.get('dayNumber', 0)
                # Calculate workout date
                workout_date = (start_dt + timedelta(days=day_num - 1)).strftime('%Y-%m-%d')
                
                # Create daily plan
                success = db.create_daily_plan(
                    weekNumber=week_number,
                    dayNumber=day_num,
                    date=workout_date
                )
                
                if not success:
                    return False, f"Failed to create daily plan for day {day_num}", []
                
                # Get daily plan ID
                daily_plan_id = db.get_daily_plan_id(
                    weekNumber=week_number,
                    dayNumber=day_num,
                    date=workout_date
                )
                
                if not daily_plan_id:
                    return False, f"Failed to get daily plan ID for day {day_num}", []
                
                daily_plan_ids.append(daily_plan_id)
                
                # Process workouts for this day
                workouts = day.get('workouts', [])
                
                if not workouts:
                    # Rest day - create a minimal rest entry
                    success = db.create_proposed_workout(
                        dailyPlanId=daily_plan_id,
                        type='rest',
                        name='Rest Day',
                        plannedDuration=0,
                        plannedTSS_min=0,
                        plannedTSS_max=0,
                        targetRPE_min=1,
                        targetRPE_max=1,
                        intervals="[]",
                        sections="[]",
                        notes="Rest and recovery"
                    )
                    if not success:
                        return False, f"Failed to create rest workout for day {day_num}", []
                    continue
                
                # Create each workout for this day
                for workout in workouts:
                    workout_type = workout.get('type', 'bike').lower()
                    workout_name = workout.get('name', f'Day {day_num}')
                    
                    # Extract duration (single value)
                    duration = workout.get('plannedDuration', 60)
                    
                    # Extract TSS (can be dict with min/max or single value)
                    planned_tss = workout.get('plannedTSS', {})
                    if isinstance(planned_tss, dict):
                        tss_min = planned_tss.get('min', 0)
                        tss_max = planned_tss.get('max', 0)
                    else:
                        tss_min = tss_max = int(planned_tss) if planned_tss else 0
                    
                    # Extract RPE (can be dict with min/max or single value)
                    target_rpe = workout.get('targetRPE', {})
                    if isinstance(target_rpe, dict):
                        rpe_min = target_rpe.get('min', 5)
                        rpe_max = target_rpe.get('max', 5)
                    else:
                        rpe_min = rpe_max = int(target_rpe) if target_rpe else 5
                    
                    # Extract notes (can be array or string)
                    notes = workout.get('notes', [])
                    if isinstance(notes, list):
                        workout_notes = '\n'.join(notes)
                    else:
                        workout_notes = str(notes)
                    
                    # Extract intervals and sections
                    intervals = workout.get('intervals', [])
                    sections = workout.get('sections', [])

                    # Synthesize intervals from structureGuidelines for unstructured
                    # bike workouts (e.g., long endurance rides with outdoor guidance
                    # blocks instead of explicit interval lists).
                    if not intervals and workout_type == 'bike':
                        struct = workout.get('structureGuidelines', {})
                        power_guide = workout.get('powerGuidelines', {})
                        if struct:
                            import re as _re
                            def _extract_watts(text):
                                m = _re.search(r'(\d+)-(\d+)W', str(text))
                                return (int(m.group(1)), int(m.group(2))) if m else (None, None)
                            def _extract_minutes(text):
                                m = _re.search(r'(\d+)\s*minute', str(text))
                                return int(m.group(1)) if m else 0
                            warmup_text   = struct.get('warmup', '')
                            main_text     = struct.get('mainBlock', '')
                            cooldown_text = struct.get('cooldown', '')
                            wu_mins  = _extract_minutes(warmup_text)
                            mn_mins  = _extract_minutes(main_text)
                            cd_mins  = _extract_minutes(cooldown_text)
                            total_mins = duration
                            if not (wu_mins + mn_mins + cd_mins):
                                wu_mins = max(10, int(total_mins * 0.15))
                                cd_mins = max(10, int(total_mins * 0.15))
                                mn_mins = total_mins - wu_mins - cd_mins
                            base_min, base_max = _extract_watts(
                                power_guide.get('baseEffort', '')
                            )
                            if base_min is None:
                                base_min, base_max = _extract_watts(main_text)
                            if base_min is None:
                                base_min, base_max = 195, 215
                            wu_min,  wu_max  = _extract_watts(warmup_text)
                            cd_min,  cd_max  = _extract_watts(cooldown_text)
                            if wu_min is None:  wu_min,  wu_max  = 140, 160
                            if cd_min is None:  cd_min,  cd_max  = 140, 160
                            synth = []
                            if wu_mins > 0:
                                synth.append({
                                    'name': 'Warmup',
                                    'duration': wu_mins * 60,
                                    'powerTarget': {'type': 'range', 'min': wu_min,   'max': wu_max,   'unit': 'watts'},
                                    'cadenceTarget': {'min': 85, 'max': 95}
                                })
                            if mn_mins > 0:
                                main_name = 'Steady Effort'
                                if ':' in main_text:
                                    main_name = main_text.split(':')[0].strip()
                                synth.append({
                                    'name': main_name,
                                    'duration': mn_mins * 60,
                                    'powerTarget': {'type': 'range', 'min': base_min, 'max': base_max, 'unit': 'watts'},
                                    'cadenceTarget': {'min': 88, 'max': 95}
                                })
                            if cd_mins > 0:
                                synth.append({
                                    'name': 'Cool Down',
                                    'duration': cd_mins * 60,
                                    'powerTarget': {'type': 'range', 'min': cd_min,   'max': cd_max,   'unit': 'watts'},
                                    'cadenceTarget': {'min': 90, 'max': 100}
                                })
                            if synth:
                                intervals = synth
                                print(f"  ✅ Synthesized {len(synth)}-interval structure for '{workout_name}' from structureGuidelines")

                    # Create workout
                    success = db.create_proposed_workout(
                        dailyPlanId=daily_plan_id,
                        type=workout_type,
                        name=workout_name,
                        plannedDuration=duration,
                        plannedTSS_min=tss_min,
                        plannedTSS_max=tss_max,
                        targetRPE_min=rpe_min,
                        targetRPE_max=rpe_max,
                        intervals=json.dumps(intervals) if intervals else "[]",
                        sections=json.dumps(sections) if sections else "[]",
                        notes=workout_notes
                    )
                    
                    if not success:
                        return False, f"Failed to create workout '{workout_name}' for day {day_num}", []
            
            print("✅ Workout plan saved to database!")
            
            # Generate Zwift files for cycling workouts
            zwift_files = []
            try:
                if not output_dir:
                    import os
                    output_dir = os.getenv('ZWIFT_WORKOUTS_DIR', "~/Documents/Zwift/Workouts/6870291")
                
                print(f"🚴 Generating Zwift workout files...")
                zwift_files = generate_zwift_workouts_from_db(
                    db_connection=db,
                    start_date=start_date,
                    end_date=end_date,
                    ftp=ftp,
                    output_dir=output_dir,
                    week_number=week_number
                )
                
                if zwift_files:
                    print(f"✅ Generated {len(zwift_files)} Zwift workout files!")
                else:
                    print("ℹ️  No cycling workouts to generate Zwift files for")
                    
            except Exception as e:
                print(f"⚠️  Zwift file generation failed: {e}")
                # Don't fail the whole operation if just Zwift files fail
                zwift_files = []
            
            message = f"Successfully saved workout plan for week {week_number}"
            if zwift_files:
                message += f" and generated {len(zwift_files)} Zwift files"
            
            return True, message, zwift_files
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error saving plan: {str(e)}", []
    
    def _save_results(self, result: CoachingResult):
        """Save coaching results to files."""
        output_dir = Path("data/ai_coach_output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save analysis
        if result.analysis:
            analysis_file = output_dir / f"analysis_{timestamp}.txt"
            analysis_file.write_text(result.analysis)
            print(f"\n💾 Saved analysis: {analysis_file}")
        
        # Save workout plan
        if result.workout_plan:
            plan_file = output_dir / f"workout_plan_{timestamp}.json"
            plan_file.write_text(json.dumps(result.workout_plan, indent=2))
            print(f"💾 Saved workout plan: {plan_file}")
        
        # Save full result
        result_file = output_dir / f"coaching_result_{timestamp}.json"
        result_file.write_text(json.dumps(result.to_dict(), indent=2, default=str))
        print(f"💾 Saved full result: {result_file}")


# Test with real data
if __name__ == "__main__":
    print("🤖 AI Coach Engine - Test with Real Data\n")
    print("=" * 80)
    
    try:
        # Initialize coach with Gemini 2.5 Flash (FREE - 15 requests/min)
        print("\n1️⃣ Initializing AI Coach (Gemini 2.5 Flash - FREE)")
        coach = AICoachEngine(model=AIModel.GEMINI_FREE)
        
        # Get REAL weekly summary from database
        print("\n2️⃣ Loading REAL training data from database...")
        
        import sys
        import os
        
        # Add parent directory to path to import database module
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from storage.database import WorkoutDatabase
        
        # Use last complete week (Oct 27 - Nov 2)
        start_date = '2025-10-27'
        end_date = '2025-11-02'
        
        db = WorkoutDatabase()
        sample_summary = db.generate_weekly_summary(start_date, end_date)
        
        if not sample_summary:
            print("   ❌ Failed to load weekly summary from database")
            sys.exit(1)
        
        print(f"   Week: {sample_summary['start_date']} to {sample_summary['end_date']}")
        print(f"   TSS: {sample_summary['total_tss']}")
        print(f"   Hours: {sample_summary['total_training_hours']}")
        print(f"   Sessions: {sample_summary['sessions_completed']}")
        print(f"   Workout Types: {sample_summary['workout_types']}")
        print(f"   Workouts with data: {len(sample_summary.get('qualitative_feedback', []))}")
        print(f"   Avg Sleep Quality: {sample_summary.get('avg_sleep_quality')}")
        print(f"   Avg Energy: {sample_summary.get('avg_daily_energy')}")
        
        # Run coaching session
        print("\n3️⃣ Running full coaching session...")
        print("   This will:")
        print("   - Analyze your recent training")
        print("   - Generate next week's plan")
        print("   - Validate the output")
        print()
        
        result = coach.coach_session(sample_summary, save_results=True)
        
        if result.success:
            print("\n" + "=" * 80)
            print("✅ COACHING SESSION SUCCESSFUL!")
            print("=" * 80)
            print(f"\nTotal cost: ${result.metadata['total_cost']:.4f}")
            print(f"Model used: {result.metadata['model']}")
            
            if result.workout_plan:
                print(f"\n📋 Generated plan overview:")
                print(f"   Week: {result.workout_plan.get('weekNumber')}")
                print(f"   FTP: {result.workout_plan.get('ftp')}W")
                print(f"   TSS: {result.workout_plan.get('plannedTSS')}")
                print(f"   Days: {len(result.workout_plan.get('days', []))}")
        else:
            print("\n⚠️  Session completed with errors:")
            for error in result.errors or []:
                print(f"   - {error}")
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
