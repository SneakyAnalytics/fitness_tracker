"""
AIChatSession – manages one conversational coaching session per week.

Phase state machine:
  ANALYSIS  → coach opens with week summary + initial questions
  CLARIFYING → back-and-forth Q&A until READY_TO_GENERATE sentinel
  GENERATING → one-shot plan generation call
  REVIEWING  → athlete can ask surgical edits
  SAVED      → plan saved to DB + Zwift files generated
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

# ---------------------------------------------------------------------------
# Path bootstrap (works whether imported from streamlit or run directly)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.dirname(_HERE)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

SENTINEL = "READY_TO_GENERATE"


class AIChatSession:
    """
    Encapsulates one week's interactive coaching conversation.

    Usage
    -----
    session = AIChatSession.load_or_create(week_start_date, db, coach, db_queries)
    # Then in Streamlit:
    for chunk in session.begin_analysis():
        yield chunk
    for chunk in session.chat(user_message):
        yield chunk
    for chunk in session.generate_plan():
        yield chunk
    for chunk in session.apply_surgical_edit(feedback):
        yield chunk
    session.save_plan(zwift_dir)
    """

    # ------------------------------------------------------------------ init

    def __init__(
        self,
        week_start_date: str,
        messages: Optional[List[Dict]] = None,
        current_plan: Optional[Dict] = None,
        phase: str = "ANALYSIS",
    ):
        self.week_start_date = week_start_date
        self.messages: List[Dict] = messages or []
        self.current_plan: Optional[Dict] = current_plan
        self.phase: str = phase

        # Lazy-loaded heavy objects (set by load_or_create)
        self._coach = None
        self._db = None
        self._prompts = None
        self._weekly_summary: Optional[Dict] = None
        self._comprehensive_context: Optional[Dict] = None
        self._coaching_notes: Optional[Dict] = None
        self._system_prompt: Optional[str] = None
        self._training_state: Optional[str] = None
        self._week_target = None  # periodization.WeekTarget for the plan week
        self._last_turn_text: str = ""

    # ----------------------------------------------------------- class method

    @classmethod
    def load_or_create(
        cls,
        week_start_date: str,
        db,
        coach,
    ) -> "AIChatSession":
        """
        Load existing session from DB or create a fresh one.
        Also wires up the heavy dependencies.
        """
        row = db.load_chat_session(week_start_date)
        if row:
            session = cls(
                week_start_date=week_start_date,
                messages=row["messages"],
                current_plan=row["current_plan"],
                phase=row["phase"],
            )
        else:
            session = cls(week_start_date=week_start_date)

        session._coach = coach
        session._db = db
        return session

    # --------------------------------------------------------- lazy loading

    @property
    def _tools_enabled(self) -> bool:
        """Claude models get database tools; Gemini keeps the prompt-only flow."""
        model = getattr(self._coach, "model", None)
        return bool(model is not None and model.is_claude and getattr(self._coach, "client", None))

    def _ensure_context(self, week_end_date: str) -> None:
        """Load DB context if not already loaded."""
        if self._system_prompt is not None:
            return

        from src.utils.ai_database_queries import AICoachDatabaseQueries
        from src.utils.coaching_notes import CoachingNotesManager
        from src.utils.ai_prompts import AICoachPrompts
        from src.storage import continuity as continuity_store
        from src.storage import goals as goals_store
        from src.utils.coach_context import build_training_state

        db_queries = AICoachDatabaseQueries()
        coaching_mgr = CoachingNotesManager()

        self._weekly_summary = self._db.generate_weekly_summary(
            self.week_start_date, week_end_date
        ) or {}
        self._comprehensive_context = db_queries.get_comprehensive_context(weeks_back=4)

        # The Settings page is the single source of truth for FTP.
        settings_ftp = (self._db.get_athlete_settings() or {}).get('ftp')
        athlete_profile = dict(coaching_mgr.athlete_profile.__dict__)
        if settings_ftp:
            athlete_profile['current_ftp'] = settings_ftp

        self._coaching_notes = {
            'athlete_profile': athlete_profile,
            'personality': coaching_mgr.personality.__dict__,
            'current_training_phase': coaching_mgr.current_training_phase,
            'next_week_focus': coaching_mgr.next_week_focus,
            'observations': [obs.__dict__ for obs in coaching_mgr.observations],
            'coaching_continuity': continuity_store.recent_continuity(3, self._db.db_path),
            'goals': goals_store.list_goals(db_path=self._db.db_path),
            'achievements': [a.to_dict() for a in coaching_mgr.achievements],
        }

        self._training_state, self._week_target = build_training_state(
            self.week_start_date, settings_ftp, self._db.db_path
        )

        prompts = AICoachPrompts()
        prior_sessions = self._db.load_prior_chat_sessions(
            before_date=self.week_start_date, n=2
        )
        self._system_prompt = prompts.build_chat_system_prompt(
            weekly_summary=self._weekly_summary,
            comprehensive_context=self._comprehensive_context,
            coaching_notes=self._coaching_notes,
            prior_sessions=prior_sessions,
            training_state=self._training_state,
            tools_enabled=self._tools_enabled,
        )
        self._prompts = prompts

    # ------------------------------------------------------------- tool loop

    def _week_end_date(self) -> str:
        from datetime import timedelta as _td
        return (datetime.strptime(self.week_start_date, '%Y-%m-%d') + _td(days=6)).strftime('%Y-%m-%d')

    _OPENING = "Please start this week's coaching session now."

    def _api_messages(self) -> List[Dict[str, Any]]:
        msgs = [{"role": "user", "content": self._OPENING}]
        msgs += [{"role": m["role"], "content": m["content"]} for m in self.messages
                 if m.get("role") in ("user", "assistant") and m.get("content")]
        return msgs

    def _converse_with_tools(self) -> Generator[str, None, None]:
        """One coach turn with tool use. Streams text plus short status lines;
        only the coach's own words are kept in self._last_turn_text."""
        from src.utils.coach_tools import stream_tool_conversation

        api, extra = self._coach.messages_api()
        result: Dict[str, Any] = {}
        for kind, value in stream_tool_conversation(
                api, extra, self._coach.model.value, self._system_prompt, self._api_messages(),
                db_path=self._db.db_path, on_usage=self._coach._record_usage, result=result):
            yield value if kind == "text" else f"\n\n_🔎 {value}…_\n\n"
        self._last_turn_text = result.get("text", "")

    def _converse(self, prompt_fallback: str) -> Generator[str, None, None]:
        """Run one coach turn; sets self._last_turn_text."""
        if self._tools_enabled:
            yield from self._converse_with_tools()
            return
        full_text = ""
        for chunk in self._coach._call_api_streaming(prompt_fallback, temperature=0.7, max_tokens=1500):
            full_text += chunk
            yield chunk
        self._last_turn_text = full_text

    # ------------------------------------------------------- public streaming

    def begin_analysis(self, week_end_date: str) -> Generator[str, None, None]:
        """
        First message – coach opens with the week analysis and initial questions.
        Streams text chunks; caller should collect full text and call persist().
        """
        self._ensure_context(week_end_date)

        prompt = self._system_prompt + "\n\n# Begin\nPlease start the coaching session now."
        yield from self._converse(prompt)
        full_text = self._last_turn_text

        clean, triggered = _strip_sentinel(full_text)
        self._append_assistant(clean)
        if triggered:
            self.phase = "GENERATING"
        else:
            self.phase = "CLARIFYING"
        yield ""  # signal end

    def chat(self, user_message: str) -> Generator[str, None, None]:
        """
        Handle an athlete message during CLARIFYING phase.
        Streams the coach reply; detects READY_TO_GENERATE sentinel.
        Auto-triggers generation after 3 user turns if sentinel never arrived.
        """
        # Advance from ANALYSIS to CLARIFYING if not already there
        if self.phase == "ANALYSIS":
            self.phase = "CLARIFYING"

        self._append_user(user_message)

        # A session rebuilt from the DB (e.g. after a Streamlit rerun) has no
        # context loaded yet; previously it silently chatted with an empty prompt.
        self._ensure_context(self._week_end_date())
        yield from self._converse(self._build_conversation_prompt())
        full_text = self._last_turn_text

        clean, triggered = _strip_sentinel(full_text)
        self._append_assistant(clean)
        if triggered:
            self.phase = "GENERATING"
        else:
            # Auto-trigger after 3 user turns to avoid infinite clarifying loops
            user_turns = sum(1 for m in self.messages if m.get("role") == "user")
            if user_turns >= 3:
                self.phase = "GENERATING"
        yield ""

    def generate_plan(self, week_end_date: str) -> Generator[str, None, None]:
        """
        One-shot plan generation.  Streams JSON; parses and stores in current_plan.
        """
        self._ensure_context(week_end_date)

        # Calculate the correct upcoming week number and start date.
        # next_week_start_date is 7 days after the current session's week start.
        # next_week_number is derived from the DB (same logic as save_plan_to_database).
        import sqlite3 as _sqlite3
        from datetime import timedelta as _td
        next_week_start_date = (
            datetime.strptime(self.week_start_date, '%Y-%m-%d') + _td(days=7)
        ).strftime('%Y-%m-%d')
        try:
            with _sqlite3.connect(self._db.db_path) as _wn_conn:
                existing = _wn_conn.execute(
                    "SELECT weekNumber FROM weekly_plans WHERE startDate = ?",
                    (next_week_start_date,)
                ).fetchone()
                if existing:
                    next_week_number = existing[0]
                else:
                    max_row = _wn_conn.execute(
                        "SELECT MAX(weekNumber) FROM weekly_plans"
                    ).fetchone()
                    next_week_number = (max_row[0] or 0) + 1
        except Exception:
            next_week_number = 1

        # Use conversation history as the "analysis" context
        conversation_summary = _messages_to_text(self.messages)
        user_context = {
            "week_feedback": conversation_summary,
            "context_type": "upcoming_week",
            "next_week_number": next_week_number,
            "next_week_start_date": next_week_start_date,
        }

        from src.utils.ai_prompts import AICoachPrompts, PromptContext
        prompts = self._prompts or AICoachPrompts()
        context = PromptContext(
            athlete_profile=self._coaching_notes.get("athlete_profile", {}),
            coaching_notes=self._coaching_notes,
            weekly_summary=self._weekly_summary,
            comprehensive_context=self._comprehensive_context,
            user_context=user_context,
            training_state=self._training_state,
        )
        # analysis_output is the conversation transcript so the AI has full context
        gen_prompt = prompts.build_workout_generation_prompt(
            context, analysis_output=conversation_summary
        )

        full_text = ""
        for chunk in self._coach._call_api_streaming(gen_prompt, temperature=0.3,
                                                     max_tokens=32000):
            full_text += chunk
            yield chunk

        # Parse JSON from response
        plan = _extract_json(full_text)

        # Enforce the computed load band: one corrective regeneration if outside it.
        band_error = self._band_error(plan)
        if band_error:
            yield f"\n\n*({band_error} — regenerating inside the band…)*\n\n"
            retry_prompt = (gen_prompt + "\n\n# Correction\nYour previous plan was rejected: " + band_error
                            + ". Regenerate the full plan with plannedTSS and the daily workouts inside the band.")
            retry_text = ""
            for chunk in self._coach._call_api_streaming(retry_prompt, temperature=0.3, max_tokens=32000):
                retry_text += chunk
                yield chunk
            retried = _extract_json(retry_text)
            if retried:
                plan, full_text = retried, retry_text
                if self._band_error(retried):
                    yield "\n\n*(Still outside the band — review the TSS before saving.)*\n\n"

        if not plan:
            # First pass JSON not parseable — try structural extraction of day objects
            partial_plan, missing_days = _extract_partial_plan(full_text)
            if partial_plan and not missing_days:
                # All 7 days found structurally — use them directly
                plan = partial_plan
            elif partial_plan and missing_days:
                # Some days missing — ask model to complete them
                yield "\n\n*(Plan was cut off — continuing with remaining days…)*\n\n"
                cont_prompt = _build_day_continuation_prompt(partial_plan, missing_days)
                extra_text = ""
                for chunk in self._coach._call_api_streaming(
                    cont_prompt, temperature=0.3, max_tokens=8000
                ):
                    extra_text += chunk
                    yield chunk
                extra = _extract_json(extra_text)
                if extra and "days" in extra:
                    partial_plan["days"].extend(extra["days"])
                    partial_plan["days"].sort(key=lambda d: d.get("dayNumber", 0))
                    # Deduplicate by dayNumber, keep last (continuation wins)
                    seen: Dict[int, Dict] = {}
                    for d in partial_plan["days"]:
                        seen[d.get("dayNumber", 0)] = d
                    partial_plan["days"] = sorted(seen.values(), key=lambda d: d.get("dayNumber", 0))
                    if len(partial_plan["days"]) >= 7:
                        plan = partial_plan

        if plan:
            self.current_plan = plan
            self.phase = "REVIEWING"
            self._append_assistant("✅ Plan generated! Review it below — ask me to adjust any days.")
        else:
            # Reset phase so user can retry via the Generate button
            self.phase = "CLARIFYING"
            self._append_assistant(
                "⚠️ I couldn't complete the full plan. Press **⚡ Generate My Plan Now** to try again."
            )
        yield ""

    def _band_error(self, plan: Optional[Dict]) -> Optional[str]:
        if not plan or not self._week_target:
            return None
        from src.utils.periodization import validate_plan_tss
        tss = plan.get("plannedTSS") or {}
        return validate_plan_tss(tss.get("min"), tss.get("max"), self._week_target.to_dict())

    def apply_surgical_edit(self, feedback: str) -> Generator[str, None, None]:
        """
        Apply targeted edits to specific days of the current plan.
        AI returns {"modified_days": [...]} delta; we merge it in.
        """
        if not self.current_plan:
            yield "No plan loaded – please generate a plan first."
            return

        from src.utils.ai_prompts import AICoachPrompts
        prompts = self._prompts or AICoachPrompts()
        edit_prompt = prompts.build_surgical_edit_prompt(self.current_plan, feedback)

        full_text = ""
        for chunk in self._coach._call_api_streaming(edit_prompt, temperature=0.2,
                                                     max_tokens=4000):
            full_text += chunk
            yield chunk

        delta = _extract_json(full_text)
        if delta and "modified_days" in delta:
            self._merge_days(delta["modified_days"])
            self._append_user(feedback)
            self._append_assistant(f"✅ Updated {len(delta['modified_days'])} day(s) as requested.")
        else:
            self._append_user(feedback)
            self._append_assistant("⚠️ Could not parse the edit response. Please try rephrasing.")
        yield ""

    def save_plan(self, zwift_dir: str) -> tuple[bool, str, list]:
        """
        Persist plan to DB and generate Zwift .zwo files.
        Also extracts any new goals mentioned during the conversation.
        Returns (success, message, zwift_files).
        """
        if not self.current_plan:
            return False, "No plan to save", []

        plan_start_date = self.current_plan.get("startDate")
        success, message, zwift_files = self._coach.save_plan_to_database(
            workout_plan=self.current_plan,
            start_date=plan_start_date,
            output_dir=zwift_dir,
        )
        if success:
            self.phase = "SAVED"
            self._db.save_chat_session(
                self.week_start_date, self.messages, self.current_plan, self.phase
            )
            from src.storage.events import record_event
            for step in (self._save_rationale, self._save_continuity):
                try:
                    step(plan_start_date)
                except Exception as exc:  # never fail a saved plan over bookkeeping
                    record_event("warning", "ai_chat_session", f"{step.__name__} failed: {exc}")
            if not self._tools_enabled:
                # Claude records goals live via tools; the prompt-only flow extracts them afterwards.
                for step in (self._extract_and_save_goals, self._extract_and_update_goals):
                    try:
                        step()
                    except Exception as exc:
                        record_event("warning", "ai_chat_session", f"{step.__name__} failed: {exc}")
        return success, message, zwift_files

    # ----------------------------------------------------- persistence helper

    def _save_rationale(self, plan_start_date: str) -> None:
        """Store why this week's targets were chosen, for next week's coach to read."""
        import sqlite3 as _sqlite3
        rationale = {
            "target": self._week_target.to_dict() if self._week_target else None,
            "plan_notes": (self.current_plan or {}).get("notes"),
            "planned_tss": (self.current_plan or {}).get("plannedTSS"),
        }
        with _sqlite3.connect(self._db.db_path) as conn:
            conn.execute("UPDATE weekly_plans SET rationale = ? WHERE startDate = ?",
                         (json.dumps(rationale, default=str), plan_start_date))

    def _save_continuity(self, plan_start_date: str) -> None:
        """Distil this session into continuity notes (one small model call)."""
        from src.storage.continuity import save_continuity
        conversation = _messages_to_text(self.messages)
        if not conversation.strip():
            return
        days = [f"- Day {d.get('dayNumber')}: " + ", ".join(w.get("name", "") for w in d.get("workouts", []))
                for d in (self.current_plan or {}).get("days", [])]
        prompt = f"""Summarise this weekly coaching session as continuity notes for next week's coach.

## Conversation
{conversation}

## Plan just saved (week of {plan_start_date})
{chr(10).join(days)}

Return ONLY a JSON object:
{{"key_observations": [...], "progression_notes": [...], "areas_to_monitor": [...], "next_week_priorities": [...]}}
Each list: 1-4 short, specific items (numbers, workouts, constraints the athlete stated). No markdown."""
        text, _ = self._coach._call_api(prompt, temperature=0.1, max_tokens=2000)
        notes = _extract_json(text)
        if isinstance(notes, dict):
            save_continuity(self.week_start_date, notes, self._db.db_path)

    def _extract_and_save_goals(self) -> None:
        """Prompt-only flow (no tools): pull NEW goals the athlete stated into the goals table."""
        from src.storage import goals as goals_store

        conversation = _messages_to_text(self.messages)
        if not conversation.strip():
            return
        existing = goals_store.list_goals(include_inactive=True, db_path=self._db.db_path)
        existing_descriptions = [g["description"].lower() for g in existing]

        prompt = f"""Identify NEW training goals or events the athlete explicitly stated in this conversation.

## Existing goals (do NOT re-add)
{chr(10).join(f"- {d}" for d in existing_descriptions) or "(none)"}

## Conversation
{conversation}

Return ONLY a JSON array (possibly empty) of objects:
{{"description": "...", "category": "event|power|endurance|technical|consistency", "priority": 1-3,
  "target_date": "YYYY-MM-DD or null", "note": "detail the athlete gave"}}"""
        text, _ = self._coach._call_api(prompt, temperature=0.1, max_tokens=1500)
        new_goals = _extract_json_array(text)
        if not isinstance(new_goals, list):
            return
        for g in new_goals:
            if isinstance(g, dict) and g.get("description") and g["description"].lower() not in existing_descriptions:
                goals_store.add_goal(g["description"], g.get("category", "event"), int(g.get("priority", 2)),
                                     g.get("target_date"), g.get("note"), self._db.db_path)

    def _extract_and_update_goals(self) -> None:
        """Prompt-only flow (no tools): apply completed/abandoned/paused statements to goals."""
        from src.storage import goals as goals_store

        active = goals_store.list_goals(db_path=self._db.db_path)
        conversation = _messages_to_text(self.messages)
        if not active or not conversation.strip():
            return
        goal_list = "\n".join(f"- #{g['id']}: {g['description']}" for g in active)
        prompt = f"""Did the athlete EXPLICITLY say they completed, abandoned or paused any of these goals?

## Active goals
{goal_list}

## Conversation
{conversation}

Return ONLY a JSON array (possibly empty) of {{"goal_id": <id>, "new_status": "completed|abandoned|paused",
"note": "what they said"}}. Do not infer from vague hints."""
        text, _ = self._coach._call_api(prompt, temperature=0.1, max_tokens=1500)
        updates = _extract_json_array(text)
        if not isinstance(updates, list):
            return
        valid_ids = {g["id"] for g in active}
        for u in updates:
            if isinstance(u, dict) and u.get("goal_id") in valid_ids and u.get("new_status") in goals_store.VALID_STATUSES:
                goals_store.update_goal(u["goal_id"], status=u["new_status"], progress_note=u.get("note"),
                                        db_path=self._db.db_path)

    def persist(self) -> None:
        """Write current session state to the database."""
        self._db.save_chat_session(
            self.week_start_date,
            self.messages,
            self.current_plan,
            self.phase,
        )

    # --------------------------------------------------------- internal helpers

    def _append_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def _append_assistant(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    def _build_conversation_prompt(self) -> str:
        """Reconstruct full prompt from system context + message history."""
        base = self._system_prompt or ""
        convo = _messages_to_prompt(self.messages)
        return base + "\n\n# Conversation So Far\n\n" + convo + "\n\nAssistant:"

    def _merge_days(self, modified_days: List[Dict]) -> None:
        """Merge modified day objects into current_plan by dayNumber."""
        if not self.current_plan:
            return
        day_map = {d["dayNumber"]: i for i, d in enumerate(self.current_plan.get("days", []))}
        for mod_day in modified_days:
            idx = day_map.get(mod_day.get("dayNumber"))
            if idx is not None:
                self.current_plan["days"][idx] = mod_day


# --------------------------------------------------------------------------
# Module-level helpers
# --------------------------------------------------------------------------

def _strip_sentinel(text: str) -> tuple[str, bool]:
    """Remove READY_TO_GENERATE sentinel token from text. Returns (clean, found)."""
    if SENTINEL in text:
        clean = text.replace(SENTINEL, "").strip()
        return clean, True
    return text, False


def _messages_to_text(messages: List[Dict]) -> str:
    """Flatten message history to plain text for context injection."""
    lines = []
    for m in messages:
        role = m.get("role", "user").title()
        lines.append(f"{role}: {m.get('content', '')}")
    return "\n\n".join(lines)


def _messages_to_prompt(messages: List[Dict]) -> str:
    """Format messages as a readable turn-by-turn conversation."""
    lines = []
    for m in messages:
        role = "Coach" if m.get("role") == "assistant" else "Athlete"
        lines.append(f"**{role}:** {m.get('content', '')}")
    return "\n\n".join(lines)


def _extract_partial_plan(text: str):
    """
    Extract whatever complete day objects exist from a potentially truncated
    plan JSON response.  Uses json.JSONDecoder.raw_decode() to parse each day
    object in sequence — this is robust against nested objects and string
    literals that contain braces.

    Returns (partial_plan_dict, list_of_missing_day_numbers).
    Returns (None, []) if nothing useful was found.
    """
    import re

    if "{" not in text:
        return None, []

    decoder = json.JSONDecoder()

    # ------------------------------------------------------------------ days
    # Locate the opening [ of the "days" array
    days_key_pos = text.find('"days"')
    if days_key_pos == -1:
        return None, []
    arr_start = text.find("[", days_key_pos)
    if arr_start == -1:
        return None, []

    days: List[Dict] = []
    pos = arr_start + 1
    while pos < len(text):
        # skip whitespace / commas
        while pos < len(text) and text[pos] in " \t\n\r,":
            pos += 1
        if pos >= len(text) or text[pos] == "]":
            break
        if text[pos] != "{":
            break
        try:
            obj, new_pos = decoder.raw_decode(text, pos)
            if isinstance(obj, dict) and "dayNumber" in obj:
                days.append(obj)
            pos = new_pos
        except json.JSONDecodeError:
            # Current day object is truncated — stop here
            break

    if not days:
        return None, []

    # -------------------------------------------------------- top-level fields
    partial: Dict[str, Any] = {}
    for field in ("weekNumber", "startDate", "ftp"):
        m = re.search(rf'"{field}"\s*:\s*("[^"]*"|\d+)', text)
        if m:
            try:
                partial[field] = json.loads(m.group(1))
            except Exception:
                partial[field] = m.group(1).strip('"')

    # plannedTSS may span multiple lines — grab a wider window
    tss_m = re.search(r'"plannedTSS"\s*:\s*(\{[^}]+\})', text)
    if tss_m:
        try:
            partial["plannedTSS"] = json.loads(tss_m.group(1))
        except Exception:
            partial["plannedTSS"] = {"min": 400, "max": 500}

    partial["days"] = days
    present = {d.get("dayNumber") for d in days}
    missing = [i for i in range(1, 8) if i not in present]
    return partial, missing


def _build_day_continuation_prompt(partial_plan: Dict, missing_days: List[int]) -> str:
    """
    Build a focused prompt that asks the AI to generate only the missing days
    to complete a truncated 7-day plan.
    """
    _day_names = {
        1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
        5: "Friday", 6: "Saturday", 7: "Sunday",
    }
    from datetime import date, timedelta

    start_str = partial_plan.get("startDate", "")
    ftp = partial_plan.get("ftp", 305)
    week_num = partial_plan.get("weekNumber", "N/A")

    try:
        start_date = date.fromisoformat(start_str)
    except Exception:
        start_date = date.today()

    missing_desc = ", ".join(
        f"Day {d} ({_day_names[d]}, {(start_date + timedelta(days=d - 1)).isoformat()})"
        for d in missing_days
    )
    existing_json = json.dumps(partial_plan.get("days", []), indent=2)
    present_nums = [d.get("dayNumber") for d in partial_plan.get("days", [])]

    return f"""You are completing a 7-day training plan that was cut off mid-generation.

Week {week_num} starting {start_str} | FTP: {ftp}W

Days already generated (days {present_nums}) — use these for continuity/context:
{existing_json}

You MUST now generate ONLY the following missing days: {missing_desc}

Return ONLY a JSON object with a single \"days\" array containing exactly those missing day objects.
Match the exact same format as the existing days above.
No markdown, no extra text — pure JSON:
{{\"days\": [<the missing day objects here>]}}"""


def _extract_json_array(text: str) -> Optional[List]:
    """Extract a JSON array (``_extract_json`` only finds objects)."""
    import re
    stripped = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    start = stripped.find("[")
    if start == -1:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(stripped, start)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, list) else None


def _extract_json(text: str) -> Optional[Dict]:
    """
    Try to extract the outermost JSON object from a text response.

    Strategy (in order):
    1. Greedy fenced-code-block match  (```json ... ```)
    2. json.JSONDecoder.raw_decode() starting at the first '{'
       (tolerates trailing text / model commentary after the object)
    3. Classic first-{…last-} slice + json.loads
       (last-resort for cases where raw_decode can't start cleanly)
    """
    import re

    start_idx = text.find("{")
    if start_idx == -1:
        return None

    # 1. Fenced block: use GREEDY inner match so we capture the whole object
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # 2. raw_decode — best for "JSON + trailing commentary" or valid JSON
    try:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text, start_idx)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 3. Brute-force slice between first { and last }
    end_idx = text.rfind("}")
    if end_idx > start_idx:
        try:
            return json.loads(text[start_idx : end_idx + 1])
        except json.JSONDecodeError:
            pass

    return None
