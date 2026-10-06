import axios from "axios";

// Proxied to FastAPI by Vite in dev and by nginx in production.
export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

export const workoutAPI = {
  getIntervals: (workoutId) => apiClient.get(`/workouts/${workoutId}/intervals`),
  getWeek: (startDate, endDate) =>
    apiClient.get("/workouts/week", { params: { start_date: startDate, end_date: endDate } }),
  getPerformance: (workoutId, workoutDate) =>
    apiClient.get("/workout/performance", { params: { workout_id: workoutId, workout_date: workoutDate } }),
  savePerformance: ({ workoutId, workoutDate, actualDuration = 0, performanceData }) =>
    apiClient.post("/workout/performance", {
      workout_id: workoutId,
      workout_date: workoutDate,
      actual_duration: actualDuration,
      performance_data: performanceData,
    }),
};

export const proposedWorkoutAPI = {
  getWeek: (startDate, endDate) =>
    apiClient.get("/proposed_workouts/week", { params: { start_date: startDate, end_date: endDate } }),
};

export const athleteAPI = {
  getSettings: () => apiClient.get("/athlete/settings"),
  saveSettings: (settings) => apiClient.post("/athlete/settings", { settings }),
};

export const zwiftAPI = {
  generateWorkouts: (startDate, endDate) =>
    apiClient.get("/zwift/generate_workouts", { params: { start_date: startDate, end_date: endDate } }),
};

export const dashboardAPI = {
  getTrends: (weeks = 16) => apiClient.get("/dashboard/trends", { params: { weeks } }),
};

export const coachAPI = {
  getSession: (weekStart, model) => apiClient.get("/coach/session", { params: { week_start: weekStart, model } }),
  savePlan: (weekStart, model) =>
    apiClient.post("/coach/session/save", { week_start: weekStart, model }, { timeout: 120000 }),
};

// Parse a text/event-stream body: each event is `data: {json}\n\n`.
export function parseSSEChunk(buffer) {
  const events = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop();
  for (const part of parts) {
    const line = part.split("\n").find((l) => l.startsWith("data: "));
    if (!line) continue;
    try {
      events.push(JSON.parse(line.slice(6)));
    } catch {
      // ignore malformed event
    }
  }
  return { events, rest };
}

// POST to a streaming endpoint and call onEvent for each SSE event.
export async function streamSSE(path, body, onEvent, { signal } = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      // not JSON
    }
    throw new Error(detail);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSSEChunk(buffer);
    buffer = rest;
    events.forEach(onEvent);
  }
}

export default apiClient;
