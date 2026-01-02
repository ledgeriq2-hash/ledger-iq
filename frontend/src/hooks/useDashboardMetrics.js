import { useQuery } from "@tanstack/react-query";

import dashboardApi from "../api/dashboardApi.js";

export const useDashboardMetrics = ({ months = 12, time_basis = "event_date" } = {}) => {
  return useQuery({
    queryKey: ["dashboard", "metrics", { months, time_basis }],
    queryFn: async () => dashboardApi.getMetrics({ months, time_basis }),
  });
};
