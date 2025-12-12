import React from "react";

const Select = ({ label, options = [], ...props }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
      {label && <label style={{ fontSize: "0.95rem", color: "#0f172a" }}>{label}</label>}
      <select
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: "8px",
          padding: "0.6rem 0.75rem",
          outline: "none",
          background: "#fff",
        }}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default Select;
