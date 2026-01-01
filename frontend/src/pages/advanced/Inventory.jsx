import React, { useContext, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Banner from "../../components/ui/Banner.jsx";
import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import ErrorBox from "../../components/ui/ErrorBox.jsx";
import Input from "../../components/ui/Input.jsx";
import Select from "../../components/ui/Select.jsx";
import Tag from "../../components/ui/Tag.jsx";
import inventoryApi from "../../api/inventoryApi.js";
import productsApi from "../../api/productsApi.js";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";
import { NotificationContext } from "../../contexts/NotificationContext.jsx";

const Inventory = () => {
  const queryClient = useQueryClient();
  const { addNotification } = useContext(NotificationContext);
  const [form, setForm] = useState({
    product_id: "",
    quantity: "",
    movement_type: "ADJUST",
    reference_type: "MANUAL",
  });
  const [formError, setFormError] = useState(null);

  const summaryQuery = useQuery({
    queryKey: ["inventory", "summary"],
    queryFn: () => inventoryApi.summary(),
  });

  const movementsQuery = useQuery({
    queryKey: ["inventory", "movements"],
    queryFn: () => inventoryApi.listMovements({ page_size: 50 }),
  });

  const productsQuery = useQuery({
    queryKey: ["products-lite"],
    queryFn: () => productsApi.listProducts(),
  });

  const movementMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createMovement(payload),
    onSuccess: () => {
      addNotification?.({ title: "Stock updated" });
      queryClient.invalidateQueries(["inventory", "summary"]);
      queryClient.invalidateQueries(["inventory", "movements"]);
      setForm({ product_id: "", quantity: "", movement_type: "ADJUST", reference_type: "MANUAL" });
      setFormError(null);
    },
    onError: (err) => setFormError(err?.message || "Failed to create movement"),
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.product_id || !form.quantity) {
      setFormError("Product and quantity required");
      return;
    }
    setFormError(null);
    movementMutation.mutate({
      product_id: form.product_id,
      quantity: form.quantity,
      movement_type: form.movement_type,
      reference_type: form.reference_type,
    });
  };

  const products = productsQuery.data?.items || productsQuery.data || [];
  const summaryItems = summaryQuery.data?.items || [];
  const movements = movementsQuery.data?.items || [];

  const totalValue = summaryQuery.data?.total_value;

  const movementTypes = useMemo(
    () => [
      { label: "Increase (IN)", value: "IN" },
      { label: "Decrease (OUT)", value: "OUT" },
      { label: "Adjust to quantity", value: "ADJUST" },
    ],
    []
  );

  return (
    <div className="u-grid u-gap-4">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md }}>
        <div>
          <h1 style={{ margin: 0, color: colors.text }}>Inventory</h1>
          <p style={{ margin: 0, color: colors.textMuted }}>Track stock movements and valuation.</p>
        </div>
        {totalValue !== undefined && (
          <Tag tone="default">Total value: {totalValue}</Tag>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: spacing.lg, alignItems: "start" }}>
        <Card title="Stock Summary">
          {summaryQuery.isLoading && <Banner message="Loading summary..." variant="info" />}
          {summaryQuery.isError && <ErrorBox message={summaryQuery.error?.message || "Failed to load summary"} />}
          {!summaryQuery.isLoading && summaryItems.length === 0 && (
            <Banner message="No products yet. Add products to start tracking inventory." variant="info" />
          )}
          <div style={{ display: "grid", gap: spacing.sm }}>
            {summaryItems.map((item) => (
              <div
                key={item.product_id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr 1fr",
                  padding: spacing.sm,
                  borderBottom: `1px solid ${colors.border}`,
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, color: colors.text }}>{item.product_name}</div>
                  <div style={{ color: colors.textMuted }}>{item.sku || "?"}</div>
                </div>
                <div style={{ color: colors.text }}>
                  Stock: <strong>{item.stock_quantity}</strong>
                </div>
                <div style={{ color: colors.textMuted }}>
                  Value: <strong>{item.valuation}</strong>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Manual adjustment">
          {productsQuery.isError && <ErrorBox message={productsQuery.error?.message || "Failed to load products"} />}
          {formError && <ErrorBox message={formError} />}
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: spacing.md }}>
            <Select
              label="Product"
              name="product_id"
              value={form.product_id}
              onChange={handleChange}
              options={[{ label: "Select product", value: "" }, ...products.map((p) => ({ label: p.name, value: p.id }))]}
              required
            />
            <Input label="Quantity" name="quantity" type="number" min="0" step="0.01" value={form.quantity} onChange={handleChange} required />
            <Select label="Movement type" name="movement_type" value={form.movement_type} onChange={handleChange} options={movementTypes} required />
            <Button type="submit" disabled={movementMutation.isLoading} dataTestId="inventory-submit">
              {movementMutation.isLoading ? "Saving..." : "Save movement"}
            </Button>
          </form>
        </Card>
      </div>

      <Card title="Recent movements" style={{ marginTop: spacing.lg }}>
        {movementsQuery.isLoading && <Banner message="Loading movements..." variant="info" />}
        {movementsQuery.isError && <ErrorBox message={movementsQuery.error?.message || "Failed to load movements"} />}
        <div style={{ display: "grid", gap: spacing.sm }}>
          {movements.map((mv) => (
            <div
              key={mv.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr 1fr",
                padding: spacing.sm,
                borderBottom: `1px solid ${colors.border}`,
              }}
            >
              <div>{mv.product?.name || mv.product_id}</div>
              <div>{mv.movement_type}</div>
              <div>{mv.quantity}</div>
              <div style={{ color: colors.textMuted }}>{new Date(mv.created_at).toLocaleString()}</div>
            </div>
          ))}
          {movements.length === 0 && !movementsQuery.isLoading && (
            <Banner message="No stock movements recorded yet." variant="info" />
          )}
        </div>
      </Card>
    </div>
  );
};

export default Inventory;
