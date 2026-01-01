import React from "react";

const Footer = ({ appName = "Ledger IQ", buildText }) => {
  const year = new Date().getFullYear();
  return (
    <footer className="appFooter">
      {appName} ? {year}
      {buildText ? ` ú ${buildText}` : ""}
    </footer>
  );
};

export default Footer;

