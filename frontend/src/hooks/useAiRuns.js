import { useQuery } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

export const useAiRuns = () => {
  return useQuery({
    queryKey: ["ai", "runs"],
    queryFn: async () => api.ai.listRuns(),
    staleTime: 15_000,
  });
};
