import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { format, isValid, parseISO, startOfWeek } from "date-fns";

/** "2026-10-07" -> Monday 2026-10-05 (local midnight); anything unparseable -> null. */
export function parseWeekParam(raw) {
  if (!raw) return null;
  const d = parseISO(raw);
  return isValid(d) ? startOfWeek(d, { weekStartsOn: 1 }) : null;
}

/**
 * The week a page is showing, kept in the URL (?week=2026-10-05) so any week can be bookmarked,
 * shared or opened directly. Without the param the page starts on `defaultWeek`.
 * Same shape as useState: [weekStart, setWeekStart(dateOrUpdater)].
 */
export function useWeekParam(defaultWeek) {
  const [params, setParams] = useSearchParams();
  const raw = params.get("week");
  const fromUrl = useMemo(() => parseWeekParam(raw), [raw]);
  const [local, setLocal] = useState(defaultWeek);
  const weekStart = fromUrl ?? local;

  const setWeekStart = useCallback(
    (next) => {
      const value = typeof next === "function" ? next(weekStart) : next;
      setLocal(value);
      setParams(
        (p) => {
          const q = new URLSearchParams(p);
          q.set("week", format(value, "yyyy-MM-dd"));
          return q;
        },
        { replace: true }
      );
    },
    [weekStart, setParams]
  );

  return [weekStart, setWeekStart];
}
