import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import ModeSwitcher from "./ModeSwitcher.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import FeedbackModal from "../feedback/FeedbackModal.jsx";
import useAuth from "../../hooks/useAuth.js";
import Button from "../ui/Button.jsx";

const Header = ({ onMenu }) => {
  const { tenant, softLaunchBadge, logout } = useAuth();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <>
      <header className="layoutHeaderBar">
        <div className="layoutHeaderLeft">
          <button aria-label="Open menu" onClick={onMenu} className="layoutHeaderMenuButton" type="button">
            ?
          </button>
          <div>
            <h2 className="layoutHeaderTitle">Dashboard</h2>
            <p className="layoutHeaderSubtitle">Welcome back</p>
          </div>
        </div>
        <div className="layoutHeaderRight">
          <button className="layoutHeaderFeedbackButton" onClick={() => setFeedbackOpen(true)} type="button">
            Send Feedback
          </button>
          <Button variant="ghost" onClick={handleLogout} dataTestId="btn-logout">
            Logout
          </Button>
          <ModeSwitcher />
          <LanguageSwitcher />
        </div>
      </header>
      {softLaunchBadge && tenant?.is_soft_launch && (
        <div className="softLaunchBanner">
          You are part of our early access program. Thank you for piloting Ledger IQ!
        </div>
      )}
      <FeedbackModal open={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
    </>
  );
};

export default Header;
