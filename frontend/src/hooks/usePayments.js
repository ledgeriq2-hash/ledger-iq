import { useQuery } from "@tanstack/react-query";

import paymentsApi from "../api/paymentsApi.js";

export const usePayments = ({ page = 1, pageSize = 50 } = {}) =>
  useQuery({
    queryKey: ["payments", { page, pageSize }],
    queryFn: () => paymentsApi.listPayments({ page, page_size: pageSize }),
  });
