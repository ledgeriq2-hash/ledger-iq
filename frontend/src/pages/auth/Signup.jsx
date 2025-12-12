import React, { useMemo, useState } from "react";
import AuthLayout from "../../layouts/AuthLayout.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";
import billingApi from "../../api/billingApi.js";
import authApi from "../../api/authApi.js";

const Signup = () => {
  const [form, setForm] = useState({ name: "", slug: "", email: "", password: "", plan_code: "free" });
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  useMemo(async () => {
    try {
      const data = await billingApi.listPlans();
      setPlans(data || []);
    } catch {
      setPlans([]);
    }
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
      await authApi.register({
        tenant: { name: form.name, slug: form.slug, plan: form.plan_code },
        admin: { email: form.email, password: form.password },
      });
      window.location.href = "/login";
    } catch (err) {
      setError(err?.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
        <Input label="Company name" name="name" value={form.name} onChange={handleChange} required />
        <Input label="Slug" name="slug" value={form.slug} onChange={handleChange} required />
        <Input label="Email" name="email" type="email" value={form.email} onChange={handleChange} required />
        <Input
          label="Password"
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          required
        />
        <div>
          <label style={{ display: "block", marginBottom: "0.35rem", color: "#0f172a", fontWeight: 600 }}>Plan</label>
          <select
            name="plan_code"
            value={form.plan_code}
            onChange={handleChange}
            style={{ width: "100%", padding: "0.65rem 0.75rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
          >
            {plans.map((plan) => (
              <option key={plan.code} value={plan.code}>
                {plan.name} ({plan.price_cents === 0 ? "Free" : `$${(plan.price_cents / 100).toFixed(0)}/mo`})
              </option>
            ))}
          </select>
        </div>
        {error && <div style={{ color: "#ef4444" }}>{error}</div>}
        <Button type="submit" disabled={loading}>
          {loading ? "Creating..." : "Create workspace"}
        </Button>
      </form>
    </AuthLayout>
  );
};

export default Signup;
