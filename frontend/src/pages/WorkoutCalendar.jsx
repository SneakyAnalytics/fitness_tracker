import React, { useState, useEffect } from "react";
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
} from "lucide-react";
import {
  format,
  startOfWeek,
  addDays,
  addWeeks,
  subWeeks,
  isSameDay,
  parseISO,
} from "date-fns";
import { workoutAPI, proposedWorkoutAPI } from "../api/client";
import WorkoutCard from "../components/WorkoutCard";
import Timer from "../components/Timer";
import IntervalVisualizer from "../components/IntervalVisualizer";
import ExerciseDetail from "../components/ExerciseDetail";
import "./WorkoutCalendar.css";

console.log("WorkoutCalendar component loaded");

function WorkoutCalendar() {
  console.log("WorkoutCalendar rendering");
  const [currentWeekStart, setCurrentWeekStart] = useState(
    startOfWeek(new Date(), { weekStartsOn: 1 }), // Monday
  );
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [proposedWorkouts, setProposedWorkouts] = useState([]);
  const [completedWorkouts, setCompletedWorkouts] = useState([]);
  const [selectedWorkout, setSelectedWorkout] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showTimer, setShowTimer] = useState(false);

  // Load workouts for the current week
  useEffect(() => {
    loadWeekData();
  }, [currentWeekStart]);

  const loadWeekData = async () => {
    setLoading(true);
    try {
      const weekEnd = addDays(currentWeekStart, 6);
      const startStr = format(currentWeekStart, "yyyy-MM-dd");
      const endStr = format(weekEnd, "yyyy-MM-dd");

      // Load both proposed and completed workouts
      const [proposedRes, completedRes] = await Promise.all([
        proposedWorkoutAPI.getWeek(startStr, endStr).catch((err) => {
          console.error("Error loading proposed workouts:", err);
          return { data: { daily_workouts: [] } };
        }),
        workoutAPI.getWeek(startStr, endStr).catch((err) => {
          console.error("Error loading completed workouts:", err);
          return { data: { completed_workouts: [] } };
        }),
      ]);

      // Extract the workout arrays from the API response structure
      const proposedData = Array.isArray(proposedRes?.data?.daily_workouts)
        ? proposedRes.data.daily_workouts
        : [];
      const completedData = Array.isArray(
        completedRes?.data?.completed_workouts,
      )
        ? completedRes.data.completed_workouts
        : [];

      console.log("Loaded proposed workouts:", proposedData.length, "workouts");
      console.log(
        "Loaded completed workouts:",
        completedData.length,
        "workouts",
      );
      console.log("Sample proposed:", proposedData[0]);
      console.log("Sample completed:", completedData[0]);

      setProposedWorkouts(proposedData);
      setCompletedWorkouts(completedData);
    } catch (error) {
      console.error("Failed to load week data:", error);
      setProposedWorkouts([]);
      setCompletedWorkouts([]);
    } finally {
      setLoading(false);
    }
  };

  const navigateWeek = (direction) => {
    setCurrentWeekStart((prev) =>
      direction === "next" ? addWeeks(prev, 1) : subWeeks(prev, 1),
    );
  };

  const goToToday = () => {
    setCurrentWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }));
    setSelectedDate(new Date());
  };

  const getWorkoutsForDate = (date) => {
    const dateStr = format(date, "yyyy-MM-dd");

    // Defensive checks to ensure we have arrays
    const proposedArray = Array.isArray(proposedWorkouts)
      ? proposedWorkouts
      : [];
    const completedArray = Array.isArray(completedWorkouts)
      ? completedWorkouts
      : [];

    const proposed = proposedArray.filter((w) => {
      const workoutDate = w.date || w.scheduled_date || w.workout_date;
      return workoutDate && workoutDate.startsWith(dateStr);
    });

    const completed = completedArray.filter((w) => {
      const workoutDate = w.date || w.workout_date;
      return workoutDate && workoutDate.startsWith(dateStr);
    });

    // Merge and mark completion status
    const allWorkouts = [
      ...completed.map((w) => ({ ...w, completed: true })),
      ...proposed
        .filter((p) => !completed.some((c) => c.proposed_workout_id === p.id))
        .map((w) => ({ ...w, completed: false })),
    ];

    return allWorkouts;
  };

  const handleDateClick = (date) => {
    setSelectedDate(date);
    const workouts = getWorkoutsForDate(date);
    if (workouts.length > 0) {
      setSelectedWorkout(workouts[0]);
    } else {
      setSelectedWorkout(null);
    }
  };

  const handleWorkoutClick = (workout) => {
    setSelectedWorkout(workout);
    setShowTimer(false); // Reset timer when switching workouts
  };

  const handleExerciseSave = async (exerciseId, data) => {
    console.log("Saving exercise data:", exerciseId, data);
    // TODO: Implement save to backend via workoutAPI.saveQualitative
    alert("Exercise progress saved! (API integration pending)");
  };

  const weekDays = Array.from({ length: 7 }, (_, i) =>
    addDays(currentWeekStart, i),
  );

  // Helper to get workout icon
  const getWorkoutIcon = (type) => {
    const typeLC = type?.toLowerCase() || "";
    if (typeLC.includes("bike") || typeLC.includes("cycling"))
      return { Icon: Bike, color: "var(--color-cycling)" };
    if (typeLC.includes("run"))
      return { Icon: Footprints, color: "var(--color-running)" };
    if (typeLC.includes("strength") || typeLC.includes("routine"))
      return { Icon: Dumbbell, color: "var(--color-strength)" };
    if (typeLC.includes("yoga") || typeLC.includes("mobility"))
      return { Icon: Activity, color: "var(--color-strength)" };
    if (typeLC.includes("ski"))
      return { Icon: TreePine, color: "var(--color-other)" };
    return { Icon: Clock, color: "var(--color-other)" };
  };

  // Check if workout is a routine type (strength/yoga/mobility)
  const isRoutineWorkout = (type) => {
    const typeLC = type?.toLowerCase() || "";
    return (
      typeLC.includes("strength") ||
      typeLC.includes("routine") ||
      typeLC.includes("yoga") ||
      typeLC.includes("mobility")
    );
  };

  return (
    <div className="workout-calendar-container">
      {/* Calendar Header */}
      <div className="calendar-header">
        <div className="header-title">
          <CalendarIcon size={32} />
          <div>
            <h1>Workout Calendar</h1>
            <p className="header-subtitle">
              Week of {format(currentWeekStart, "MMM d")} -{" "}
              {format(addDays(currentWeekStart, 6), "MMM d, yyyy")}
            </p>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn-outline" onClick={goToToday}>
            Today
          </button>
          <div className="week-nav">
            <button
              className="btn btn-outline icon-btn"
              onClick={() => navigateWeek("prev")}
            >
              <ChevronLeft size={20} />
            </button>
            <button
              className="btn btn-outline icon-btn"
              onClick={() => navigateWeek("next")}
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Compact Weekly Calendar Grid */}
      <div className="calendar-grid-compact">
        {loading ? (
          <div className="spinner">Loading workouts...</div>
        ) : (
          weekDays.map((date) => {
            const dayWorkouts = getWorkoutsForDate(date);
            const isToday = isSameDay(date, new Date());

            return (
              <div
                key={date.toString()}
                className={`calendar-day-compact ${isToday ? "today" : ""}`}
              >
                <div className="day-header-compact">
                  <span className="day-name">{format(date, "EEE")}</span>
                  <span className="day-number">{format(date, "d")}</span>
                </div>
                <div className="day-workouts-compact">
                  {dayWorkouts.length === 0 ? (
                    <div className="no-workout-indicator">Rest Day</div>
                  ) : (
                    dayWorkouts.map((workout, idx) => {
                      const { Icon, color } = getWorkoutIcon(workout.type);
                      const isExpanded =
                        selectedWorkout?.id === workout.id ||
                        (selectedWorkout?.name === workout.name &&
                          selectedWorkout?.date === workout.date);

                      return (
                        <div
                          key={idx}
                          className={`workout-mini-card ${isExpanded ? "expanded" : ""} ${workout.completed ? "completed" : ""}`}
                          onClick={() => handleWorkoutClick(workout)}
                        >
                          <div className="workout-mini-icon" style={{ color }}>
                            <Icon size={16} />
                          </div>
                          <div className="workout-mini-info">
                            <div className="workout-mini-title">
                              {workout.name || workout.title}
                            </div>
                            <div className="workout-mini-stats">
                              <span>
                                {workout.plannedDuration ||
                                  workout.duration ||
                                  0}
                                min
                              </span>
                              {(workout.plannedTSS_min || workout.tss) && (
                                <span>
                                  • {workout.plannedTSS_min || workout.tss || 0}{" "}
                                  TSS
                                </span>
                              )}
                            </div>
                          </div>
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

      {/* Expandable Workout Detail View */}
      {selectedWorkout && (
        <div className="workout-detail-expandable">
          <div className="workout-detail-header">
            <div className="workout-detail-title-section">
              <h2>{selectedWorkout.name || selectedWorkout.title}</h2>
              <div className="workout-detail-meta">
                <span>{selectedWorkout.type}</span>
                <span>•</span>
                <span>
                  {selectedWorkout.plannedDuration || selectedWorkout.duration}{" "}
                  minutes
                </span>
                {(selectedWorkout.plannedTSS_min || selectedWorkout.tss) && (
                  <>
                    <span>•</span>
                    <span>
                      {selectedWorkout.plannedTSS_min || selectedWorkout.tss}{" "}
                      TSS
                    </span>
                  </>
                )}
              </div>
            </div>
            <div className="workout-detail-actions">
              {isRoutineWorkout(selectedWorkout.type) && (
                <button
                  className="btn btn-primary"
                  onClick={() => setShowTimer(!showTimer)}
                >
                  <Clock size={18} />
                  {showTimer ? "Hide Workout" : "Start Workout"}
                </button>
              )}
              <button
                className="btn btn-outline icon-btn"
                onClick={() => setSelectedWorkout(null)}
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="workout-detail-content">
            <WorkoutDetailView
              workout={selectedWorkout}
              onExerciseSave={handleExerciseSave}
              showTimer={showTimer}
              onToggleTimer={() => setShowTimer(!showTimer)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Separate component for workout detail view
function WorkoutDetailView({
  workout,
  onExerciseSave,
  showTimer,
  onToggleTimer,
}) {
  // Debug logging
  console.log("WorkoutDetailView - Full workout data:", workout);
  console.log("Workout type:", workout.type);
  console.log("Workout sections:", workout.sections);
  console.log("Workout exercises:", workout.exercises);
  console.log("Workout intervals:", workout.intervals);

  const isRoutineWorkout =
    workout.type?.toLowerCase().includes("strength") ||
    workout.type?.toLowerCase().includes("routine") ||
    workout.type?.toLowerCase().includes("yoga") ||
    workout.type?.toLowerCase().includes("mobility") ||
    workout.exercises?.length > 0;

  const isCardioWorkout =
    workout.type?.toLowerCase().includes("bike") ||
    workout.type?.toLowerCase().includes("run") ||
    workout.type?.toLowerCase().includes("cycling");

  return (
    <div className="workout-detail-content">
      {/* Workout Description - MOVED TO TOP */}
      {workout.notes && (
        <div className="workout-notes-top">
          <h4>Workout Description</h4>
          <p>{workout.notes}</p>
        </div>
      )}

      {/* Workout Header */}
      <div className="workout-header">
        <h3>{workout.name || workout.title}</h3>
        {workout.completed && (
          <span className="status-badge completed">✓ Completed</span>
        )}
        {!workout.completed && (
          <span className="status-badge planned">Planned</span>
        )}
      </div>

      {/* Workout Summary Info */}
      <div className="workout-summary">
        {(workout.plannedDuration || workout.duration) && (
          <div className="summary-item">
            <Clock size={18} />
            <div>
              <span className="label">Duration</span>
              <span className="value">
                {workout.plannedDuration || workout.duration} min
              </span>
            </div>
          </div>
        )}
        {(workout.plannedTSS_min || workout.tss) && (
          <div className="summary-item">
            <Target size={18} />
            <div>
              <span className="label">TSS</span>
              <span className="value">
                {workout.plannedTSS_min || workout.tss}
              </span>
            </div>
          </div>
        )}
        {(workout.targetRPE_min || workout.intensity) && (
          <div className="summary-item">
            <TrendingUp size={18} />
            <div>
              <span className="label">Intensity</span>
              <span className="value">
                {workout.targetRPE_min
                  ? `RPE ${workout.targetRPE_min}-${workout.targetRPE_max}`
                  : workout.intensity}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Timer Toggle for Timed Workouts */}
      {(isRoutineWorkout || workout.has_timer) && (
        <button className="btn btn-secondary" onClick={onToggleTimer}>
          {showTimer ? "Hide Timer" : "Show Timer"}
        </button>
      )}

      {/* Timer Component */}
      {showTimer && (
        <div className="timer-section">
          <Timer
            workDuration={workout.work_duration || 45}
            restDuration={workout.rest_duration || 15}
            rounds={workout.rounds || workout.sets || 3}
          />
        </div>
      )}

      {/* Routine Workout: Exercise List */}
      {isRoutineWorkout &&
        (() => {
          // Parse sections if it's a JSON string
          let sections = [];
          let exercises = [];

          console.log("Parsing routine workout...");

          try {
            if (workout.sections) {
              sections =
                typeof workout.sections === "string"
                  ? JSON.parse(workout.sections)
                  : workout.sections;
              console.log("Parsed sections:", sections);
            }

            if (workout.exercises) {
              exercises =
                typeof workout.exercises === "string"
                  ? JSON.parse(workout.exercises)
                  : workout.exercises;
              console.log("Parsed exercises:", exercises);
            }

            // If we have sections, flatten exercises from them
            if (sections && Array.isArray(sections) && sections.length > 0) {
              sections.forEach((section) => {
                if (section.exercises && Array.isArray(section.exercises)) {
                  exercises = [
                    ...exercises,
                    ...section.exercises.map((ex) => ({
                      ...ex,
                      section: section.name,
                    })),
                  ];
                }
              });
              console.log("Final flattened exercises:", exercises);
            }

            if (exercises && exercises.length > 0) {
              return (
                <div className="exercises-section">
                  <h4>Exercises ({exercises.length})</h4>
                  {exercises.map((exercise, idx) => (
                    <ExerciseDetail
                      key={idx}
                      exercise={{ ...exercise, id: `${workout.id}-${idx}` }}
                      onSave={onExerciseSave}
                    />
                  ))}
                </div>
              );
            } else {
              console.log("No exercises found for routine workout");
              return (
                <div className="no-exercises">
                  No exercise details available
                </div>
              );
            }
          } catch (error) {
            console.error("Error parsing routine workout:", error);
            return (
              <div className="error-message">Error loading workout details</div>
            );
          }
        })()}

      {/* Cardio Workout: Interval Visualization */}
      {isCardioWorkout &&
        workout.intervals &&
        (() => {
          try {
            const intervals =
              typeof workout.intervals === "string"
                ? JSON.parse(workout.intervals)
                : workout.intervals;

            console.log("Parsed intervals:", intervals);

            if (!Array.isArray(intervals) || intervals.length === 0) {
              return null;
            }

            return (
              <>
                <div className="intervals-section">
                  <h4>Power Profile</h4>
                  <IntervalVisualizer intervals={intervals} />
                </div>

                <div className="intervals-table-section">
                  <h4>Interval Breakdown</h4>
                  <table className="intervals-table">
                    <thead>
                      <tr>
                        <th>Interval</th>
                        <th>Duration</th>
                        <th>Power Target</th>
                        <th>Cadence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {intervals.map((interval, idx) => {
                        const duration = interval.duration
                          ? `${Math.floor(interval.duration / 60)}:${String(interval.duration % 60).padStart(2, "0")}`
                          : "N/A";

                        let powerTarget = "N/A";
                        if (interval.powerTarget) {
                          if (interval.powerTarget.type === "range") {
                            powerTarget = `${interval.powerTarget.min}-${interval.powerTarget.max}W`;
                          } else if (
                            interval.powerTarget.start &&
                            interval.powerTarget.end
                          ) {
                            powerTarget = `${Math.round(interval.powerTarget.start.value * (workout.ftp || 302))}W → ${Math.round(interval.powerTarget.end.value * (workout.ftp || 302))}W`;
                          }
                        }

                        let cadence = "N/A";
                        if (interval.cadenceTarget) {
                          cadence = `${interval.cadenceTarget.min}-${interval.cadenceTarget.max} rpm`;
                        }

                        return (
                          <tr key={idx}>
                            <td>
                              <strong>
                                {interval.name || `Interval ${idx + 1}`}
                              </strong>
                            </td>
                            <td>{duration}</td>
                            <td>{powerTarget}</td>
                            <td>{cadence}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            );
          } catch (error) {
            console.error("Error parsing intervals:", error);
            return (
              <div className="error-message">Error loading interval data</div>
            );
          }
        })()}

      {/* Workout Notes/Instructions */}
      {workout.notes && (
        <div className="workout-notes">
          <h4>Notes</h4>
          <p>{workout.notes}</p>
        </div>
      )}
    </div>
  );
}

function formatDuration(seconds) {
  if (!seconds) return "";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (hours > 0) {
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  return `${minutes}m`;
}

export default WorkoutCalendar;
