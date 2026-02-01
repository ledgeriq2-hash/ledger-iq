import React, { useEffect, useRef, useState } from "react";

import Button from "./Button.jsx";

const DropdownMenu = ({ items = [], triggerLabel = "Actions", align = "right", className = "" }) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const handleClick = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", handleClick);
    return () => window.removeEventListener("mousedown", handleClick);
  }, [open]);

  useEffect(() => {
    const handleKey = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleSelect = (item) => {
    if (item.disabled) return;
    item.onSelect?.();
    setOpen(false);
  };

  return (
    <div className={`dropdownMenu ${className}`.trim()} ref={containerRef}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={triggerLabel}
      >
        ⋯
      </Button>
      {open && items.length ? (
        <div role="menu" className={`dropdownMenuList dropdownMenuList-${align}`}>
          {items.map((item) => (
            <button
              key={item.key || item.label}
              type="button"
              className="dropdownMenuItem"
              onClick={() => handleSelect(item)}
              disabled={item.disabled}
              role="menuitem"
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default DropdownMenu;
