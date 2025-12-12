import React, { useEffect, useMemo, useState } from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";
import InvoiceForm from "../../components/forms/InvoiceForm.jsx";
import Card from "../../components/ui/Card.jsx";
import invoicesApi from "../../api/invoicesApi.js";
import customersApi from "../../api/customersApi.js";

const InvoicesBasic = () => {
  const [invoices, setInvoices] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  const loadInvoices = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await invoicesApi.listInvoices();
      setInvoices(data?.items || data || []);
    } catch (err) {
      setError("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  const loadCustomers = async () => {
    try {
      const data = await customersApi.listCustomers();
      setCustomers(data?.items || data || []);
    } catch {
      // ignore customer load error for now
    }
  };

  useEffect(() => {
    loadInvoices();
    loadCustomers();
  }, []);

  const handleSubmit = async (values) => {
    try {
      if (editing) {
        await invoicesApi.updateInvoice(editing.id, values);
      } else {
        await invoicesApi.createInvoice(values);
      }
      setEditing(null);
      await loadInvoices();
    } catch (err) {
      setError("Save failed");
    }
  };

  const handleDelete = async (row) => {
    try {
      await invoicesApi.deleteInvoice(row.id);
      await loadInvoices();
    } catch {
      setError("Delete failed");
    }
  };

  const columns = useMemo(
    () => [
      { Header: "Customer", accessor: "customer_name" },
      { Header: "Status", accessor: "status" },
      { Header: "Issue Date", accessor: "issue_date" },
      { Header: "Due Date", accessor: "due_date" },
      { Header: "Total", accessor: "total_amount" },
    ],
    []
  );

  const normalizedInvoices = invoices.map((inv) => ({
    ...inv,
    customer_name: inv.customer?.name || inv.customer_name || inv.customer_id,
  }));

  return (
    <MainLayout>
      {!loading && normalizedInvoices.length === 0 && (
        <Card title="No invoices yet">
          <p style={{ color: "#475569", marginTop: 0 }}>
            Create your first invoice or use the onboarding wizard to generate demo invoices automatically.
          </p>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setEditing({})}
              style={{ padding: "0.55rem 0.9rem", borderRadius: "8px", border: "1px solid #0ea5e9", background: "#0ea5e9", color: "#fff" }}
            >
              New invoice
            </button>
            <a href="/onboarding" style={{ color: "#2563eb", textDecoration: "none", alignSelf: "center" }}>
              Open onboarding →
            </a>
          </div>
        </Card>
      )}
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "2fr 1fr" }}>
        <GenericTable
          title={loading ? "Invoices (loading...)" : "Invoices"}
          columns={columns}
          data={normalizedInvoices}
          actions={{
            onEdit: (row) => setEditing(row),
            onDelete: handleDelete,
          }}
        />
        <Card title={editing ? "Edit invoice" : "Create invoice"}>
          {error && <div style={{ color: "#ef4444", marginBottom: "0.5rem" }}>{error}</div>}
          <InvoiceForm
            customers={customers}
            initialValues={editing || {}}
            onSubmit={handleSubmit}
            submitLabel={editing ? "Update" : "Create"}
          />
          {editing && (
            <button
              style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#2563eb" }}
              onClick={() => setEditing(null)}
            >
              Cancel edit
            </button>
          )}
        </Card>
      </div>
    </MainLayout>
  );
};

export default InvoicesBasic;
