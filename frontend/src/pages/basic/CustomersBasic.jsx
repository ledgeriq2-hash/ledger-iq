import React, { useEffect, useMemo, useState } from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";
import CustomerForm from "../../components/forms/CustomerForm.jsx";
import Card from "../../components/ui/Card.jsx";
import customersApi from "../../api/customersApi.js";

const CustomersBasic = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);

  const loadCustomers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await customersApi.listCustomers();
      setCustomers(data || []);
    } catch (err) {
      setError("Failed to load customers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCustomers();
  }, []);

  const handleSubmit = async (values) => {
    try {
      if (editing) {
        await customersApi.updateCustomer(editing.id, values);
      } else {
        await customersApi.createCustomer(values);
      }
      setEditing(null);
      await loadCustomers();
    } catch (err) {
      setError("Save failed");
    }
  };

  const handleDelete = async (row) => {
    try {
      await customersApi.deleteCustomer(row.id);
      await loadCustomers();
    } catch {
      setError("Delete failed");
    }
  };

  const columns = useMemo(
    () => [
      { Header: "Name", accessor: "name" },
      { Header: "Email", accessor: "email" },
      { Header: "Phone", accessor: "phone" },
      { Header: "Balance", accessor: "balance" },
    ],
    []
  );

  return (
    <MainLayout>
      {!loading && customers.length === 0 && (
        <Card title="Start with your first customer">
          <p style={{ color: "#475569", marginTop: 0 }}>
            Add a customer or run the onboarding wizard to load a few samples and see invoices flow end-to-end.
          </p>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setEditing({})}
              style={{ padding: "0.55rem 0.9rem", borderRadius: "8px", border: "1px solid #0ea5e9", background: "#0ea5e9", color: "#fff" }}
            >
              Add customer
            </button>
            <a href="/onboarding" style={{ color: "#2563eb", textDecoration: "none", alignSelf: "center" }}>
              Open onboarding →
            </a>
          </div>
        </Card>
      )}
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "2fr 1fr" }}>
        <GenericTable
          title={loading ? "Customers (loading...)" : "Customers"}
          columns={columns}
          data={customers}
          actions={{
            onEdit: (row) => setEditing(row),
            onDelete: handleDelete,
          }}
        />
        <Card title={editing ? "Edit customer" : "Add customer"}>
          {error && <div style={{ color: "#ef4444", marginBottom: "0.5rem" }}>{error}</div>}
          <CustomerForm initialValues={editing || {}} onSubmit={handleSubmit} submitLabel={editing ? "Update" : "Save"} />
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

export default CustomersBasic;
