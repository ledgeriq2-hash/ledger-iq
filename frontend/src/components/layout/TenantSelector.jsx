import React, { useEffect, useState } from "react";

import Button from "../ui/Button.jsx";
import useAuth from "../../hooks/useAuth.js";

const TenantSelector = () => {
  const { tenantId, tenant, setTenantId } = useAuth();
  const [value, setValue] = useState(tenantId || "");

  useEffect(() => {
    setValue(tenantId || "");
  }, [tenantId]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const next = String(value || "").trim();
    if (!next) return;
    setTenantId(next);
  };

  const handleClear = () => {
    setTenantId(null);
    setValue("");
    if (typeof window !== "undefined") {
      localStorage.removeItem("ledgeriqlastTenantId");
    }
  };

  return (
    <form className="tenantSelector" onSubmit={handleSubmit}>
      <span className="tenantSelectorLabel">
        {tenant?.name ? `Company: ${tenant.name}` : "Company"}
      </span>
      <input
        className="tenantSelectorInput"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={tenant?.name ? `${tenant.name} ID` : "Select company"}
        aria-label="Tenant ID"
      />
      {tenantId ? (
        <Button type="button" size="sm" variant="ghost" onClick={handleClear} className="tenantSelectorButton">
          Clear
        </Button>
      ) : (
        <Button type="submit" size="sm" className="tenantSelectorButton" disabled={!value.trim()}>
          Set
        </Button>
      )}
    </form>
  );
};

export default TenantSelector;
