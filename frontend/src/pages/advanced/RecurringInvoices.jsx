import React, { useContext, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Select from "../../components/ui/Select.jsx";
import Button from "../../components/ui/Button.jsx";
import Banner from "../../components/ui/Banner.jsx";
import ErrorBox from "../../components/ui/ErrorBox.jsx";
import Tag from "../../components/ui/Tag.jsx";
import recurringApi from "../../api/recurringApi.js";
import customersApi from "../../api/customersApi.js";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";
import { NotificationContext } from "../../contexts/NotificationContext.jsx";

const initialForm = {
  customer_id: "",
  frequency: "monthly",
  interval: 1,
  day_of_month: "",
  amount: "",
  currency: "USD",
  status: "SENT",
  due_in_days: 7,
  description: "Subscription",
  next_run_at: "",
};

const formatDate = (value) => (value ? new Date(value).toLocaleString() : "—");

const RecurringInvoices = () => {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState(null);
  const { addNotification } = useContext(NotificationContext);
  const queryClient = useQueryClient();

  const { data: recurringData, isLoading } = useQuery({
    queryKey: ["recurring-invoices"],
    queryFn: async () => recurringApi.list({ page_size: 100 }),
  });

  const { data: customersData } = useQuery({
    queryKey: ["customers-list-lite"],
    queryFn: async () => customersApi.listCustomers(),
  });

  const customers = customersData?.items || customersData || [];
  const recurringItems = recurringData?.items || recurringData || [];

  const createMutation = useMutation({
    mutationFn: (payload) => recurringApi.create(payload),
    onSuccess: () => {
      addNotification?.({ title: "Recurring invoice saved", message: "Schedule updated." });
      queryClient.invalidateQueries(["recurring-invoices"]);
      setForm(initialForm);
      setError(null);
    },
    onError: (err) => setError(err?.message || "Failed to save recurring invoice"),
  });

  const runMutation = useMutation({
    mutationFn: (id) => recurringApi.runNow(id),
    onSuccess: (invoice) => {
      addNotification?.({ title: "Invoice generated", message: `Invoice ${invoice?.id || ""} created.` });
      queryClient.invalidateQueries(["recurring-invoices"]);
    },
    onError: (err) => setError(err?.message || "Run now failed"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => recurringApi.remove(id),
    onSuccess: () => {
      addNotification?.({ title: "Recurring invoice deleted" });
      queryClient.invalidateQueries(["recurring-invoices"]);
    },
    onError: (err) => setError(err?.message || "Delete failed"),
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const buildPayload = () => {
    const today = new Date();
    const issueDate = today.toISOString().slice(0, 10);
    const dueInDays = Number(form.due_in_days || 0);
    const dueDate = dueInDays ? new Date(today.getTime() + dueInDays * 86400000).toISOString().slice(0, 10) : issueDate;
    const amount = Number(form.amount || 0).toFixed(2);

    const payload = {
      customer_id: form.customer_id,
      frequency: form.frequency,
      interval: Number(form.interval || 1),
      day_of_month: form.frequency === "monthly" ? Number(form.day_of_month || today.getDate()) : null,
      template: {
        customer_id: form.customer_id,
        issue_date: issueDate,
        due_date: dueDate,
        status: form.status,
        currency: form.currency,
        items: [
          {
            description: form.description || "Recurring charge",
            quantity: "1",
            unit_price: amount,
            tax_rate: "0",
            line_total: amount,
          },
        ],
      },
    };

    if (form.next_run_at) {
      const dt = new Date(form.next_run_at);
      payload.next_run_at = dt.toISOString();
    }
    return payload;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.customer_id || !form.frequency) {
      setError("Customer and frequency are required");
      return;
    }
    setError(null);
    createMutation.mutate(buildPayload());
  };

  const frequencyOptions = useMemo(
    () => [
      { label: "Daily", value: "daily" },
      { label: "Weekly", value: "weekly" },
      { label: "Monthly", value: "monthly" },
      { label: "Custom (every N days)", value: "custom" },
    ],
    []
  );

  return (
    <MainLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md }}>
        <div>
          <h1 style={{ margin: 0, color: colors.text }}>Recurring Invoices</h1>
          <p style={{ margin: 0, color: colors.textMuted }}>Automate invoice generation and keep cashflow predictable.</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: spacing.lg, alignItems: "start" }}>
        <Card title={isLoading ? "Loading schedules..." : "Scheduled runs"}>
          {error && <ErrorBox message={error} />}
          {!isLoading && recurringItems.length === 0 && (
            <Banner message="No recurring invoices yet. Create your first schedule." variant="info" />
          )}
          <div style={{ display: "grid", gap: spacing.md }}>
            {recurringItems.map((item) => (
              <div
                key={item.id}
                style={{
                  border: `1px solid ${colors.border}`,
                  borderRadius: "12px",
                  padding: spacing.md,
                  display: "grid",
                  gap: spacing.sm,
                  background: "#fff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 700, color: colors.text }}>
                      {item.customer?.name || item.customer_id} · {item.template?.currency || "USD"}
                    </div>
                    <div style={{ color: colors.textMuted, fontSize: "0.9rem" }}>
                      Every {item.interval} {item.frequency}
                      {item.frequency === "monthly" && item.day_of_month ? ` on day ${item.day_of_month}` : ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: spacing.sm }}>
                    <Button size="sm" variant="primary" onClick={() => runMutation.mutate(item.id)}>
                      Run now
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => deleteMutation.mutate(item.id)}>
                      Delete
                    </Button>
                  </div>
                </div>
                <div style={{ display: "flex", gap: spacing.md, color: colors.textMuted, fontSize: "0.9rem" }}>
                  <div>
                    Next run: <Tag>{formatDate(item.next_run_at)}</Tag>
                  </div>
                  <div>
                    Last run: <Tag>{formatDate(item.last_run_at)}</Tag>
                  </div>
                  <div>
                    Amount: <strong>{item.template?.items?.[0]?.unit_price || item.template?.total_amount || form.amount}</strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Create recurring invoice">
          {error && <ErrorBox message={error} />}
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: spacing.md }}>
            <Select
              label="Customer"
              name="customer_id"
              value={form.customer_id}
              onChange={handleChange}
              options={[{ label: "Select customer", value: "" }, ...customers.map((c) => ({ label: c.name, value: c.id }))]}
              required
            />
            <Select label="Frequency" name="frequency" value={form.frequency} onChange={handleChange} options={frequencyOptions} required />
            <Input label="Interval" type="number" min="1" name="interval" value={form.interval} onChange={handleChange} required />
            {form.frequency === "monthly" && (
              <Input
                label="Day of month"
                type="number"
                min="1"
                max="31"
                name="day_of_month"
                value={form.day_of_month}
                onChange={handleChange}
              />
            )}
            <Input
              label="Next run at"
              type="datetime-local"
              name="next_run_at"
              value={form.next_run_at}
              onChange={handleChange}
            />
            <Input label="Amount" type="number" min="0" step="0.01" name="amount" value={form.amount} onChange={handleChange} required />
            <Input label="Currency" name="currency" value={form.currency} onChange={handleChange} required />
            <Select
              label="Invoice status"
              name="status"
              value={form.status}
              onChange={handleChange}
              options={[
                { label: "Draft", value: "DRAFT" },
                { label: "Sent", value: "SENT" },
                { label: "Paid", value: "PAID" },
              ]}
            />
            <Input
              label="Due in (days)"
              type="number"
              min="0"
              name="due_in_days"
              value={form.due_in_days}
              onChange={handleChange}
            />
            <Input label="Description" name="description" value={form.description} onChange={handleChange} />
            <Button type="submit" disabled={createMutation.isLoading} dataTestId="recurring-submit">
              {createMutation.isLoading ? "Saving..." : "Save schedule"}
            </Button>
          </form>
        </Card>
      </div>
    </MainLayout>
  );
};

export default RecurringInvoices;
