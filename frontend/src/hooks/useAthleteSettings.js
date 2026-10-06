import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { athleteAPI } from "../api/client";

export const DEFAULT_FTP = 300;

export function useAthleteSettings() {
  const query = useQuery({
    queryKey: ["athleteSettings"],
    queryFn: async () => (await athleteAPI.getSettings()).data.settings || {},
    staleTime: 5 * 60 * 1000,
  });
  const settings = query.data || {};
  return { ...query, settings, ftp: Number(settings.ftp) || DEFAULT_FTP };
}

export function useSaveAthleteSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (settings) => athleteAPI.saveSettings(settings),
    onSuccess: () => client.invalidateQueries({ queryKey: ["athleteSettings"] }),
  });
}
