import React, { useState } from "react";
import ModeSwitcher from "./ModeSwitcher.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import ThemeToggle from "./ThemeToggle.jsx";
import FeedbackModal from "../feedback/FeedbackModal.jsx";
import useAuth from "../../hooks/useAuth.js";
import Button from "../ui/Button.jsx";
import { useNavigate } from "react-router-dom";

const Header = ({ onMenu }) => {
  const { tenant, softLaunchBadge, logout } = useAuth();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };
  return (
    <>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "1rem 1rem",
          borderBottom: "1px solid #e2e8f0",
          background: "#fff",
          position: "sticky",
          top: 0,
          zIndex: 6,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            aria-label="Open menu"
            onClick={onMenu}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "38px",
              height: "38px",
              borderRadius: "10px",
              border: "1px solid #e2e8f0",
              background: "#fff",
              cursor: "pointer",
            }}
          >
            ☰
          </button>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.2rem", color: "#0f172a" }}>Dashboard</h2>
            <p style={{ margin: 0, color: "#64748b", fontSize: "0.9rem" }}>Welcome back</p>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
          <button
            style={{
              padding: "0.4rem 0.75rem",
              background: "#0ea5e9",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
            onClick={() => setFeedbackOpen(true)}
          >
            Send Feedback
          </button>
          <Button variant="ghost" onClick={handleLogout} dataTestId="btn-logout">
            Logout
          </Button>
          <ThemeToggle />
          <ModeSwitcher />
          <LanguageSwitcher />
        </div>
      </header>
      {softLaunchBadge && tenant?.is_soft_launch && (
        <div
          style={{
            background: "#ecfeff",
            color: "#0f172a",
            padding: "0.75rem 1.25rem",
            borderBottom: "1px solid #bae6fd",
          }}
        >
          You are part of our early access program. Thank you for piloting Ledger IQ!
        </div>
      )}
      <FeedbackModal open={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
    </>
  );
};

export default Header;
