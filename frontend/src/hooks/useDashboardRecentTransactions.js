import { useQuery } from "@tanstack/react-query";

import dashboardApi from "../api/dashboardApi.js";

export const useDashboardRecentTransactions = ({ page = 1, pageSize = 8 } = {}) =>
  useQuery({
    queryKey: ["dashboard", "recentTransactions", { page, pageSize }],
    queryFn: () => dashboardApi.getRecentTransactions({ page, page_size: pageSize }),
    staleTime: 15_000,
  });
