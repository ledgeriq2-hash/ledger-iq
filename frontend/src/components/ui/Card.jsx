import React from "react";

const Card = ({ title, subtitle, actions, children, className = "" }) => {
  return (
    <section className={`kit-card ${className}`.trim()}>
      {(title || actions) && (
        <div className="kit-cardHeader">
          <div>
            {title && <h3 className="kit-cardTitle">{title}</h3>}
            {subtitle && <div className="kit-muted">{subtitle}</div>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
};

export default Card;
