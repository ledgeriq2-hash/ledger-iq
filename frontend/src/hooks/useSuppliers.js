import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

const asNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const normalizeSuppliers = (data) => {
  const items = Array.isArray(data?.items) ? data.items : [];
  const sorted = [...items].sort((a, b) => asNumber(b.balance) - asNumber(a.balance));
  return { ...data, items: sorted };
};

const invalidateSuppliers = (client) => client.invalidateQueries({ queryKey: ["suppliers"] });

export const useSuppliers = ({ page = 1, pageSize = 200 } = {}) => {
  return useQuery({
    queryKey: ["suppliers", page, pageSize],
    queryFn: async () => {
      const data = await api.suppliers.listSuppliers({ page, page_size: pageSize });
      return normalizeSuppliers(data);
    },
  });
};

export const useCreateSupplier = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => api.suppliers.createSupplier(payload),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
};

export const useUpdateSupplier = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ supplierId, payload }) => api.suppliers.updateSupplier(supplierId, payload),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
};

export const useDeleteSupplier = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (supplierId) => api.suppliers.deleteSupplier(supplierId),
    onSuccess: () => invalidateSuppliers(queryClient),
  });
};
