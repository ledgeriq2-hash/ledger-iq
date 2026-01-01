import React, { useState } from "react";

import AuthLayout from "../../layouts/AuthLayout.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";

const ResetPassword = () => {
  const [form, setForm] = useState({ token: "", password: "", confirm: "" });
  const [done, setDone] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) return;
    setDone(true);
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="formStack">
        <Input label="Reset Token" name="token" value={form.token} onChange={handleChange} required />
        <Input label="New Password" name="password" type="password" value={form.password} onChange={handleChange} required />
        <Input label="Confirm Password" name="confirm" type="password" value={form.confirm} onChange={handleChange} required />
        <Button type="submit">Reset Password</Button>
        {done && <div className="formHelper">Password reset placeholder.</div>}
      </form>
    </AuthLayout>
  );
};

export default ResetPassword;

