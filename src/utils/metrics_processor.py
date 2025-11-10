from typing import Dict, Any, List

import pandas as pd
import io

from datetime import datetime, timedelta

from .fit_parser import FitParser
from ..storage.database import WorkoutDatabase


class MetricsProcessor:
    """Lightweight metrics/workout processor.

    Purpose: provide a small API used by the rest of the app to ingest CSVs
    (sleep/body metrics and workouts) and to attach parsed FIT data to
    workout rows. This implementation is intentionally minimal — it keeps
    data in-memory and preserves the public methods used elsewhere.
    """

    def __init__(self):
        self.fit_parser = FitParser()
        self.db = WorkoutDatabase()

        # keyed by date (YYYY-MM-DD) -> list of metric rows (dicts)
        self.sleep_metrics: Dict[str, List[Dict[str, Any]]] = {}

        # keyed by date -> list of workout rows (dicts)
        self.workouts: Dict[str, List[Dict[str, Any]]] = {}

        # keyed by (date, title) -> fit metadata (fit_file_id, fit_metrics)
        self.fit_data: Dict[tuple, Dict[str, Any]] = {}

    def process_metrics_csv(self, metrics_data: str) -> None:
        """Process sleep and body metrics CSV content.

        The CSV is expected to have at least a Timestamp and Value/Type
        columns. Rows are bucketed by date (YYYY-MM-DD).
        """
        df = pd.read_csv(io.StringIO(metrics_data))
        for _, row in df.iterrows():
            ts = str(row.get('Timestamp', '')).split()[0]
            if not ts:
                continue
            self.sleep_metrics.setdefault(ts, []).append(row.to_dict())

    def process_workouts_csv(self, workouts_data: str) -> None:
        """Process workouts CSV content and store rows by date.

        Expected to contain a Timestamp or Date column and Title/Name.
        """
        df = pd.read_csv(io.StringIO(workouts_data))

        # try a few common date column names
        date_cols = [c for c in df.columns if 'date' in c.lower() or 'timestamp' in c.lower()]
        title_cols = [c for c in df.columns if 'title' in c.lower() or 'name' in c.lower()]

        for _, row in df.iterrows():
            if date_cols:
                ts = str(row[date_cols[0]]).split()[0]
            else:
                ts = datetime.utcnow().date().isoformat()

            title = row[title_cols[0]] if title_cols else row.to_dict().get('Title')
            r = row.to_dict()
            r['title'] = title
            self.workouts.setdefault(ts, []).append(r)

    def add_fit_data(self, fit_file_id: int, fit_metrics: Dict[str, Any], date_str: str, title: str) -> None:
        """Attach parsed FIT metrics to a workout identified by date and title.

        Keyed by (date_str, title) and value contains fit_file_id and fit_metrics.
        """
        key = (date_str, title)
        self.fit_data[key] = {'fit_file_id': fit_file_id, 'fit_metrics': fit_metrics}

    def get_combined_workout_data(self, date_str: str) -> List[Dict[str, Any]]:
        """Return workouts for a given date with any attached FIT data and
        available metrics (sleep/body battery).
        """
        results: List[Dict[str, Any]] = []
        for w in self.workouts.get(date_str, []):
            title = w.get('title') or w.get('Title')
            combined = dict(w)
            key = (date_str, title)
            if key in self.fit_data:
                combined['fit_file_id'] = self.fit_data[key]['fit_file_id']
                combined['fit_metrics'] = self.fit_data[key]['fit_metrics']
            # attach sleep metrics (if any)
            combined['sleep_metrics'] = self.sleep_metrics.get(date_str, [])
            results.append(combined)
        return results

    def calculate_sleep_quality_score(self, metrics: Any) -> float:
        """Simple heuristic to compute a sleep quality score from metric row(s).

        If the row contains a 'Value' field that's numeric, return it. Otherwise
        fall back to 0. This keeps the function deterministic for tests.
        """
        if not metrics:
            return 0.0

        # metrics may be a list of rows; handle both cases
        row = metrics[0] if isinstance(metrics, list) else metrics
        try:
            return float(row.get('Value', 0) or 0)
        except Exception:
            return 0.0

    def get_weekly_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Return a minimal weekly summary over the inclusive date range.

        The summary includes per-day combined workout data and an average
        sleep quality score computed from the available sleep metrics.
        """
        sd = datetime.fromisoformat(start_date).date()
        ed = datetime.fromisoformat(end_date).date()

        cur = sd
        per_day = {}
        sleep_scores = []

        while cur <= ed:
            dstr = cur.isoformat()
            combined = self.get_combined_workout_data(dstr)
            per_day[dstr] = combined
            # compute sleep quality for the day
            rows = self.sleep_metrics.get(dstr, [])
            if rows:
                score = self.calculate_sleep_quality_score(rows)
                sleep_scores.append(score)
            cur += timedelta(days=1)

        avg_sleep = float(sum(sleep_scores) / len(sleep_scores)) if sleep_scores else 0.0
        return {
            'start_date': start_date,
            'end_date': end_date,
            'per_day': per_day,
            'avg_sleep_quality': avg_sleep,
        }