import React from "react";

const Card = ({ title, headerRight, children, className = "" }) => {
  return (
    <section className={`kit-card ${className}`.trim()}>
      {(title || headerRight) && (
        <div className="kit-cardHeader">
          {title ? <h3 className="kit-cardTitle">{title}</h3> : <div />}
          {headerRight}
        </div>
      )}
      {children}
    </section>
  );
};

export default Card;

