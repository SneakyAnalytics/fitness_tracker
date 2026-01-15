# AI Coaching System

**Complete guide to how AI generates personalized training plans.**

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
- [Orchestration Engine](#orchestration-engine)
- [Prompt Engineering](#prompt-engineering)
- [Model Selection](#model-selection)
- [Usage Examples](#usage-examples)
- [Advanced Patterns](#advanced-patterns)

---

## Overview

The AI Coaching System transforms workout history and athlete data into personalized training plans using Large Language Models (LLMs).

### What it Does

1. **Analyzes** recent training (TSS, intervals, fatigue)
2. **Synthesizes** cycling science knowledge
3. **Generates** structured workout plans (JSON)
4. **Validates** plans meet constraints (TSS targets, recovery)
5. **Creates** Zwift-compatible workout files

### Why AI?

**Traditional approach:** Generic plans, manual adjustments  
**AI approach:** Personalized plans that adapt to:

- Your recent performance
- Your personal bests
- Your schedule constraints
- Your subjective feedback
- Cycling science best practices

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Coach Request                          │
│  "Generate next week's training (Jan 15-21)"                 │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         v
┌──────────────────────────────────────────────────────────────┐
│              1. Data Collection Phase                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐     │
│  │  Database   │  │ Coaching     │  │  Athlete       │     │
│  │  Queries    │  │ Notes        │  │  Profile       │     │
│  └──────┬──────┘  └──────┬───────┘  └────────┬───────┘     │
│         │                 │                    │              │
│         └─────────────────┴────────────────────┘              │
│                           │                                   │
│                  ┌────────v────────┐                         │
│                  │  Athlete Context │                         │
│                  └────────┬────────┘                         │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             v
┌──────────────────────────────────────────────────────────────┐
│              2. Knowledge Retrieval (RAG)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Cycling Science Docs (1500+ lines)                  │   │
│  │  • Training zones • Periodization • Recovery         │   │
│  │  • Interval design • Testing protocols              │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                   │
│                  ┌────────v────────┐                         │
│                  │ Smart Retrieval  │                         │
│                  │ (topic-based)    │                         │
│                  └────────┬────────┘                         │
│                           │                                   │
│                  ┌────────v────────┐                         │
│                  │  Relevant Chunks │                         │
│                  │  (~5K tokens)    │                         │
│                  └────────┬────────┘                         │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             v
┌──────────────────────────────────────────────────────────────┐
│              3. AI Generation Phase                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Prompt Assembly                                    │     │
│  │  • System instructions (role, constraints)         │     │
│  │  • Athlete context (history, profile)              │     │
│  │  • Knowledge chunks (cycling science)              │     │
│  │  • Task specification (generate weekly plan)       │     │
│  │  • Output format (JSON schema)                     │     │
│  └────────────────────────┬───────────────────────────┘     │
│                           │                                   │
│                  ┌────────v────────┐                         │
│                  │  LLM Call        │                         │
│                  │  (Gemini/Claude) │                         │
│                  └────────┬────────┘                         │
│                           │                                   │
│                  ┌────────v────────┐                         │
│                  │  Raw Response    │                         │
│                  │  (JSON string)   │                         │
│                  └────────┬────────┘                         │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             v
┌──────────────────────────────────────────────────────────────┐
│              4. Validation Phase                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Parse & Validate                                    │    │
│  │  • Valid JSON?                                       │    │
│  │  • All required fields?                              │    │
│  │  • TSS within targets?                               │    │
│  │  • Workout types appropriate?                        │    │
│  │  • Recovery days included?                           │    │
│  └────────────────────────┬────────────────────────────┘    │
│                           │                                   │
│                   ┌───────┴────────┐                         │
│                   │                 │                         │
│              Valid?           Invalid?                        │
│                   │                 │                         │
│                   v                 v                         │
│           ┌───────────┐    ┌────────────┐                   │
│           │  Accept   │    │   Retry    │                   │
│           │  Plan     │    │ with fixes │────┐               │
│           └─────┬─────┘    └────────────┘    │               │
│                 │                             │               │
└─────────────────┼─────────────────────────────┘               │
                  │              ^──────────────┘               │
                  v                                             │
┌──────────────────────────────────────────────────────────────┘
│              5. Output Generation
│  ┌────────────────────────────────────────────────────┐
│  │  For each workout in plan:                         │
│  │  • Create Zwift .zwo file                          │
│  │  • Generate workout summary                        │
│  │  • Store in database                               │
│  └────────────────────────┬───────────────────────────┘
│                           │
│                  ┌────────v────────┐
│                  │  Complete Plan   │
│                  │  • JSON          │
│                  │  • .zwo files    │
│                  │  • Database IDs  │
│                  └──────────────────┘
└──────────────────────────────────────────────────────────────
```

---

## RAG (Retrieval-Augmented Generation)

**File:** [`src/utils/rag_context_loader.py`](../../src/utils/rag_context_loader.py)

### The Problem

You have 7 markdown files with ~1500 lines of cycling science:

- Training zones
- Periodization principles
- Interval design patterns
- Recovery protocols
- Testing methodologies
- Best practices

**Challenge:** Can't fit all knowledge in every AI prompt (token limits).

### The Solution

**RAG = Retrieval-Augmented Generation**

1. **Chunk** documents into logical pieces
2. **Index** with topic tags
3. **Retrieve** only relevant chunks for each query
4. **Augment** prompt with retrieved knowledge
5. **Generate** informed response

### How It Works

```python
from src.utils.rag_context_loader import RAGContextLoader

loader = RAGContextLoader()

# Load all cycling science docs
loader.load_markdown_files('data/rag_context/')

# Retrieve relevant chunks for a query
context = loader.get_context_for_query(
    topics={'vo2max', 'intervals', 'high-intensity'},
    max_tokens=5000
)

# Use in AI prompt
prompt = f"""
Cycling Science:
{context}

Generate a VO2max workout...
"""
```

### Chunking Strategy

**Hierarchical chunking by headers:**

```markdown
# Training Zones (Priority: HIGH)

## Zone 1: Recovery (Priority: MEDIUM)

Content about recovery training...

## Zone 2: Endurance (Priority: HIGH)

Content about endurance training...

# Interval Design (Priority: HIGH)

## VO2max Intervals (Priority: MEDIUM)

Content about VO2max workouts...
```

Each section becomes a chunk:

```python
KnowledgeChunk(
    source_file='training-zones.md',
    title='Zone 2: Endurance',
    content='Content about endurance training...',
    topics={'zone2', 'endurance', 'base-building'},
    priority=ChunkPriority.HIGH,
    token_estimate=350
)
```

### Smart Retrieval

**Query topics:** `{'vo2max', 'intervals'}`

**Retrieved chunks:**

1. "VO2max Intervals" (direct match, HIGH priority)
2. "Interval Design Principles" (related, HIGH priority)
3. "Zone 5 Training" (related, MEDIUM priority)
4. "Recovery Between Intervals" (related, MEDIUM priority)

**Total:** ~4,500 tokens (fits in context budget)

**Not retrieved:**

- "Nutrition for Long Rides" (irrelevant)
- "Time Trial Pacing" (irrelevant)
- "Bike Fit Guidelines" (irrelevant)

### Topic Taxonomy

Common topics used for retrieval:

- **Zones:** `zone1`, `zone2`, `zone3`, `zone4`, `zone5`, `zone6`
- **Workout Types:** `vo2max`, `threshold`, `tempo`, `endurance`, `recovery`, `sprint`
- **Concepts:** `intervals`, `periodization`, `tapering`, `overreaching`, `testing`
- **Goals:** `base-building`, `race-prep`, `maintenance`, `comeback`

### Priority Levels

```python
class ChunkPriority(Enum):
    ALWAYS = 1      # Always include (e.g., JSON schema)
    HIGH = 2        # Core principles, frequently needed
    MEDIUM = 3      # Specific techniques, include when relevant
    LOW = 4         # Edge cases, include only if specifically requested
```

### Token Budgeting

```python
# Set max tokens for context
context = loader.get_context_for_query(
    topics={'threshold', 'sweet-spot'},
    max_tokens=5000  # Leave room for athlete data + conversation
)

# Context includes:
# - ALWAYS chunks (e.g., JSON schema): ~1000 tokens
# - HIGH priority matches: ~2000 tokens
# - MEDIUM priority matches: ~2000 tokens
# Total: ~5000 tokens
```

### Custom Knowledge

Add your own cycling science:

```python
loader = RAGContextLoader()

# Add custom chunk
from dataclasses import dataclass
from src.utils.rag_context_loader import KnowledgeChunk, ChunkPriority

custom_chunk = KnowledgeChunk(
    source_file='my-notes.md',
    title='Cold Weather Training',
    content='In cold weather, expect 5-10w lower FTP...',
    topics={'weather', 'indoor', 'winter'},
    priority=ChunkPriority.MEDIUM,
    token_estimate=200
)

loader.chunks.append(custom_chunk)

# Now available for retrieval
context = loader.get_context_for_query(
    topics={'winter', 'indoor'}
)
```

---

## Orchestration Engine

**File:** [`src/utils/ai_coach_engine.py`](../../src/utils/ai_coach_engine.py)

### Orchestration Patterns

**Why orchestrate?** Complex tasks need multiple AI calls with validation between steps.

**Pattern:** Sequential pipeline with feedback loops

```
1. Analyze recent training
     ↓
2. Generate workout plan
     ↓
3. Validate plan ──→ Invalid? ──→ Regenerate with fixes
     ↓ Valid
4. Return result
```

### Workflow

```python
from src.utils.ai_coach_engine import AICoachEngine, AIModel

coach = AICoachEngine(model=AIModel.GEMINI_FREE)

# Generate weekly plan
result = coach.generate_weekly_plan(
    start_date='2026-01-20',
    athlete_id=1,
    constraints={
        'available_days': ['Monday', 'Tuesday', 'Thursday', 'Saturday'],
        'max_duration': 90,  # minutes per workout
        'weekly_tss_target': 500
    }
)
```

**Result:**

```python
CoachingResult(
    success=True,
    analysis="""
    Recent Training Analysis (Jan 1-14):
    - Total TSS: 485 (target: 500)
    - Hard workouts: 3 (threshold, VO2max, sweet spot)
    - Recovery quality: Good (RPE 2-3)
    - Progression: On track

    Recommendations:
    - Maintain intensity level
    - Add 1 longer endurance ride
    - Include recovery week in 2 weeks
    """,
    workout_plan={
        'week_number': 3,
        'start_date': '2026-01-20',
        'end_date': '2026-01-26',
        'weekly_tss_target': 500,
        'theme': 'Threshold Development',
        'workouts': [
            {
                'date': '2026-01-20',
                'title': 'Threshold Intervals',
                'type': 'bike',
                'duration': 75,
                'tss': 85,
                'description': '4x8min @ 98% FTP',
                'intervals': [...]
            },
            # ... more workouts
        ]
    },
    errors=None,
    metadata={
        'model': 'gemini-1.5-flash-002',
        'tokens_used': 12500,
        'api_calls': 2,
        'cost': 0.015,
        'generation_time': 8.3
    }
)
```

### Step-by-Step Breakdown

#### Step 1: Data Collection

```python
# Collect athlete context
context = {
    'athlete_profile': db.get_athlete_profile(athlete_id),
    'recent_workouts': db.get_recent_workouts(days=14),
    'coaching_notes': notes_manager.get_recent_notes(weeks=4),
    'personal_bests': db.get_personal_bests(),
    'weekly_tss': db.get_weekly_tss(weeks=8)
}
```

#### Step 2: RAG Retrieval

```python
# Determine relevant topics from context
topics = self._extract_topics_from_context(context)
# e.g., {'threshold', 'periodization', 'recovery'}

# Load relevant cycling science
knowledge = rag_loader.get_context_for_query(
    topics=topics,
    max_tokens=5000
)
```

#### Step 3: Analysis

```python
# Ask AI to analyze recent training
analysis_prompt = prompts.create_analysis_prompt(
    context=context,
    knowledge=knowledge
)

analysis = self._call_llm(analysis_prompt)
```

#### Step 4: Generation

```python
# Generate workout plan
generation_prompt = prompts.create_generation_prompt(
    context=context,
    analysis=analysis,
    knowledge=knowledge,
    constraints=constraints
)

plan_json = self._call_llm(generation_prompt)
```

#### Step 5: Validation

```python
# Parse and validate
try:
    plan = json.loads(plan_json)
    errors = self._validate_plan(plan, constraints)

    if errors:
        # Regenerate with corrections
        fix_prompt = prompts.create_fix_prompt(
            original_plan=plan,
            errors=errors
        )
        plan_json = self._call_llm(fix_prompt)
        plan = json.loads(plan_json)
except json.JSONDecodeError:
    # Ask AI to fix JSON
    fix_prompt = f"Fix this invalid JSON: {plan_json}"
    plan_json = self._call_llm(fix_prompt)
```

### Error Handling

**1. API Failures**

```python
def _call_llm(self, prompt: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return self.client.generate(prompt)
        except APIError as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

**2. JSON Parse Errors**

```python
try:
    plan = json.loads(response)
except json.JSONDecodeError:
    # Ask AI to fix
    fix_prompt = f"""
    The following JSON is invalid. Fix it and return valid JSON:

    {response}

    Return ONLY valid JSON, no explanation.
    """
    response = self._call_llm(fix_prompt)
    plan = json.loads(response)
```

**3. Validation Errors**

```python
errors = []
if plan['weekly_tss'] > constraints['max_tss'] * 1.1:
    errors.append(f"TSS too high: {plan['weekly_tss']}")

if len(plan['workouts']) != constraints['days_per_week']:
    errors.append(f"Wrong number of workouts")

if errors:
    # Regenerate with specific fixes
    return self._regenerate_with_fixes(plan, errors)
```

### Cost Tracking

```python
class AICoachEngine:
    def _call_llm(self, prompt: str):
        response = self.client.generate(prompt)

        # Track cost
        tokens = self._estimate_tokens(prompt, response)
        cost = self._calculate_cost(tokens, self.model)

        self.session_cost += cost
        self.api_calls.append({
            'timestamp': datetime.now(),
            'tokens': tokens,
            'cost': cost,
            'model': self.model.value
        })

        return response

    def _calculate_cost(self, tokens: int, model: AIModel):
        rates = {
            AIModel.GEMINI_FREE: 0.0,  # Free tier
            AIModel.GEMINI_PRO: 0.0005,  # $0.50 per 1M tokens
            AIModel.CLAUDE_SONNET: 0.003  # $3 per 1M tokens
        }
        return (tokens / 1_000_000) * rates[model]
```

---

## Prompt Engineering

**File:** [`src/utils/ai_prompts.py`](../../src/utils/ai_prompts.py)

### Prompt Structure

All prompts follow this structure:

```
1. System Context (Who is the AI?)
2. Knowledge Base (What does it know?)
3. Task Context (What's the situation?)
4. Specific Task (What should it do?)
5. Output Format (How should it respond?)
6. Constraints (What are the rules?)
```

### Example: Weekly Plan Generation

```python
class AICoachPrompts:
    def create_generation_prompt(
        self,
        context: Dict,
        analysis: str,
        knowledge: str,
        constraints: Dict
    ) -> str:
        return f"""
# ROLE
You are an expert cycling coach with 20+ years experience.
You create personalized training plans based on science and athlete data.

# KNOWLEDGE BASE
{knowledge}

# ATHLETE CONTEXT
Name: {context['athlete_profile']['name']}
FTP: {context['athlete_profile']['ftp']}w
Recent TSS (14 days): {sum(w['tss'] for w in context['recent_workouts'])}
Recent workouts:
{self._format_workouts(context['recent_workouts'])}

# RECENT TRAINING ANALYSIS
{analysis}

# TASK
Generate a weekly training plan for {constraints['start_date']} to {constraints['end_date']}.

# REQUIREMENTS
- {constraints['days_per_week']} workouts
- Target TSS: {constraints['weekly_tss_target']} (±10%)
- Max duration: {constraints['max_duration']} minutes per workout
- Include variety: threshold, VO2max, endurance
- Follow principles from knowledge base

# OUTPUT FORMAT
Return ONLY valid JSON matching this schema:
{{
    "week_number": 3,
    "start_date": "2026-01-20",
    "end_date": "2026-01-26",
    "theme": "Threshold Development",
    "weekly_tss_target": 500,
    "rationale": "Why this week's focus...",
    "workouts": [
        {{
            "date": "2026-01-20",
            "title": "Threshold Intervals",
            "type": "bike",
            "duration": 75,
            "tss": 85,
            "description": "4x8min @ 98% FTP with 3min rests",
            "intervals": [...]
        }}
    ]
}}

NO explanatory text, ONLY JSON.
"""
```

### Prompt Engineering Techniques

#### 1. Chain of Thought

**Problem:** AI gives poorly reasoned answers.  
**Solution:** Ask it to explain reasoning first.

```python
prompt = """
Analyze this athlete's training.

Think step-by-step:
1. Calculate weekly TSS trend
2. Identify workout type distribution
3. Assess recovery adequacy
4. Note performance changes

Then provide recommendations.
"""
```

#### 2. Few-Shot Learning

**Problem:** AI doesn't understand desired format.  
**Solution:** Show examples.

```python
prompt = """
Generate workout intervals.

Example 1:
Input: "Threshold workout, 4x8min"
Output: [
    {"name": "Warmup", "duration": 600, "power": {"type": "percent_ftp", "value": 50}},
    {"name": "Threshold", "duration": 480, "power": {"type": "percent_ftp", "value": 98}, "repeat": 4, "rest": {"duration": 180, "power": {"type": "percent_ftp", "value": 60}}},
    {"name": "Cooldown", "duration": 600, "power": {"type": "percent_ftp", "value": 50}}
]

Now generate for: "{workout_description}"
"""
```

#### 3. Constrained Output

**Problem:** AI adds extra text, breaks JSON.  
**Solution:** Explicitly constrain output.

```python
prompt = """
Generate workout plan.

CRITICAL: Return ONLY valid JSON.
NO explanatory text before or after.
NO markdown code blocks.
NO comments in JSON.
Start with {{ and end with }}
"""
```

#### 4. Self-Correction

**Problem:** AI makes mistakes.  
**Solution:** Ask it to validate its own output.

```python
prompt = """
Generate workout plan.

After generating, validate:
1. Is JSON valid?
2. Do TSS values sum to target?
3. Are workout durations realistic?
4. Is there adequate recovery?

If any validation fails, regenerate corrected version.

Return ONLY final validated JSON.
"""
```

#### 5. Knowledge Grounding

**Problem:** AI makes up facts.  
**Solution:** Ground in provided knowledge.

```python
prompt = f"""
{knowledge_base}

Using ONLY the information above, generate a VO2max workout.

Do not use external knowledge.
Do not make assumptions.
If information is missing, state so explicitly.
"""
```

---

## Model Selection

**File:** [`src/utils/ai_coach_config.py`](../../src/utils/ai_coach_config.py)

### Available Models

```python
from enum import Enum

class AIModel(Enum):
    # Google Gemini (Free)
    GEMINI_FREE = "gemini-1.5-flash-002"
    GEMINI_FLASH_8B = "gemini-1.5-flash-8b"
    GEMINI_2_FLASH = "gemini-2.0-flash-exp"

    # Google Gemini (Paid)
    GEMINI_PRO = "gemini-1.5-pro-002"

    # Anthropic Claude (Paid)
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
```

### Model Comparison

| Model            | Cost     | Speed   | Quality   | Context   | Best For             |
| ---------------- | -------- | ------- | --------- | --------- | -------------------- |
| Gemini Flash     | Free     | Fast    | Good      | 1M tokens | Development, testing |
| Gemini Flash 8B  | Free     | Fastest | Decent    | 1M tokens | Simple analysis      |
| Gemini 2.0 Flash | Free     | Fast    | Better    | 1M tokens | Weekly plans         |
| Gemini Pro       | $0.50/1M | Medium  | Best      | 2M tokens | Complex reasoning    |
| Claude Sonnet    | $3/1M    | Medium  | Excellent | 200K      | Detailed coaching    |
| Claude Haiku     | $0.25/1M | Fast    | Good      | 200K      | Quick analysis       |

### Model Selection Logic

```python
def select_model(task_complexity: str, budget: float) -> AIModel:
    """
    Select optimal model based on task and budget.

    Args:
        task_complexity: 'simple', 'medium', 'complex'
        budget: Maximum cost per request ($)
    """
    if budget == 0:
        # Free models only
        if task_complexity == 'simple':
            return AIModel.GEMINI_FLASH_8B
        else:
            return AIModel.GEMINI_2_FLASH

    elif task_complexity == 'complex':
        # Need best quality
        if budget >= 0.10:
            return AIModel.CLAUDE_SONNET
        else:
            return AIModel.GEMINI_PRO

    else:
        # Medium complexity
        if budget >= 0.01:
            return AIModel.CLAUDE_HAIKU
        else:
            return AIModel.GEMINI_FREE
```

### Dynamic Model Fallback

If a model fails, automatically try alternatives:

```python
class AICoachEngine:
    FALLBACK_ORDER = [
        AIModel.GEMINI_2_FLASH,
        AIModel.GEMINI_FREE,
        AIModel.GEMINI_FLASH_8B,
        AIModel.GEMINI_PRO,
        AIModel.CLAUDE_HAIKU,
        AIModel.CLAUDE_SONNET
    ]

    def _call_llm_with_fallback(self, prompt: str):
        for model in self.FALLBACK_ORDER:
            try:
                return self._call_llm(prompt, model=model)
            except APIError:
                continue

        raise Exception("All models failed")
```

---

## Usage Examples

### Example 1: Generate Weekly Plan

```python
from src.utils.ai_coach_engine import AICoachEngine, AIModel

coach = AICoachEngine(model=AIModel.GEMINI_FREE)

result = coach.generate_weekly_plan(
    start_date='2026-01-20',
    athlete_id=1,
    constraints={
        'available_days': ['Mon', 'Tue', 'Thu', 'Sat'],
        'weekly_tss_target': 500,
        'max_duration': 90
    }
)

if result.success:
    print(result.analysis)
    print(f"Generated {len(result.workout_plan['workouts'])} workouts")
    print(f"Cost: ${result.metadata['cost']:.4f}")
else:
    print("Errors:", result.errors)
```

### Example 2: Analyze Recent Training

```python
# Get analysis without generating plan
analysis = coach.analyze_recent_training(
    athlete_id=1,
    days_back=14
)

print(analysis)
"""
Training Summary (Last 14 Days):
- Total TSS: 485 (target: 500)
- Hard workouts: 3 (threshold, VO2max, sweet spot)
- Endurance: 2 long rides (120min, 90min)
- Recovery: 2 easy spins

Strengths:
- Consistent intensity progression
- Good workout variety
- Adequate recovery

Areas for Improvement:
- Slightly below TSS target
- Could add one more endurance ride

Recommendations:
- Maintain current intensity
- Add 60-90min Zone 2 ride this week
- Consider recovery week in 2 weeks
"""
```

### Example 3: Custom Coaching Notes

```python
from src.utils.coaching_notes import CoachingNotesManager

notes = CoachingNotesManager()

# Add athlete-specific guidance
notes.add_note(
    athlete_id=1,
    topic='threshold',
    content='Jake responds well to 8-10min intervals vs 20min sustained'
)

notes.add_note(
    athlete_id=1,
    topic='recovery',
    content='Needs full rest day after VO2max sessions'
)

# AI coach will incorporate these notes
coach = AICoachEngine()
result = coach.generate_weekly_plan(athlete_id=1, start_date='2026-01-20')
# Plan will use 8-10min threshold intervals, full rest after VO2max
```

### Example 4: Race Preparation

```python
result = coach.generate_race_prep_plan(
    athlete_id=1,
    race_date='2026-02-15',
    race_type='criterium',
    weeks_out=4
)

# Automatically creates:
# - Week 4: Build (high TSS, mixed intensity)
# - Week 3: Overload (peak TSS, race-specific work)
# - Week 2: Recovery (50% TSS reduction)
# - Week 1: Taper (light intensity, race sharpening)
```

### Example 5: Custom RAG Context

```python
from src.utils.rag_context_loader import RAGContextLoader

loader = RAGContextLoader()
loader.load_markdown_files('data/rag_context/')

# Add custom knowledge
loader.add_chunk(
    title='Cold Weather Adaptations',
    content='''
    When training in cold weather (< 40°F):
    - Expect 5-10w lower FTP indoors
    - Increase warmup duration by 50%
    - Focus on cadence drills (harder to push big gears)
    ''',
    topics={'winter', 'indoor', 'cold-weather'},
    priority='HIGH'
)

# Now available for AI coach
coach = AICoachEngine(rag_loader=loader)
result = coach.generate_weekly_plan(athlete_id=1, start_date='2026-01-20')
# Will incorporate cold weather guidance if relevant
```

---

## Advanced Patterns

### Pattern 1: Multi-Week Periodization

```python
def generate_mesocycle(
    coach: AICoachEngine,
    start_date: str,
    weeks: int,
    focus: str
) -> List[CoachingResult]:
    """
    Generate multi-week training block with progressive overload.
    """
    results = []

    for week in range(weeks):
        # Calculate TSS progression
        base_tss = 500
        if week == weeks - 1:
            tss = base_tss * 0.6  # Recovery week
        else:
            tss = base_tss * (1 + 0.05 * week)  # 5% weekly increase

        # Generate week
        result = coach.generate_weekly_plan(
            start_date=add_weeks(start_date, week),
            athlete_id=1,
            constraints={
                'weekly_tss_target': tss,
                'focus': focus
            }
        )
        results.append(result)

    return results

# Generate 4-week threshold block
results = generate_mesocycle(
    coach=coach,
    start_date='2026-01-20',
    weeks=4,
    focus='threshold'
)
```

### Pattern 2: Adaptive Planning

```python
def adaptive_weekly_plan(
    coach: AICoachEngine,
    athlete_id: int,
    start_date: str
) -> CoachingResult:
    """
    Adjust plan based on recent performance and recovery.
    """
    # Analyze recent training
    analysis = coach.analyze_recent_training(athlete_id, days_back=7)

    # Detect fatigue signals
    fatigue_score = calculate_fatigue(analysis)

    # Adjust TSS target
    base_tss = 500
    if fatigue_score > 0.8:
        # High fatigue, reduce load
        tss_target = base_tss * 0.7
        focus = 'recovery'
    elif fatigue_score < 0.3:
        # Fresh, push harder
        tss_target = base_tss * 1.15
        focus = 'progression'
    else:
        tss_target = base_tss
        focus = 'maintenance'

    # Generate adapted plan
    return coach.generate_weekly_plan(
        start_date=start_date,
        athlete_id=athlete_id,
        constraints={
            'weekly_tss_target': tss_target,
            'focus': focus
        }
    )
```

### Pattern 3: A/B Testing Workouts

```python
def generate_workout_variants(
    coach: AICoachEngine,
    workout_type: str,
    count: int = 3
) -> List[Dict]:
    """
    Generate multiple variants of same workout type.
    Useful for finding what athlete responds to best.
    """
    variants = []

    for i in range(count):
        prompt = f"""
        Generate a {workout_type} workout.
        This is variant {i+1} of {count}.
        Make it different from previous variants while maintaining similar TSS.
        """

        result = coach._call_llm(prompt)
        variants.append(json.loads(result))

    return variants

# Generate 3 different threshold workouts
variants = generate_workout_variants(
    coach=coach,
    workout_type='threshold',
    count=3
)

# Variant 1: 4x8min @ 98% FTP
# Variant 2: 3x12min @ 95% FTP
# Variant 3: 2x20min @ 93% FTP
# All similar TSS, different stimulus
```

### Pattern 4: Coached Workout Execution

```python
def real_time_coaching(
    workout: Dict,
    athlete_feedback: List[str]
) -> str:
    """
    Provide in-workout coaching based on athlete feedback.
    """
    coach = AICoachEngine()

    prompt = f"""
    You are coaching an athlete through this workout:
    {json.dumps(workout)}

    They've provided this feedback during the workout:
    {chr(10).join(f'- {f}' for f in athlete_feedback)}

    Provide encouraging, tactical coaching advice.
    Keep it brief (1-2 sentences).
    """

    return coach._call_llm(prompt)

# During workout
feedback = [
    "3 minutes into interval 2, HR climbing fast",
    "Legs feel heavy, cadence dropping to 85"
]

advice = real_time_coaching(workout, feedback)
# Returns: "You're doing great! Focus on smooth pedal strokes.
#           If HR keeps climbing, dial back 2-3% to finish strong."
```

---

## Troubleshooting

### Issue: "No Gemini API key"

**Solution:** Set environment variable:

```bash
export GEMINI_API_KEY="your_key_here"
# Or for Claude:
export ANTHROPIC_API_KEY="your_key_here"
```

### Issue: "Rate limit exceeded"

**Solution:** Model falls back automatically. Or use paid tier:

```python
coach = AICoachEngine(model=AIModel.CLAUDE_HAIKU)
```

### Issue: Generated plan has invalid JSON

**Solution:** Already handled with self-correction. If persists:

```python
# Increase validation strictness
coach.validation_strict = True
coach.max_regeneration_attempts = 5
```

### Issue: Plan doesn't follow constraints

**Solution:** Be more explicit in constraints:

```python
constraints = {
    'weekly_tss_target': 500,
    'weekly_tss_min': 450,  # Add minimum
    'weekly_tss_max': 550,  # Add maximum
    'required_recovery_days': 2,
    'max_consecutive_hard_days': 2
}
```

### Issue: AI uses outdated knowledge

**Solution:** Update RAG context files in `data/rag_context/`

### Issue: Cost too high

**Solution:** Use free models:

```python
coach = AICoachEngine(model=AIModel.GEMINI_FREE)
```

---

## Related Documentation

- [Data Processing Pipeline](./data-processing-pipeline.md) - How workout data is processed
- [Database Schema](./database-schema.md) - Where plans are stored
- [API Endpoints](./api-endpoints.md) - HTTP interface to coaching engine
- [Development Workflow](../agent-instructions/development-workflow.md) - Testing AI components

---

**Last Updated:** January 14, 2026  
**Maintainer:** Fitness Tracker Development Team
