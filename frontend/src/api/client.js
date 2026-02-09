import axios from "axios";

// API base URL - defaults to proxied path in dev, can be overridden with env var
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  },
);

// API methods matching FastAPI backend endpoints

export const workoutAPI = {
  // Get all workouts
  getAll: () => apiClient.get("/workouts"),

  // Get workouts with analyses
  getWithAnalyses: () => apiClient.get("/workouts/with-analyses"),

  // Get workouts for a specific week
  getWeek: (startDate, endDate) =>
    apiClient.get("/workouts/week", {
      params: { start_date: startDate, end_date: endDate },
    }),

  // Get performance data for a workout
  getPerformance: (workoutId) =>
    apiClient.get("/workout/performance", {
      params: { workout_id: workoutId },
    }),

  // Save qualitative feedback
  saveQualitative: (data) => apiClient.post("/workouts/qualitative", data),

  // Save performance metrics
  savePerformance: (data) => apiClient.post("/workout/performance", data),
};

export const proposedWorkoutAPI = {
  // Get proposed workouts for a week
  getWeek: (startDate, endDate) =>
    apiClient.get("/proposed_workouts/week", {
      params: { start_date: startDate, end_date: endDate },
    }),

  // Upload proposed workouts
  upload: (data) => apiClient.post("/upload/proposed_workouts", data),
};

export const uploadAPI = {
  // Upload workouts CSV from TrainingPeaks
  uploadWorkouts: (formData) =>
    apiClient.post("/upload/workouts", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // Upload metrics CSV
  uploadMetrics: (formData) =>
    apiClient.post("/upload/metrics", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // Upload FIT file
  uploadFit: (formData) =>
    apiClient.post("/upload/fit", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
};

export const summaryAPI = {
  // Get all summaries
  getAll: () => apiClient.get("/summaries"),

  // Generate weekly summary
  generate: (startDate, endDate) =>
    apiClient.get("/summary/generate", {
      params: { start_date: startDate, end_date: endDate },
    }),

  // Save weekly summary
  save: (data) => apiClient.post("/summary/save", data),

  // Export summary as JSON
  export: (startDate, endDate) =>
    apiClient.get("/summary/export", {
      params: { start_date: startDate, end_date: endDate },
    }),
};

export const athleteAPI = {
  // Get athlete settings
  getSettings: () => apiClient.get("/athlete/settings"),

  // Save athlete settings
  saveSettings: (data) => apiClient.post("/athlete/settings", data),
};

export const zwiftAPI = {
  // Generate Zwift workout files
  generateWorkouts: (weekStart) =>
    apiClient.get("/zwift/generate_workouts", {
      params: { week_start: weekStart },
    }),
};

export const healthAPI = {
  // Health check
  check: () => apiClient.get("/health"),
};

export default apiClient;
