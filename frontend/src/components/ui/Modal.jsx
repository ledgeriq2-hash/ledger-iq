import React from "react";
import Card from "./Card.jsx";
import Button from "./Button.jsx";

const Modal = ({ open, title, onClose, children, actions }) => {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,23,42,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <Card
        title={title}
        actions={
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        }
        style={{ maxWidth: "520px", width: "100%" }}
      >
        {children}
        {actions && <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>{actions}</div>}
      </Card>
    </div>
  );
};

export default Modal;
