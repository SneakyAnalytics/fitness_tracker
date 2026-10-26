import { addDays, differenceInCalendarDays, format, parseISO } from "date-fns";

export const TEST_INTERVAL_WEEKS = 6;   // mirrors FTP_TEST_DUE_WEEKS on the server

/**
 * Where the athlete is in the ramp-test cycle, from the dashboard's zwift_ftp block.
 * state: "fresh" (under 4 weeks), "soon" (4 to 6), "due" (6 or more), "unknown" (no test or FTP change on record).
 */
export function ftpTestStatus(zftp, today = new Date()) {
  const ref = zftp?.last_test_or_race || zftp?.changed_on;
  if (!ref) return { state: "unknown" };
  const refDate = parseISO(ref);
  const days = differenceInCalendarDays(today, refDate);
  const weeks = Math.round((days / 7) * 10) / 10;
  const dueDate = addDays(refDate, TEST_INTERVAL_WEEKS * 7);
  const daysLeft = differenceInCalendarDays(dueDate, today);
  const state = weeks >= TEST_INTERVAL_WEEKS ? "due" : weeks >= 4 ? "soon" : "fresh";
  return {
    state, ref, weeks, days, daysLeft,
    dueLabel: format(dueDate, "MMM d"),
    progress: Math.min(1, Math.max(0, days / (TEST_INTERVAL_WEEKS * 7))),
    kind: zftp?.last_test_or_race ? "test" : "change",
  };
}

/** "6 days" under two weeks, otherwise "5.3 weeks"; never "0.7 weeks". */
export function spanLabel(days) {
  const d = Math.abs(Math.round(days));
  if (d < 14) return `${d} day${d === 1 ? "" : "s"}`;
  return `${Math.round((d / 7) * 10) / 10} weeks`;
}
