import React, { useState } from "react";

import AuthLayout from "../../layouts/AuthLayout.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSent(true);
  };

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="formStack">
        <Input label="Email" name="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Button type="submit">Send reset link</Button>
        {sent && <div className="formHelper">If the email exists, a reset link was sent.</div>}
      </form>
    </AuthLayout>
  );
};

export default ForgotPassword;

