import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

export const usePortalLinks = (customerId) => {
  const queryClient = useQueryClient();

  const linksQuery = useQuery({
    queryKey: ["portalLinks", customerId],
    queryFn: async () => api.portal.listCustomerLinks(customerId),
    enabled: Boolean(customerId),
  });

  const createLink = useMutation({
    mutationFn: async ({ expiresInHours, expiresInSeconds } = {}) =>
      api.portal.createLink({
        client_id: customerId,
        expires_in_hours: expiresInHours,
        expires_in: expiresInSeconds,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["portalLinks", customerId] });
    },
  });

  const revokeLink = useMutation({
    mutationFn: async (tokenId) => api.portal.revokeLink(tokenId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["portalLinks", customerId] });
    },
  });

  return { linksQuery, createLink, revokeLink };
};
