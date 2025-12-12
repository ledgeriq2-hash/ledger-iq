import React, { useState } from "react";
import Input from "../ui/Input.jsx";
import Button from "../ui/Button.jsx";
import Select from "../ui/Select.jsx";

const InvoiceForm = ({ initialValues = {}, onSubmit, customers = [], submitLabel = "Save Invoice" }) => {
  const [form, setForm] = useState({
    customer_id: "",
    issue_date: "",
    due_date: "",
    status: "DRAFT",
    currency: "USD",
    total_amount: "",
    notes: "",
    ...initialValues,
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.customer_id || !form.issue_date) return;
    onSubmit?.(form);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
      <Select
        label="Customer"
        name="customer_id"
        value={form.customer_id}
        onChange={handleChange}
        options={[{ label: "Select customer", value: "" }, ...customers.map((c) => ({ label: c.name, value: c.id }))]}
        required
        data-testid="invoice-customer"
      />
      <Input
        label="Issue Date"
        type="date"
        name="issue_date"
        value={form.issue_date}
        onChange={handleChange}
        required
        dataTestId="invoice-issue-date"
      />
      <Input label="Due Date" type="date" name="due_date" value={form.due_date} onChange={handleChange} dataTestId="invoice-due-date" />
      <Select
        label="Status"
        name="status"
        value={form.status}
        onChange={handleChange}
        options={[
          { label: "Draft", value: "DRAFT" },
          { label: "Sent", value: "SENT" },
          { label: "Paid", value: "PAID" },
          { label: "Overdue", value: "OVERDUE" },
          { label: "Cancelled", value: "CANCELLED" },
        ]}
        data-testid="invoice-status"
      />
      <Input label="Currency" name="currency" value={form.currency} onChange={handleChange} required dataTestId="invoice-currency" />
      <Input
        label="Total Amount"
        type="number"
        name="total_amount"
        value={form.total_amount}
        onChange={handleChange}
        required
        dataTestId="invoice-total"
      />
      <Input label="Notes" name="notes" value={form.notes} onChange={handleChange} dataTestId="invoice-notes" />
      <Button type="submit" dataTestId="invoice-submit">
        {submitLabel}
      </Button>
    </form>
  );
};

export default InvoiceForm;
