import { useQuery } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

export const useTreasury = (filters = {}) => {
  const normalized = {
    from_date: filters.from_date || undefined,
    to_date: filters.to_date || undefined,
    treasury_id: filters.treasury_id || undefined,
    direction: filters.direction || undefined,
    reference_type: filters.reference_type || undefined,
    reference_id: filters.reference_id || undefined,
  };

  return useQuery({
    queryKey: ["treasuryReport", normalized],
    queryFn: async () => api.reports.treasuryReport(normalized),
  });
};
