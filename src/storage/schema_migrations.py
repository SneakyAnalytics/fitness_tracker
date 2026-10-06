"""Ordered, versioned schema migrations.

Every schema change goes here as a new numbered entry; never edit an applied
one. `apply_migrations` records progress in `schema_version`, so each migration
runs exactly once per database. Failures raise: a half-migrated schema must not
be silently papered over (that is how the manual-match bug hid for months).
"""
import sqlite3
import threading
from typing import Callable, List, Tuple

_applied_paths = set()
_lock = threading.Lock()


def _columns(conn: sqlite3.Connection, table: str) -> List[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _add_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _m1_matching_columns(conn):
    # Previously only added by hand-run scripts in migrations/, so fresh DBs lacked them.
    _add_column(conn, "workouts", "proposed_workout_name", "TEXT")
    _add_column(conn, "workouts", "matched_at", "TIMESTAMP")
    _add_column(conn, "workouts", "match_source", "TEXT")


def _m2_proposed_workout_fk(conn):
    """Link completed workouts to planned workouts by id instead of by name.

    Names repeat across weeks ("Active Recovery Spin" x15), so the name alone is
    ambiguous. Backfill only where the name resolves to exactly one planned
    workout: same day first, else the unique one within +/-7 days. Custom labels
    for unplanned sessions stay NULL, as do genuinely ambiguous rows.
    """
    _add_column(conn, "workouts", "proposed_workout_id", "INTEGER REFERENCES proposed_workouts(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workouts_proposed_workout_id ON workouts(proposed_workout_id)")
    rows = conn.execute(
        "SELECT id, workout_day, proposed_workout_name FROM workouts "
        "WHERE proposed_workout_name IS NOT NULL AND proposed_workout_name != '' "
        "AND proposed_workout_id IS NULL"
    ).fetchall()
    for workout_id, day, name in rows:
        same_day = conn.execute(
            "SELECT pw.id FROM proposed_workouts pw JOIN daily_plans dp ON pw.dailyPlanId = dp.id "
            "WHERE pw.name = ? AND dp.date = ?", (name, day)
        ).fetchall()
        candidates = same_day or conn.execute(
            "SELECT pw.id FROM proposed_workouts pw JOIN daily_plans dp ON pw.dailyPlanId = dp.id "
            "WHERE pw.name = ? AND ABS(JULIANDAY(dp.date) - JULIANDAY(?)) <= 7", (name, day)
        ).fetchall()
        if len(candidates) == 1:
            conn.execute("UPDATE workouts SET proposed_workout_id = ? WHERE id = ?", (candidates[0][0], workout_id))


def _m3_prescribed_ftp(conn):
    """FTP in force when a workout was prescribed, so %FTP targets stay reconstructable."""
    _add_column(conn, "proposed_workouts", "prescribed_ftp", "INTEGER")
    conn.execute(
        "UPDATE proposed_workouts SET prescribed_ftp = ("
        "  SELECT wp.ftp FROM daily_plans dp JOIN weekly_plans wp ON dp.weekNumber = wp.weekNumber"
        "  WHERE dp.id = proposed_workouts.dailyPlanId"
        ") WHERE prescribed_ftp IS NULL"
    )


def _m4_interval_results(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interval_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL REFERENCES workouts(id),
            proposed_workout_id INTEGER REFERENCES proposed_workouts(id),
            interval_index INTEGER NOT NULL,
            name TEXT,
            label TEXT NOT NULL,
            duration_sec INTEGER,
            target_low_w REAL,
            target_high_w REAL,
            actual_avg_w REAL,
            deviation_pct REAL,
            compliance TEXT,
            alignment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(workout_id, interval_index)
        )
    """)


def _m5_execution_score(conn):
    _add_column(conn, "workout_analyses", "execution_score", "REAL")
    _add_column(conn, "workout_analyses", "proposed_workout_id", "INTEGER")


def _m6_training_load_daily(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS training_load_daily (
            date TEXT PRIMARY KEY,
            tss REAL NOT NULL,
            ctl REAL NOT NULL,
            atl REAL NOT NULL,
            tsb REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _m7_workout_progression(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workout_progression (
            workout_id INTEGER PRIMARY KEY REFERENCES workouts(id),
            workout_date TEXT NOT NULL,
            archetype TEXT NOT NULL,
            proposed_workout_id INTEGER,
            work_intervals INTEGER,
            work_seconds INTEGER,
            work_avg_power REAL,
            normalized_power REAL,
            pct_ftp REAL,
            ftp INTEGER,
            execution_score REAL,
            structure TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_progression_archetype ON workout_progression(archetype, workout_date)")


def _m8_goals(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT,
            priority INTEGER DEFAULT 3,
            status TEXT NOT NULL DEFAULT 'active',
            target_date TEXT,
            added_date TEXT,
            progress_notes TEXT NOT NULL DEFAULT '[]',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _m9_coaching_continuity(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coaching_continuity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start_date TEXT NOT NULL UNIQUE,
            key_observations TEXT NOT NULL DEFAULT '[]',
            progression_notes TEXT NOT NULL DEFAULT '[]',
            areas_to_monitor TEXT NOT NULL DEFAULT '[]',
            next_week_priorities TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _m10_plan_rationale(conn):
    _add_column(conn, "weekly_plans", "rationale", "TEXT")


def _m11_app_events(conn):
    """Durable record of background failures; stdout on a headless box goes unread."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            acknowledged INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _m12_ride_power_bests(conn):
    """Best average power per ride at standard durations (the basis of the power curve)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ride_power_bests (
            fit_file_id INTEGER PRIMARY KEY REFERENCES fit_files(id),
            ride_date TEXT NOT NULL,
            p5s REAL, p1m REAL, p5m REAL, p20m REAL, p60m REAL,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ride_power_bests_date ON ride_power_bests(ride_date)")


MIGRATIONS: List[Tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "matching columns on workouts", _m1_matching_columns),
    (2, "workouts.proposed_workout_id foreign key + backfill", _m2_proposed_workout_fk),
    (3, "proposed_workouts.prescribed_ftp", _m3_prescribed_ftp),
    (4, "interval_results table", _m4_interval_results),
    (5, "workout_analyses execution score + plan link", _m5_execution_score),
    (6, "training_load_daily table", _m6_training_load_daily),
    (7, "workout_progression table", _m7_workout_progression),
    (8, "goals table", _m8_goals),
    (9, "coaching_continuity table", _m9_coaching_continuity),
    (10, "weekly_plans.rationale", _m10_plan_rationale),
    (11, "app_events table", _m11_app_events),
    (12, "ride_power_bests table", _m12_ride_power_bests),
]


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        " version INTEGER PRIMARY KEY, description TEXT NOT NULL,"
        " applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def apply_migrations(db_path: str) -> int:
    """Apply pending migrations. Cheap after the first call per process."""
    if db_path in _applied_paths:
        return 0
    with _lock:
        if db_path in _applied_paths:
            return 0
        # Autocommit mode so the explicit BEGIN/COMMIT below are the only transactions.
        conn = sqlite3.connect(db_path, isolation_level=None)
        try:
            version = current_version(conn)
            applied = 0
            for number, description, fn in MIGRATIONS:
                if number <= version:
                    continue
                try:
                    conn.execute("BEGIN")
                    fn(conn)
                    conn.execute(
                        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                        (number, description),
                    )
                    conn.execute("COMMIT")
                    applied += 1
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
            _applied_paths.add(db_path)
            return applied
        finally:
            conn.close()
