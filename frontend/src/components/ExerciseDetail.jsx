import React, { useState } from 'react';
import { ExternalLink, Save } from 'lucide-react';
import './ExerciseDetail.css';

function ExerciseDetail({ exercise, onSave }) {
  const [reps, setReps] = useState(exercise.reps_completed || '');
  const [weight, setWeight] = useState(exercise.weight_used || '');
  const [notes, setNotes] = useState(exercise.notes || '');

  const handleSave = () => {
    if (onSave) {
      onSave(exercise.id, { reps, weight, notes });
    }
  };

  const getExerciseImageUrl = (exerciseName) => {
    // This would link to exercise demonstration images/videos
    // For now, return a generic exercise lookup URL
    const searchName = exerciseName.replace(/\s+/g, '+');
    return `https://www.google.com/search?q=${searchName}+exercise+demonstration&tbm=isch`;
  };

  return (
    <div className="exercise-detail">
      <div className="exercise-header">
        <div className="exercise-info">
          <h4 className="exercise-name">{exercise.name}</h4>
          {exercise.target_sets && exercise.target_reps && (
            <span className="exercise-target">
              Target: {exercise.target_sets} × {exercise.target_reps}
              {exercise.target_weight && ` @ ${exercise.target_weight}lbs`}
            </span>
          )}
        </div>
        <a
          href={getExerciseImageUrl(exercise.name)}
          target="_blank"
          rel="noopener noreferrer"
          className="exercise-link"
          title="View exercise demonstration"
        >
          <ExternalLink size={18} />
        </a>
      </div>

      {exercise.description && (
        <p className="exercise-description">{exercise.description}</p>
      )}

      {exercise.cues && Array.isArray(exercise.cues) && (
        <div className="exercise-cues">
          <strong>Form Cues:</strong>
          <ul>
            {exercise.cues.map((cue, index) => (
              <li key={index}>{cue}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="exercise-inputs">
        <div className="input-group">
          <label htmlFor={`reps-${exercise.id}`}>Reps Completed</label>
          <input
            id={`reps-${exercise.id}`}
            type="text"
            className="input"
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            placeholder="e.g., 10, 10, 8"
          />
        </div>

        <div className="input-group">
          <label htmlFor={`weight-${exercise.id}`}>Weight Used (lbs)</label>
          <input
            id={`weight-${exercise.id}`}
            type="text"
            className="input"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder="e.g., 135"
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor={`notes-${exercise.id}`}>Notes</label>
        <textarea
          id={`notes-${exercise.id}`}
          className="input textarea"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="How did this feel? Any adjustments needed?"
          rows={2}
        />
      </div>

      <button 
        className="btn btn-primary btn-sm"
        onClick={handleSave}
      >
        <Save size={16} />
        Save Progress
      </button>
    </div>
  );
}

export default ExerciseDetail;
