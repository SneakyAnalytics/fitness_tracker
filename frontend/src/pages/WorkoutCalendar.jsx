import React, { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Target,
  TrendingUp,
  X,
  Bike,
  Footprints,
  Dumbbell,
  Activity,
  TreePine,
  CheckCircle2,
} from "lucide-react";
import { format, startOfWeek, addDays, addWeeks, subWeeks, isSameDay } from "date-fns";
import { workoutAPI, proposedWorkoutAPI } from "../api/client";
import { useAthleteSettings } from "../hooks/useAthleteSettings";
import {
  flattenExercises,
  isCardioType,
  isRoutineType,
  mergeDayWorkouts,
  parseJSONField,
  resolvePowerTarget,
} from "../lib/workouts";
import IntervalVisualizer from "../components/IntervalVisualizer";
import ExerciseDetail from "../components/ExerciseDetail";
import AskCoach from "../components/AskCoach";
import "./WorkoutCalendar.css";

function useWeek(weekStart) {
  const startStr = format(weekStart, "yyyy-MM-dd");
  const endStr = format(addDays(weekStart, 6), "yyyy-MM-dd");
  return useQuery({
    queryKey: ["week", startStr],
    queryFn: async () => {
      const [proposedRes, completedRes] = await Promise.all([
        proposedWorkoutAPI.getWeek(startStr, endStr),
        workoutAPI.getWeek(startStr, endStr),
      ]);
      return {
        proposed: proposedRes.data?.daily_workouts || [],
        completed: completedRes.data?.completed_workouts || [],
        plan: proposedRes.data?.weekly_plan || null,
      };
    },
  });
}

function getWorkoutIcon(type) {
  const t = type?.toLowerCase() || "";
  if (t.includes("bike") || t.includes("cycling")) return { Icon: Bike, color: "var(--color-cycling)" };
  if (t.includes("run")) return { Icon: Footprints, color: "var(--color-running)" };
  if (t.includes("strength") || t.includes("routine")) return { Icon: Dumbbell, color: "var(--color-strength)" };
  if (t.includes("yoga") || t.includes("mobility")) return { Icon: Activity, color: "var(--color-strength)" };
  if (t.includes("ski")) return { Icon: TreePine, color: "var(--color-other)" };
  return { Icon: Clock, color: "var(--color-other)" };
}

// Plan name if matched; your own label for unplanned sessions; TrainingPeaks title otherwise.
function displayName(w) {
  if (w.completed && w.plan) return w.plan.name;
  if (w.completed && w.proposed_workout_name) return w.proposed_workout_name;
  return w.name;
}

function cardState(w, date) {
  if (w.completed) return w.plan ? "completed" : "unplanned";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date < today ? "missed" : "planned";
}

function minutes(w) {
  return w.completed ? Math.round(w.actualDuration || 0) : w.plannedDuration || 0;
}

function tssLabel(w) {
  if (w.completed) return w.actualTSS != null ? `${Math.round(w.actualTSS)} TSS` : null;
  if (w.plannedTSS_min) return `${w.plannedTSS_min}${w.plannedTSS_max ? `-${w.plannedTSS_max}` : ""} TSS`;
  return null;
}

function WorkoutCalendar() {
  const [weekStart, setWeekStart] = useState(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [selectedKey, setSelectedKey] = useState(null);
  const { data, isLoading, error } = useWeek(weekStart);
  const { ftp } = useAthleteSettings();

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const byDay = useMemo(() => {
    const out = {};
    weekDays.forEach((d) => {
      const key = format(d, "yyyy-MM-dd");
      out[key] = data ? mergeDayWorkouts(data.proposed, data.completed, key) : [];
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, weekStart]);
  const selected = Object.values(byDay).flat().find((w) => w.key === selectedKey) || null;

  const selectWorkout = (w) => {
    setSelectedKey(w.key === selectedKey ? null : w.key);
  };

  return (
    <div className="workout-calendar-container">
      <div className="calendar-header">
        <div className="header-title">
          <CalendarIcon size={32} />
          <div>
            <h1>Workout Calendar</h1>
            <p className="header-subtitle">
              Week of {format(weekStart, "MMM d")} - {format(addDays(weekStart, 6), "MMM d, yyyy")}
              {data?.plan?.plannedTSS_min ? ` · plan ${data.plan.plannedTSS_min}-${data.plan.plannedTSS_max} TSS` : ""}
            </p>
          </div>
        </div>
        <div className="header-actions">
          <button
            className="btn btn-outline"
            onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))}
          >
            Today
          </button>
          <div className="week-nav">
            <button className="btn btn-outline icon-btn" onClick={() => setWeekStart((w) => subWeeks(w, 1))}>
              <ChevronLeft size={20} />
            </button>
            <button className="btn btn-outline icon-btn" onClick={() => setWeekStart((w) => addWeeks(w, 1))}>
              <ChevronRight size={20} />
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-message">Could not load this week: {error.message}</div>}

      <div className="calendar-grid-compact">
        {isLoading ? (
          <div className="spinner">Loading workouts...</div>
        ) : (
          weekDays.map((date) => {
            const dayWorkouts = byDay[format(date, "yyyy-MM-dd")] || [];
            return (
              <div key={date.toISOString()} className={`calendar-day-compact ${isSameDay(date, new Date()) ? "today" : ""}`}>
                <div className="day-header-compact">
                  <span className="day-name">{format(date, "EEE")}</span>
                  <span className="day-number">{format(date, "d")}</span>
                </div>
                <div className="day-workouts-compact">
                  {dayWorkouts.length === 0 ? (
                    <div className="no-workout-indicator">Rest Day</div>
                  ) : (
                    dayWorkouts.map((w) => {
                      const { Icon, color } = getWorkoutIcon(w.type);
                      const tss = tssLabel(w);
                      const state = cardState(w, date);
                      return (
                        <div
                          key={w.key}
                          className={`workout-mini-card ${state} ${w.key === selectedKey ? "expanded" : ""}`}
                          onClick={() => selectWorkout(w)}
                          title={displayName(w)}
                        >
                          <div className="workout-mini-head">
                            <span className="workout-mini-icon" style={{ color }}>
                              {state === "completed" ? (
                                <CheckCircle2 size={15} color="var(--color-success, #2e7d32)" />
                              ) : (
                                <Icon size={15} />
                              )}
                            </span>
                            <div className="workout-mini-info">
                              <div className="workout-mini-title">{displayName(w)}</div>
                            </div>
                          </div>
                          <div className="workout-mini-stats">
                            <span>{minutes(w)} min</span>
                            {tss && <span>{tss}</span>}
                            {w.execution_score != null && <span>exec {w.execution_score}/10</span>}
                          </div>
                          {state === "unplanned" && <span className="workout-mini-tag">unplanned</span>}
                          {state === "missed" && <span className="workout-mini-tag">not done</span>}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {selected && (
        <div className="workout-detail-expandable">
          <div className="workout-detail-header">
            <div className="workout-detail-title-section">
              <h2>{displayName(selected)}</h2>
              <div className="workout-detail-meta">
                <span>{selected.type}</span>
                <span>•</span>
                <span>{minutes(selected)} minutes</span>
                {tssLabel(selected) && (
                  <>
                    <span>•</span>
                    <span>{tssLabel(selected)}</span>
                  </>
                )}
              </div>
            </div>
            <div className="workout-detail-actions">
              <button className="btn btn-outline icon-btn" onClick={() => setSelectedKey(null)}>
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="workout-detail-content">
            <WorkoutDetailView workout={selected} ftp={ftp} />
          </div>
        </div>
      )}
    </div>
  );
}

function ExerciseList({ workout }) {
  const exercises = flattenExercises(workout);
  const planId = workout.plan?.id ?? (workout.completed ? null : workout.id);
  const date = workout.date;
  const queryClient = useQueryClient();
  const perfKey = ["performance", planId, date];
  const { data: saved } = useQuery({
    queryKey: perfKey,
    enabled: Boolean(planId),
    queryFn: async () => (await workoutAPI.getPerformance(planId, date)).data?.performance_data || {},
  });

  if (exercises.length === 0) return <div className="no-exercises">No exercise details available</div>;

  // The backend stores one record per workout, so always send every exercise's log.
  const save = async (exerciseId, log) => {
    if (!planId) throw new Error("this session isn't linked to a planned workout");
    const current = queryClient.getQueryData(perfKey) || {};
    const next = { ...current, exercises: { ...(current.exercises || {}), [exerciseId]: log } };
    await workoutAPI.savePerformance({ workoutId: planId, workoutDate: date, performanceData: next });
    queryClient.setQueryData(perfKey, next);
  };

  return (
    <div className="exercises-section">
      <h4>Exercises ({exercises.length})</h4>
      {exercises.map((exercise, idx) => {
        const id = `${idx}`;
        return (
          <ExerciseDetail
            key={`${planId}-${idx}-${saved ? "loaded" : "new"}`}
            exercise={{ ...exercise, id }}
            initialLog={saved?.exercises?.[id]}
            onSave={save}
          />
        );
      })}
    </div>
  );
}

const COMPLIANCE_LABEL = { on_target: "✓", close: "~", low: "low", high: "high", missing: "—" };

function IntervalSection({ workout, ftp }) {
  const intervals = parseJSONField(workout.intervals, []);
  const workoutId = workout.completed ? workout.id : null;
  const { data: actuals = [] } = useQuery({
    queryKey: ["intervals", workoutId],
    enabled: Boolean(workoutId),
    queryFn: async () => (await workoutAPI.getIntervals(workoutId)).data.intervals,
  });
  if (!Array.isArray(intervals) || intervals.length === 0) return null;
  const planFtp = workout.prescribed_ftp || workout.plan?.prescribed_ftp || ftp;
  const hasActuals = actuals.length > 0;
  return (
    <>
      <div className="intervals-section">
        <h4>{hasActuals ? "Target vs actual power" : "Power Profile"}</h4>
        <IntervalVisualizer intervals={intervals} ftp={planFtp} actuals={actuals} />
      </div>
      <div className="intervals-table-section">
        <h4>Interval Breakdown</h4>
        <div className="table-scroll">
          <table className="intervals-table">
            <thead>
              <tr>
                <th>Interval</th>
                <th>Duration</th>
                <th>Target</th>
                {hasActuals && <th>Actual</th>}
                {hasActuals && <th>Δ</th>}
                <th>Cadence</th>
              </tr>
            </thead>
            <tbody>
              {intervals.map((interval, idx) => {
                const a = actuals.find((r) => r.interval_index === idx);
                return (
                  <tr key={idx}>
                    <td>
                      <strong>{interval.name || `Interval ${idx + 1}`}</strong>
                    </td>
                    <td>
                      {interval.duration
                        ? `${Math.floor(interval.duration / 60)}:${String(interval.duration % 60).padStart(2, "0")}`
                        : "N/A"}
                    </td>
                    <td>{resolvePowerTarget(interval.powerTarget, planFtp)?.label || "N/A"}</td>
                    {hasActuals && <td>{a?.actual_avg_w != null ? `${Math.round(a.actual_avg_w)}W` : "—"}</td>}
                    {hasActuals && (
                      <td className={`compliance ${a?.compliance || ""}`}>
                        {a?.deviation_pct ? `${a.deviation_pct > 0 ? "+" : ""}${a.deviation_pct}%` : ""}{" "}
                        {COMPLIANCE_LABEL[a?.compliance] || ""}
                      </td>
                    )}
                    <td>
                      {interval.cadenceTarget ? `${interval.cadenceTarget.min}-${interval.cadenceTarget.max} rpm` : "N/A"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function WorkoutDetailView({ workout, ftp }) {
  const routine = isRoutineType(workout.type) || flattenExercises(workout).length > 0;
  const cardio = isCardioType(workout.type);
  const notes = workout.plan?.notes ?? workout.notes;

  return (
    <div className="workout-detail-content">
      {notes && (
        <div className="workout-notes-top">
          <h4>Workout Description</h4>
          <p>{notes}</p>
        </div>
      )}

      <div className="workout-header">
        <h3>{workout.completed && workout.plan ? `Completed as: ${workout.name}` : displayName(workout)}</h3>
        {workout.completed ? (
          <span className="status-badge completed">
            ✓ Completed{workout.execution_score != null ? ` · execution ${workout.execution_score}/10` : ""}
          </span>
        ) : (
          <span className="status-badge planned">Planned</span>
        )}
      </div>

      <div className="workout-summary">
        <div className="summary-item">
          <Clock size={18} />
          <div>
            <span className="label">{workout.completed ? "Duration" : "Planned"}</span>
            <span className="value">{minutes(workout)} min</span>
          </div>
        </div>
        {tssLabel(workout) && (
          <div className="summary-item">
            <Target size={18} />
            <div>
              <span className="label">TSS</span>
              <span className="value">{tssLabel(workout)}</span>
            </div>
          </div>
        )}
        {workout.targetRPE_min && (
          <div className="summary-item">
            <TrendingUp size={18} />
            <div>
              <span className="label">Intensity</span>
              <span className="value">
                RPE {workout.targetRPE_min}-{workout.targetRPE_max}
              </span>
            </div>
          </div>
        )}
      </div>

      {routine && <ExerciseList workout={workout} />}
      {cardio && <IntervalSection workout={workout} ftp={ftp} />}

      <AskCoach date={workout.date} key={workout.key} />
    </div>
  );
}

export default WorkoutCalendar;
