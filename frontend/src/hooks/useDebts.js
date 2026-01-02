import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

const normalizeStatus = (value) => {
  if (!value) return "all";
  return String(value).toLowerCase();
};

const invalidateDebts = (client) => client.invalidateQueries({ queryKey: ["debts"] });

const invalidateDebtDetail = (client, debtId) => {
  if (debtId) {
    return client.invalidateQueries({ queryKey: ["debt", debtId] });
  }
  return Promise.resolve();
};

export const useDebts = ({ page = 1, pageSize = 50, status = "all" } = {}) => {
  const normalizedStatus = normalizeStatus(status);
  return useQuery({
    queryKey: ["debts", { page, pageSize, status: normalizedStatus }],
    queryFn: async () => {
      const query = { page, page_size: pageSize };
      if (normalizedStatus !== "all") {
        query.status = normalizedStatus;
      }
      return api.debts.listDebts(query);
    },
  });
};

export const useCreateDebt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => api.debts.createDebt(payload),
    onSuccess: async (debt) => {
      await Promise.all([invalidateDebts(queryClient), invalidateDebtDetail(queryClient, debt?.id)]);
    },
  });
};

export const useUpdateDebt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ debtId, payload }) => api.debts.updateDebt(debtId, payload),
    onSuccess: async (debt) => {
      await Promise.all([invalidateDebts(queryClient), invalidateDebtDetail(queryClient, debt?.id)]);
    },
  });
};

export const useDeleteDebt = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (debtId) => api.debts.deleteDebt(debtId),
    onSuccess: async (_, debtId) => {
      await Promise.all([invalidateDebts(queryClient), invalidateDebtDetail(queryClient, debtId)]);
    },
  });
};

export const useRecordDebtPayment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ debtId, payload }) => api.debts.recordPayment(debtId, payload),
    onSuccess: async (debt) => {
      await Promise.all([invalidateDebts(queryClient), invalidateDebtDetail(queryClient, debt?.id)]);
    },
  });
};
