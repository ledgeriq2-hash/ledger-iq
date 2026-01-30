import React from "react";

import Button from "./Button.jsx";
import Card from "./Card.jsx";

const Modal = ({ open, title, onClose, children, actions }) => {
  if (!open) return null;

  return (
    <div className="modalOverlay" role="dialog" aria-modal="true">
      <div className="modalCard">
        <Card
          title={title}
          headerRight={
            <Button variant="ghost" type="button" onClick={onClose}>
              Close
            </Button>
          }
        >
          {children}
          {actions ? <div className="modalActions">{actions}</div> : null}
        </Card>
      </div>
    </div>
  );
};

export default Modal;

