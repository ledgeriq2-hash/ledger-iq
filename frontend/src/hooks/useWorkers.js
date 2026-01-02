import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

const normalizeWorkers = (data) => {
  const items = Array.isArray(data?.items) ? data.items : [];
  const sorted = [...items].sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  return { ...data, items: sorted };
};

const invalidateWorkers = (client) => client.invalidateQueries({ queryKey: ["workers"] });

export const useWorkers = ({ page = 1, pageSize = 200 } = {}) => {
  return useQuery({
    queryKey: ["workers", page, pageSize],
    queryFn: async () => {
      const data = await api.employees.listEmployees({ page, page_size: pageSize });
      return normalizeWorkers(data);
    },
  });
};

export const useCreateWorker = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => api.employees.createEmployee(payload),
    onSuccess: () => invalidateWorkers(queryClient),
  });
};

export const useUpdateWorker = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workerId, payload }) => api.employees.updateEmployee(workerId, payload),
    onSuccess: () => invalidateWorkers(queryClient),
  });
};

export const useDeleteWorker = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (workerId) => api.employees.deleteEmployee(workerId),
    onSuccess: () => invalidateWorkers(queryClient),
  });
};
