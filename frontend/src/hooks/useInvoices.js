import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/generated/index.js";

const normalizeStatus = (value) => {
  if (!value) return "all";
  return String(value).toLowerCase();
};

const matchesStatus = (filter, status) => {
  if (filter === "all") return true;
  return String(status || "").toLowerCase() === filter;
};

const invalidateInvoices = (client) =>
  client.invalidateQueries({ queryKey: ["invoices"] });

const invalidateInvoiceDetail = (client, invoiceId) => {
  if (invoiceId) {
    return client.invalidateQueries({ queryKey: ["invoice", invoiceId] });
  }
  return Promise.resolve();
};

export const useInvoices = ({ page = 1, pageSize = 50, status = "all" } = {}) => {
  const normalizedStatus = normalizeStatus(status);
  return useQuery({
    queryKey: ["invoices", { page, pageSize, status: normalizedStatus }],
    queryFn: async () => {
      const data = await api.invoices.listInvoices({ page, page_size: pageSize });
      const items = Array.isArray(data?.items) ? data.items : [];
      const filtered = items.filter((invoice) => matchesStatus(normalizedStatus, invoice.status));
      return { ...data, items: filtered };
    },
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => api.invoices.createInvoice(payload),
    onSuccess: async (invoice) => {
      await Promise.all([
        invalidateInvoices(queryClient),
        invalidateInvoiceDetail(queryClient, invoice?.id),
      ]);
    },
  });
};

export const useUpdateInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ invoiceId, payload }) => api.invoices.updateInvoice(invoiceId, payload),
    onSuccess: async (invoice) => {
      await Promise.all([
        invalidateInvoices(queryClient),
        invalidateInvoiceDetail(queryClient, invoice?.id),
      ]);
    },
  });
};

export const useDeleteInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invoiceId) => api.invoices.deleteInvoice(invoiceId),
    onSuccess: async (_, invoiceId) => {
      await Promise.all([invalidateInvoices(queryClient), invalidateInvoiceDetail(queryClient, invoiceId)]);
    },
  });
};

export const usePostInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (invoiceId) => api.invoices.postInvoice(invoiceId),
    onSuccess: async (invoice) => {
      await Promise.all([
        invalidateInvoices(queryClient),
        invalidateInvoiceDetail(queryClient, invoice?.id),
      ]);
    },
  });
};

export const useRecordInvoicePayment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ invoiceId, payload }) => api.invoices.recordPartialPayment(invoiceId, payload),
    onSuccess: async (invoice) => {
      await Promise.all([
        invalidateInvoices(queryClient),
        invalidateInvoiceDetail(queryClient, invoice?.id),
      ]);
    },
  });
};
