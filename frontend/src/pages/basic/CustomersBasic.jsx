import React, { useEffect, useMemo, useState } from "react";

import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";
import CustomerForm from "../../components/forms/CustomerForm.jsx";
import Card from "../../components/ui/Card.jsx";
import Button from "../../components/ui/Button.jsx";
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
      const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
      setCustomers(items);
    } catch {
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
    } catch {
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
          <p className="u-text-muted u-m-0">
            Add a customer or run the onboarding wizard to load a few samples and see invoices flow end-to-end.
          </p>
          <div className="u-flex u-gap-2 u-wrap">
            <Button onClick={() => setEditing({})}>Add customer</Button>
            <a href="/onboarding" className="linkInline">
              Open onboarding ?
            </a>
          </div>
        </Card>
      )}

      <div className="splitGrid">
        <GenericTable
          title={loading ? "Customers (loading...)" : "Customers"}
          columns={columns}
          data={customers}
          actions={{ onEdit: (row) => setEditing(row), onDelete: handleDelete }}
        />

        <Card title={editing ? "Edit customer" : "Add customer"}>
          {error && <div className="formError">{error}</div>}
          <CustomerForm initialValues={editing || {}} onSubmit={handleSubmit} submitLabel={editing ? "Update" : "Save"} />
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

export default CustomersBasic;
