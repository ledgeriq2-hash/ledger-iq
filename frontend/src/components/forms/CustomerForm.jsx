import React, { useState } from "react";
import Input from "../ui/Input.jsx";
import Button from "../ui/Button.jsx";

const CustomerForm = ({ initialValues = {}, onSubmit, submitLabel = "Save" }) => {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    address: "",
    tax_id: "",
    ...initialValues,
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name) return;
    onSubmit?.(form);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
      <Input label="Name" name="name" value={form.name} onChange={handleChange} required dataTestId="customer-name" />
      <Input label="Email" name="email" value={form.email} onChange={handleChange} dataTestId="customer-email" />
      <Input label="Phone" name="phone" value={form.phone} onChange={handleChange} dataTestId="customer-phone" />
      <Input label="Address" name="address" value={form.address} onChange={handleChange} />
      <Input label="Tax ID" name="tax_id" value={form.tax_id} onChange={handleChange} />
      <Button type="submit" dataTestId="customer-submit">
        {submitLabel}
      </Button>
    </form>
  );
};

export default CustomerForm;
