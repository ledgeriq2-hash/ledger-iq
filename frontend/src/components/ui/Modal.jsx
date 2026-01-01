import React from "react";
import Card from "./Card.jsx";
import Button from "./Button.jsx";

const Modal = ({ open, title, onClose, children, actions }) => {
  if (!open) return null;
  return (
    <div className="modalOverlay" role="dialog" aria-modal="true">
      <Card
        title={title}
        actions={
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        }
        className="modalCard"
      >
        {children}
        {actions && <div className="modalActions">{actions}</div>}
      </Card>
    </div>
  );
};

export default Modal;
