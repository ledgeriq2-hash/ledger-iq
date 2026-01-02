import { useQuery } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

const fetchCustomerPortalData = async (token) => {
  const [summary, invoices, payments, balance, statement] = await Promise.all([
    api.portal.summary(token),
    api.portal.invoices(token),
    api.portal.payments(token),
    api.portal.balance(token),
    api.portal.statement(token),
  ]);
  return {
    ...summary,
    invoices: invoices?.invoices || [],
    payments: payments?.payments || [],
    balance,
    statement,
  };
};

export const useCustomerPortalData = (token) =>
  useQuery({
    queryKey: ["portal", "customer", token],
    queryFn: () => fetchCustomerPortalData(token),
    enabled: Boolean(token),
    retry: 2,
  });
