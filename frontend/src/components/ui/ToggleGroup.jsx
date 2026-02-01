import React from "react";

import Button from "./Button.jsx";

const ToggleGroup = ({ options = [], value, onChange, className = "" }) => {
  if (!options.length) return null;

  return (
    <div className={`toggleGroup ${className}`.trim()} role="tablist">
      {options.map((option) => {
        const isActive = option.value === value;
        return (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={isActive ? "primary" : "ghost"}
            className="toggleGroupTrigger"
            onClick={() => onChange?.(option.value)}
            aria-pressed={isActive}
            role="tab"
          >
            {option.label}
          </Button>
        );
      })}
    </div>
  );
};

export default ToggleGroup;
