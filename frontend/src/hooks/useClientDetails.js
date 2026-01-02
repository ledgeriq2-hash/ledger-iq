import { useQuery } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

export const useClientDetails = (clientId, { fromDate = null, toDate = null } = {}) => {
  const clientQuery = useQuery({
    queryKey: ["client", clientId],
    queryFn: async () => api.customers.getCustomer(clientId),
    enabled: Boolean(clientId),
  });

  const statementQuery = useQuery({
    queryKey: ["clientStatement", clientId, { fromDate, toDate }],
    queryFn: async () =>
      api.reports.clientStatement({
        client_id: clientId,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
      }),
    enabled: Boolean(clientId),
  });

  return { clientQuery, statementQuery };
};
