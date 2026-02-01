import React from "react";

import Button from "./Button.jsx";

const Dialog = ({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  confirmVariant = "secondary",
  loading = false,
  children,
  className = "",
}) => {
  if (!open) return null;

  const descriptionId = description ? "dialog-description" : undefined;

  return (
    <div className="dialogBackdrop">
      <section
        className={`dialogPanel ${className}`.trim()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby={descriptionId}
      >
        <div>
          <h3 id="dialog-title" className="dialogTitle">
            {title}
          </h3>
          {description ? (
            <p id="dialog-description" className="dialogDescription">
              {description}
            </p>
          ) : null}
        </div>
        {children ? <div className="dialogBody">{children}</div> : null}
        <div className="dialogActions">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button variant={confirmVariant} size="sm" onClick={onConfirm} disabled={loading || !onConfirm}>
            {loading ? `${confirmLabel}...` : confirmLabel}
          </Button>
        </div>
      </section>
    </div>
  );
};

export default Dialog;
