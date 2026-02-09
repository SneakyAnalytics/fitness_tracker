import React, { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight,
  Clock,
  Target,
  TrendingUp
} from 'lucide-react';
import { format, startOfWeek, addDays, addWeeks, subWeeks, isSameDay, parseISO } from 'date-fns';
import { workoutAPI, proposedWorkoutAPI } from '../api/client';
import WorkoutCard from '../components/WorkoutCard';
import Timer from '../components/Timer';
import IntervalVisualizer from '../components/IntervalVisualizer';
import ExerciseDetail from '../components/ExerciseDetail';
import './WorkoutCalendar.css';

function WorkoutCalendar() {
  const [currentWeekStart, setCurrentWeekStart] = useState(
    startOfWeek(new Date(), { weekStartsOn: 1 }) // Monday
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
      const startStr = format(currentWeekStart, 'yyyy-MM-dd');
      const endStr = format(weekEnd, 'yyyy-MM-dd');

      // Load both proposed and completed workouts
      const [proposedRes, completedRes] = await Promise.all([
        proposedWorkoutAPI.getWeek(startStr, endStr).catch(() => ({ data: [] })),
        workoutAPI.getWeek(startStr, endStr).catch(() => ({ data: [] })),
      ]);

      setProposedWorkouts(proposedRes.data || []);
      setCompletedWorkouts(completedRes.data || []);
    } catch (error) {
      console.error('Failed to load week data:', error);
    } finally {
      setLoading(false);
    }
  };

  const navigateWeek = (direction) => {
    setCurrentWeekStart(prev => 
      direction === 'next' ? addWeeks(prev, 1) : subWeeks(prev, 1)
    );
  };

  const goToToday = () => {
    setCurrentWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }));
    setSelectedDate(new Date());
  };

  const getWorkoutsForDate = (date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    
    const proposed = proposedWorkouts.filter(w => {
      const workoutDate = w.date || w.scheduled_date || w.workout_date;
      return workoutDate && workoutDate.startsWith(dateStr);
    });

    const completed = completedWorkouts.filter(w => {
      const workoutDate = w.date || w.workout_date;
      return workoutDate && workoutDate.startsWith(dateStr);
    });

    // Merge and mark completion status
    const allWorkouts = [
      ...completed.map(w => ({ ...w, completed: true })),
      ...proposed.filter(p => !completed.some(c => c.proposed_workout_id === p.id))
        .map(w => ({ ...w, completed: false }))
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
  };

  const handleExerciseSave = async (exerciseId, data) => {
    console.log('Saving exercise data:', exerciseId, data);
    // TODO: Implement save to backend via workoutAPI.saveQualitative
    alert('Exercise progress saved! (API integration pending)');
  };

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));
  const selectedDayWorkouts = getWorkoutsForDate(selectedDate);

  return (
    <div className="workout-calendar-container">
      {/* Calendar Header */}
      <div className="calendar-header">
        <div className="header-title">
          <CalendarIcon size={32} />
          <div>
            <h1>Workout Calendar</h1>
            <p className="header-subtitle">
              Week of {format(currentWeekStart, 'MMM d')} - {format(addDays(currentWeekStart, 6), 'MMM d, yyyy')}
            </p>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn btn-outline" onClick={goToToday}>
            Today
          </button>
          <div className="week-nav">
            <button className="btn btn-outline icon-btn" onClick={() => navigateWeek('prev')}>
              <ChevronLeft size={20} />
            </button>
            <button className="btn btn-outline icon-btn" onClick={() => navigateWeek('next')}>
              <ChevronRight size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Calendar Layout */}
      <div className="calendar-layout">
        {/* Weekly Calendar Grid */}
        <div className="calendar-grid">
          {loading ? (
            <div className="spinner" />
          ) : (
            weekDays.map((date) => {
              const dayWorkouts = getWorkoutsForDate(date);
              const isToday = isSameDay(date, new Date());
              const isSelected = isSameDay(date, selectedDate);
              const hasWorkouts = dayWorkouts.length > 0;

              return (
                <div
                  key={date.toString()}
                  className={`calendar-day ${isToday ? 'today' : ''} ${isSelected ? 'selected' : ''} ${hasWorkouts ? 'has-workouts' : ''}`}
                  onClick={() => handleDateClick(date)}
                >
                  <div className="day-header">
                    <span className="day-name">{format(date, 'EEE')}</span>
                    <span className="day-number">{format(date, 'd')}</span>
                  </div>
                  <div className="day-workouts">
                    {dayWorkouts.map((workout, idx) => (
                      <div 
                        key={idx}
                        className={`day-workout-indicator ${workout.completed ? 'completed' : 'planned'}`}
                        title={workout.name || workout.title}
                      >
                        <span className="workout-name">{workout.name || workout.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Workout Detail Panel */}
        <div className="detail-panel">
          {selectedDayWorkouts.length === 0 ? (
            <div className="empty-state">
              <CalendarIcon size={48} />
              <h3>No workouts scheduled</h3>
              <p>{format(selectedDate, 'EEEE, MMMM d, yyyy')}</p>
            </div>
          ) : (
            <>
              <div className="detail-header">
                <h2>{format(selectedDate, 'EEEE, MMMM d')}</h2>
                <span className="workout-count">
                  {selectedDayWorkouts.length} workout{selectedDayWorkouts.length !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Workout Selection */}
              {selectedDayWorkouts.length > 1 && (
                <div className="workout-list">
                  {selectedDayWorkouts.map((workout, idx) => (
                    <WorkoutCard
                      key={idx}
                      workout={workout}
                      isSelected={selectedWorkout?.id === workout.id}
                      onClick={() => handleWorkoutClick(workout)}
                    />
                  ))}
                </div>
              )}

              {/* Selected Workout Detail */}
              {selectedWorkout && (
                <div className="workout-detail">
                  <WorkoutDetailView
                    workout={selectedWorkout}
                    onExerciseSave={handleExerciseSave}
                    showTimer={showTimer}
                    onToggleTimer={() => setShowTimer(!showTimer)}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Separate component for workout detail view
function WorkoutDetailView({ workout, onExerciseSave, showTimer, onToggleTimer }) {
  const isRoutineWorkout = workout.type?.toLowerCase().includes('strength') || 
                          workout.type?.toLowerCase().includes('routine') ||
                          workout.exercises?.length > 0;

  const isCardioWorkout = workout.type?.toLowerCase().includes('bike') ||
                         workout.type?.toLowerCase().includes('run') ||
                         workout.type?.toLowerCase().includes('cycling');

  return (
    <div className="workout-detail-content">
      {/* Workout Header */}
      <div className="workout-header">
        <h3>{workout.name || workout.title}</h3>
        {workout.completed && <span className="status-badge completed">✓ Completed</span>}
        {!workout.completed && <span className="status-badge planned">Planned</span>}
      </div>

      {/* Workout Summary Info */}
      <div className="workout-summary">
        {workout.duration && (
          <div className="summary-item">
            <Clock size={18} />
            <div>
              <span className="label">Duration</span>
              <span className="value">{formatDuration(workout.duration)}</span>
            </div>
          </div>
        )}
        {workout.tss && (
          <div className="summary-item">
            <Target size={18} />
            <div>
              <span className="label">TSS</span>
              <span className="value">{workout.tss}</span>
            </div>
          </div>
        )}
        {workout.intensity && (
          <div className="summary-item">
            <TrendingUp size={18} />
            <div>
              <span className="label">Intensity</span>
              <span className="value">{workout.intensity}</span>
            </div>
          </div>
        )}
      </div>

      {/* Workout Description */}
      {workout.description && (
        <div className="workout-description-section">
          <h4>Description</h4>
          <p>{workout.description}</p>
        </div>
      )}

      {/* Timer Toggle for Timed Workouts */}
      {(isRoutineWorkout || workout.has_timer) && (
        <button className="btn btn-secondary" onClick={onToggleTimer}>
          {showTimer ? 'Hide Timer' : 'Show Timer'}
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
      {isRoutineWorkout && workout.exercises && workout.exercises.length > 0 && (
        <div className="exercises-section">
          <h4>Exercises</h4>
          {workout.exercises.map((exercise, idx) => (
            <ExerciseDetail
              key={idx}
              exercise={{ ...exercise, id: `${workout.id}-${idx}` }}
              onSave={onExerciseSave}
            />
          ))}
        </div>
      )}

      {/* Cardio Workout: Interval Visualization */}
      {isCardioWorkout && workout.intervals && workout.intervals.length > 0 && (
        <div className="intervals-section">
          <IntervalVisualizer intervals={workout.intervals} />
        </div>
      )}

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
  if (!seconds) return '';
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
