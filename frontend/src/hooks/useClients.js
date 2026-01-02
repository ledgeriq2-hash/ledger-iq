import { useQuery } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

const asNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

export const useClients = ({ page = 1, pageSize = 200 } = {}) => {
  return useQuery({
    queryKey: ["clients", { page, pageSize }],
    queryFn: async () => {
      const data = await api.customers.listCustomers({ page, page_size: pageSize });
      const items = Array.isArray(data?.items) ? data.items : [];
      const sorted = [...items].sort((a, b) => asNumber(b.balance) - asNumber(a.balance));
      return { ...data, items: sorted };
    },
  });
};
