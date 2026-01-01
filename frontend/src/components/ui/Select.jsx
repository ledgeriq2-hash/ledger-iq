import React from "react";

const Select = ({ label, options = [], ...props }) => {
  return (
    <div className="formField">
      {label && <label className="formLabel">{label}</label>}
      <select className="kit-select" {...props}>
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
