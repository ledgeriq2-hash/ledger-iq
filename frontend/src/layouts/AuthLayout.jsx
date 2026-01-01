import React from "react";

const AuthLayout = ({ children }) => {
  return (
    <div className="authShell">
      <div className="authGrid">
        <div className="authPanel">
          <div className="authBrand">LEDGER IQ</div>
          <h2 className="authTitle">Modern finance workspace</h2>
          <p className="authIntro">
            Track invoices, collaborate with your team, and let our AI co-pilot spot anomalies before they turn into issues.
          </p>
          <ul className="authBullets">
            <li>Role-based access with audit-ready history</li>
            <li>Billing, reports, and portal in one place</li>
            <li>Guided onboarding to get you live in minutes</li>
          </ul>
        </div>
        <div className="authCard">
          <div className="authCardHeader">
            <h1 className="authCardHeaderTitle">Welcome back</h1>
            <p className="authCardHeaderSubtitle">Sign in or continue onboarding</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
