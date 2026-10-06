import React, { useState, useEffect, useRef } from "react";
import { Play, Pause, RotateCcw, Timer as TimerIcon } from "lucide-react";
import "./Timer.css";

function Timer({ workDuration = 45, restDuration = 15, rounds = 1 }) {
  const [timeLeft, setTimeLeft] = useState(workDuration);
  const [currentRound, setCurrentRound] = useState(1);
  const [isRunning, setIsRunning] = useState(false);
  const [isWorkPhase, setIsWorkPhase] = useState(true);
  const intervalRef = useRef(null);
  const audioRef = useRef(null);

  // Create audio context for beeps
  useEffect(() => {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      audioRef.current = new AudioContext();
    }
  }, []);

  const playBeep = (frequency = 800, duration = 200) => {
    if (!audioRef.current) return;

    const oscillator = audioRef.current.createOscillator();
    const gainNode = audioRef.current.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioRef.current.destination);

    oscillator.frequency.value = frequency;
    oscillator.type = "sine";

    gainNode.gain.setValueAtTime(0.3, audioRef.current.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioRef.current.currentTime + duration / 1000,
    );

    oscillator.start(audioRef.current.currentTime);
    oscillator.stop(audioRef.current.currentTime + duration / 1000);
  };

  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            // Time's up for current phase
            playBeep(1000, 300);

            if (isWorkPhase) {
              // Switch to rest phase
              setIsWorkPhase(false);
              return restDuration;
            } else {
              // Rest phase ended
              if (currentRound < rounds) {
                // Move to next round
                setCurrentRound((r) => r + 1);
                setIsWorkPhase(true);
                return workDuration;
              } else {
                // All rounds complete
                setIsRunning(false);
                playBeep(1200, 500);
                return 0;
              }
            }
          }

          // Warning beep at 3 seconds
          if (prev === 3) {
            playBeep(600, 150);
          }

          return prev - 1;
        });
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [
    isRunning,
    isWorkPhase,
    currentRound,
    rounds,
    workDuration,
    restDuration,
  ]);

  const handleStartPause = () => {
    setIsRunning(!isRunning);
    if (
      !isRunning &&
      audioRef.current &&
      audioRef.current.state === "suspended"
    ) {
      audioRef.current.resume();
    }
  };

  const handleReset = () => {
    setIsRunning(false);
    setCurrentRound(1);
    setIsWorkPhase(true);
    setTimeLeft(workDuration);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const progress = isWorkPhase
    ? ((workDuration - timeLeft) / workDuration) * 100
    : ((restDuration - timeLeft) / restDuration) * 100;

  return (
    <div
      className={`timer-container ${isWorkPhase ? "work-phase" : "rest-phase"}`}
    >
      <div className="timer-header">
        <TimerIcon size={24} />
        <h3>Workout Timer</h3>
      </div>

      <div className="timer-display">
        <div className="timer-phase">{isWorkPhase ? "💪 WORK" : "😌 REST"}</div>
        <div className="timer-time">{formatTime(timeLeft)}</div>
        <div className="timer-round">
          Round {currentRound} of {rounds}
        </div>
      </div>

      <div className="timer-progress">
        <div className="timer-progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <div className="timer-controls">
        <button
          className="btn btn-primary timer-btn"
          onClick={handleStartPause}
        >
          {isRunning ? <Pause size={20} /> : <Play size={20} />}
          <span>{isRunning ? "Pause" : "Start"}</span>
        </button>
        <button className="btn btn-outline timer-btn" onClick={handleReset}>
          <RotateCcw size={20} />
          <span>Reset</span>
        </button>
      </div>

      <div className="timer-config">
        <div className="config-item">
          <span>Work:</span>
          <strong>{workDuration}s</strong>
        </div>
        <div className="config-item">
          <span>Rest:</span>
          <strong>{restDuration}s</strong>
        </div>
        <div className="config-item">
          <span>Rounds:</span>
          <strong>{rounds}</strong>
        </div>
      </div>
    </div>
  );
}

export default Timer;
