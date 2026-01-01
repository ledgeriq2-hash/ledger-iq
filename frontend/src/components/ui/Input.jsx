import React from "react";

const Input = ({ label, helper, error, dataTestId, ...props }) => {
  return (
    <label className="formField">
      {label && <span className="formLabel">{label}</span>}
      <input
        className={`kit-input ${error ? "isError" : ""}`.trim()}
        data-testid={dataTestId || props["data-testid"]}
        {...props}
      />
      {helper && <span className="formHelper">{helper}</span>}
      {error && <span className="formError">{error}</span>}
    </label>
  );
};

export default Input;
