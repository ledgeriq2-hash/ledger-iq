import React from "react";

const Plan = ({ name, price, features }) => (
  <div className="planCard">
    <h3 className="planName">{name}</h3>
    <div className="planPrice">{price}</div>
    <ul className="planBullets">
      {features.map((f) => (
        <li key={f}>{f}</li>
      ))}
    </ul>
    <a href="/signup" className="planCta">
      Choose plan
    </a>
  </div>
);

const Pricing = () => (
  <div className="pricingShell">
    <header className="pricingHeader">
      <a href="/" className="pricingBrand">
        Ledger IQ
      </a>
      <a href="/signup" className="pricingCta">
        Get started
      </a>
    </header>
    <main className="pricingMain">
      <div className="pricingIntro">
        <h1 className="pricingTitle">Simple pricing</h1>
        <p className="pricingSubtitle">Pick the plan that fits your team today and scale later.</p>
      </div>
      <div className="pricingGrid">
        <Plan name="Free" price="$0" features={["Up to 3 users", "Customer portal", "AI previews"]} />
        <Plan name="Pro" price="$49" features={["25 users", "AI anomalies + forecasts", "Billing + portal payments", "Support SLA"]} />
      </div>
    </main>
  </div>
);

export default Pricing;

