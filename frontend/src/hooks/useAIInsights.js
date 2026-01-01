import { useQuery } from "@tanstack/react-query";

import aiApi from "../api/aiApi.js";
import aiInsightsApi from "../api/aiInsightsApi.js";

export const useAiSummary = ({ enabled = true } = {}) =>
  useQuery({
    queryKey: ["ai", "summary"],
    queryFn: () => aiInsightsApi.getSummary(),
    enabled,
    staleTime: 30_000,
  });

export const useAiOverview = ({ enabled = true } = {}) =>
  useQuery({
    queryKey: ["ai", "overview"],
    queryFn: () => aiApi.overview(),
    enabled,
    staleTime: 15_000,
  });

export const useAiInsights = (filters = {}) => {
  const params = {
    from_date: filters.from_date || undefined,
    to_date: filters.to_date || undefined,
    severity: filters.severity || undefined,
    type: filters.type || undefined,
    min_confidence: filters.min_confidence || undefined,
  };

  return useQuery({
    queryKey: ["ai", "insights", params],
    queryFn: () => aiInsightsApi.listInsights(params),
    staleTime: 15_000,
  });
};
