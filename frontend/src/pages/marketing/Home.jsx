import React from "react";

const Section = ({ title, children }) => (
  <section className="marketingSection">
    <h2 className="marketingSectionTitle">{title}</h2>
    <div className="marketingSectionBody">{children}</div>
  </section>
);

const Home = () => (
  <div className="marketingShell">
    <header className="marketingHeader">
      <div className="marketingBrand">Ledger IQ</div>
      <nav className="marketingNav">
        <a href="/pricing" className="marketingNavLink">
          Pricing
        </a>
        <a href="/signup" className="marketingNavCta">
          Get started
        </a>
      </nav>
    </header>

    <section className="marketingHero">
      <div className="marketingHeroInner">
        <h1 className="marketingHeroTitle">Modern accounting, automated</h1>
        <p className="marketingHeroSubtitle">
          Ledger IQ brings billing, reporting, and AI insights together with secure portals for your customers and
          suppliers.
        </p>
        <div className="marketingHeroActions">
          <a href="/signup" className="marketingHeroPrimary">
            Start free trial
          </a>
          <a href="/pricing" className="marketingHeroSecondary">
            View pricing
          </a>
        </div>
      </div>
    </section>

    <Section title="Everything you need to launch">
      <ul className="marketingBullets">
        <li>AI-powered anomaly detection and forecasting</li>
        <li>Customer and supplier portals with secure token access</li>
        <li>Role-based controls, audit logs, and MFA</li>
      </ul>
    </Section>
  </div>
);

export default Home;

