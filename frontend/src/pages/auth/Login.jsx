import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import AuthLayout from "../../layouts/AuthLayout.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";
import useAuth from "../../hooks/useAuth.js";

const Login = () => {
  const navigate = useNavigate();
  const { login, loading, error: authError } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", tenant: "" });
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await login({ email: form.email, password: form.password, tenant: form.tenant });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err?.message || "Invalid credentials");
    }
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="formStack">
        <Input label="Tenant ID or slug" name="tenant" value={form.tenant} onChange={handleChange} required dataTestId="input-tenant" />
        <Input label="Email" name="email" value={form.email} onChange={handleChange} required dataTestId="input-email" />
        <Input label="Password" name="password" type="password" value={form.password} onChange={handleChange} required dataTestId="input-password" />
        {(error || authError) && <div className="formError">{error || authError}</div>}
        <Button type="submit" disabled={loading} dataTestId="btn-login">
          {loading ? "Signing in..." : "Sign In"}
        </Button>
      </form>
    </AuthLayout>
  );
};

export default Login;
