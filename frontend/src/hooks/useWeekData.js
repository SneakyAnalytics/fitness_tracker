import { useQuery } from "@tanstack/react-query";
import { addDays, format } from "date-fns";
import { proposedWorkoutAPI, weatherAPI, workoutAPI } from "../api/client";

export function useWeek(weekStart) {
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

// Forecast for the visible week (the API returns nothing for weeks outside its window, so no chips appear).
export function useWeather(weekStart) {
  const startStr = format(weekStart, "yyyy-MM-dd");
  const endStr = format(addDays(weekStart, 6), "yyyy-MM-dd");
  return useQuery({
    queryKey: ["weather", startStr],
    queryFn: async () => (await weatherAPI.get(startStr, endStr)).data?.days || {},
    staleTime: 15 * 60 * 1000,
    retry: false,
  });
}

