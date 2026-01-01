import React, { useEffect, useState } from "react";

import AuthLayout from "../../layouts/AuthLayout.jsx";
import Input from "../../components/ui/Input.jsx";
import Select from "../../components/ui/Select.jsx";
import Button from "../../components/ui/Button.jsx";
import billingApi from "../../api/billingApi.js";
import useAuth from "../../hooks/useAuth.js";

const Signup = () => {
  const [form, setForm] = useState({ name: "", slug: "", email: "", password: "", plan_code: "free" });
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { register } = useAuth();

  useEffect(() => {
    const loadPlans = async () => {
      try {
        const data = await billingApi.listPlans();
        setPlans(Array.isArray(data) ? data : []);
      } catch {
        setPlans([]);
      }
    };
    loadPlans();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register({
        tenant: { name: form.name, slug: form.slug, plan: form.plan_code },
        admin: { email: form.email, password: form.password },
      });
      window.location.href = "/";
    } catch (err) {
      setError(err?.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const planOptions =
    plans.length > 0
      ? plans.map((plan) => ({
          value: plan.code,
          label: `${plan.name} (${plan.price_cents === 0 ? "Free" : `$${(plan.price_cents / 100).toFixed(0)}/mo`})`,
        }))
      : [{ value: "free", label: "Free" }];

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="formStack">
        <Input label="Company name" name="name" value={form.name} onChange={handleChange} required />
        <Input label="Slug" name="slug" value={form.slug} onChange={handleChange} required />
        <Input label="Email" name="email" type="email" value={form.email} onChange={handleChange} required />
        <Input label="Password" name="password" type="password" value={form.password} onChange={handleChange} required />
        <Select label="Plan" name="plan_code" value={form.plan_code} onChange={handleChange} options={planOptions} />
        {error && <div className="formError">{error}</div>}
        <Button type="submit" disabled={loading}>
          {loading ? "Creating..." : "Create workspace"}
        </Button>
      </form>
    </AuthLayout>
  );
};

export default Signup;
