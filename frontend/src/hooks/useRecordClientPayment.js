import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

export const useRecordClientPayment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload) => api.payments.createPayment(payload),
    onSuccess: async (_payment, variables) => {
      const customerId = variables?.customer_id;
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["clients"] }),
        queryClient.invalidateQueries({ queryKey: ["client", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["clientStatement", customerId] }),
        queryClient.invalidateQueries({ queryKey: ["treasuryReport"] }),
      ]);
    },
  });
};
