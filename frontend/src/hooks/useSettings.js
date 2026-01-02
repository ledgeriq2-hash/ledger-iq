import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

export const useSettings = () => {
  return useQuery({
    queryKey: ["settings"],
    queryFn: async () => api.settings.getSettings(),
    staleTime: 60_000,
  });
};

export const useUpdateSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload) => api.settings.updateSettings(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
};
