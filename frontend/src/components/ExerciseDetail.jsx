import React, { useState } from "react";
import { ExternalLink, Save } from "lucide-react";
import "./ExerciseDetail.css";

function ExerciseDetail({ exercise, onSave }) {
  const [reps, setReps] = useState(exercise.reps_completed || "");
  const [weight, setWeight] = useState(exercise.weight_used || "");
  const [notes, setNotes] = useState(exercise.notes || "");

  const handleSave = () => {
    if (onSave) {
      onSave(exercise.id, { reps, weight, notes });
    }
  };

  const getExerciseImageUrl = (exerciseName) => {
    // This would link to exercise demonstration images/videos
    // For now, return a generic exercise lookup URL
    const searchName = exerciseName.replace(/\s+/g, "+");
    return `https://www.google.com/search?q=${searchName}+exercise+demonstration&tbm=isch`;
  };

  // Format duration display
  const formatDuration = (seconds) => {
    if (!seconds) return null;
    if (seconds >= 60) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
    }
    return `${seconds}s`;
  };

  return (
    <div className="exercise-detail">
      <div className="exercise-header">
        <div className="exercise-info">
          <h4 className="exercise-name">{exercise.name}</h4>
          {exercise.section && (
            <span className="exercise-section">
              Section: {exercise.section}
            </span>
          )}
        </div>
        <a
          href={getExerciseImageUrl(exercise.name)}
          target="_blank"
          rel="noopener noreferrer"
          className="exercise-link"
          title="🔍 Look up exercise demonstration"
        >
          <ExternalLink size={18} />
        </a>
      </div>

      {/* Display Sets Information */}
      {exercise.sets &&
        Array.isArray(exercise.sets) &&
        exercise.sets.length > 0 && (
          <div className="exercise-sets">
            {exercise.sets.map((set, idx) => (
              <div key={idx} className="set-details">
                <strong>Set {exercise.sets.length > 1 ? idx + 1 : ""}:</strong>
                <ul className="set-info-list">
                  {set.sets && <li>Perform: {set.sets} sets</li>}
                  {set.reps && (
                    <li>
                      Reps: {set.reps}
                      {set.perSide ? " (each side)" : ""}
                    </li>
                  )}
                  {set.targetReps && (
                    <li>
                      Target Reps:{" "}
                      {typeof set.targetReps === "object"
                        ? `${set.targetReps.min || set.targetReps.value}-${set.targetReps.max || set.targetReps.value}`
                        : set.targetReps}
                      {set.perSide ? " (each side)" : ""}
                    </li>
                  )}
                  {set.duration && (
                    <li>
                      Duration: {formatDuration(set.duration)}
                      {set.perSide &&
                        ` (${formatDuration(set.duration * 2)} total)`}
                    </li>
                  )}
                  {set.weight && (
                    <li>
                      Weight:{" "}
                      {typeof set.weight === "object"
                        ? `${set.weight.min || set.weight.value}-${set.weight.max || set.weight.value} ${set.weight.unit || "lbs"}`
                        : `${set.weight} lbs`}
                    </li>
                  )}
                  {set.workTime && <li>Work: {set.workTime}s</li>}
                  {set.restTime && <li>Rest: {set.restTime}s</li>}
                  {set.restBetweenSets && (
                    <li>Rest Between Sets: {set.restBetweenSets}s</li>
                  )}
                </ul>
                {set.notes && Array.isArray(set.notes) && (
                  <div className="set-notes">
                    <strong>Notes:</strong>
                    <ul>
                      {set.notes.map((note, noteIdx) => (
                        <li key={noteIdx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {set.cues && Array.isArray(set.cues) && (
                  <div className="set-cues">
                    <strong>Cues:</strong>
                    <ul>
                      {set.cues.map((cue, cueIdx) => (
                        <li key={cueIdx}>{cue}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

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

      <button className="btn btn-primary btn-sm" onClick={handleSave}>
        <Save size={16} />
        Save Progress
      </button>
    </div>
  );
}

export default ExerciseDetail;
