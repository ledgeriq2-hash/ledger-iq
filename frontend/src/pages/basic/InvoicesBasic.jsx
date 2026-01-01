import React, { useEffect, useMemo, useState } from "react";

import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";
import InvoiceForm from "../../components/forms/InvoiceForm.jsx";
import Card from "../../components/ui/Card.jsx";
import Button from "../../components/ui/Button.jsx";
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
    } catch {
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
    } catch {
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
          <p className="u-text-muted u-m-0">
            Create your first invoice or use the onboarding wizard to generate demo invoices automatically.
          </p>
          <div className="u-flex u-gap-2 u-wrap">
            <Button onClick={() => setEditing({})}>New invoice</Button>
            <a href="/onboarding" className="linkInline">
              Open onboarding ?
            </a>
          </div>
        </Card>
      )}

      <div className="splitGrid">
        <GenericTable
          title={loading ? "Invoices (loading...)" : "Invoices"}
          columns={columns}
          data={normalizedInvoices}
          actions={{ onEdit: (row) => setEditing(row), onDelete: handleDelete }}
        />

        <Card title={editing ? "Edit invoice" : "Create invoice"}>
          {error && <div className="formError">{error}</div>}
          <InvoiceForm customers={customers} initialValues={editing || {}} onSubmit={handleSubmit} submitLabel={editing ? "Update" : "Create"} />
          {editing && (
            <button type="button" className="linkButton" onClick={() => setEditing(null)}>
              Cancel edit
            </button>
          )}
        </Card>
      </div>
    </MainLayout>
  );
};

export default InvoicesBasic;

