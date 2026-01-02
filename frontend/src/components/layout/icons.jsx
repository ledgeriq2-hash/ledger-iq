import React from "react";

const Svg = ({ title, children }) => (
  <svg className="navIcon" viewBox="0 0 24 24" role="img" aria-label={title}>
    {children}
  </svg>
);

export const IconDashboard = () => (
  <Svg title="Dashboard">
    <path
      d="M4 13.5a2.5 2.5 0 0 1 2.5-2.5h1A2.5 2.5 0 0 1 10 13.5v4A2.5 2.5 0 0 1 7.5 20h-1A2.5 2.5 0 0 1 4 17.5v-4ZM14 6.5A2.5 2.5 0 0 1 16.5 4h1A2.5 2.5 0 0 1 20 6.5v11A2.5 2.5 0 0 1 17.5 20h-1A2.5 2.5 0 0 1 14 17.5v-11ZM4 6.5A2.5 2.5 0 0 1 6.5 4h1A2.5 2.5 0 0 1 10 6.5v1A2.5 2.5 0 0 1 7.5 10h-1A2.5 2.5 0 0 1 4 7.5v-1ZM14 13.5A2.5 2.5 0 0 1 16.5 11h1A2.5 2.5 0 0 1 20 13.5v4A2.5 2.5 0 0 1 17.5 20h-1A2.5 2.5 0 0 1 14 17.5v-4Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconPredictions = () => (
  <Svg title="Predictions">
    <path
      d="M4 19V5a1 1 0 0 1 2 0v14a1 1 0 1 1-2 0Zm4 0V9a1 1 0 0 1 2 0v10a1 1 0 1 1-2 0Zm4 0V12a1 1 0 0 1 2 0v7a1 1 0 1 1-2 0Zm4 0V7a1 1 0 0 1 2 0v12a1 1 0 1 1-2 0Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconRuns = () => (
  <Svg title="Model runs">
    <path
      d="M12 3a9 9 0 1 0 9 9A9.01 9.01 0 0 0 12 3Zm1 9.4 3.1 1.8a1 1 0 1 1-1 1.7l-3.6-2.1a1 1 0 0 1-.5-.9V7a1 1 0 1 1 2 0v5.4Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconData = () => (
  <Svg title="Data">
    <path
      d="M12 3c-4.4 0-8 1.8-8 4v10c0 2.2 3.6 4 8 4s8-1.8 8-4V7c0-2.2-3.6-4-8-4Zm0 2c3.6 0 6 .9 6 2s-2.4 2-6 2-6-.9-6-2 2.4-2 6-2Zm0 14c-3.6 0-6-.9-6-2v-2.1c1.6 1 4.1 1.6 6 1.6s4.4-.6 6-1.6V17c0 1.1-2.4 2-6 2Zm0-5c-3.6 0-6-.9-6-2V9.9c1.6 1 4.1 1.6 6 1.6s4.4-.6 6-1.6V12c0 1.1-2.4 2-6 2Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconTreasury = () => (
  <Svg title="Treasury">
    <path
      d="M4 7c0-2 3.6-4 8-4s8 2 8 4v10c0 2-3.6 4-8 4s-8-2-8-4V7Zm8-2c-3.6 0-6 .9-6 2s2.4 2 6 2 6-.9 6-2-2.4-2-6-2Zm0 12c-3.6 0-6-.9-6-2V11c1.6 1 4.1 1.6 6 1.6s4.4-.6 6-1.6v4c0 1.1-2.4 2-6 2Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconExports = () => (
  <Svg title="Exports">
    <path
      d="M6 3h9a2 2 0 0 1 2 2v12.2a2 2 0 0 1-.6 1.4l-1.8 1.8a2 2 0 0 1-1.4.6H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm9 2H6v14h7.2L15 17.2V5Zm-4 3a1 1 0 0 1 1 1v3.6l.3-.3a1 1 0 1 1 1.4 1.4l-2 2a1 1 0 0 1-1.4 0l-2-2a1 1 0 1 1 1.4-1.4l.3.3V9a1 1 0 0 1 1-1Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconSettings = () => (
  <Svg title="Settings">
    <path
      d="M19.4 13a7.6 7.6 0 0 0 .1-1 7.6 7.6 0 0 0-.1-1l2-1.6a1 1 0 0 0 .2-1.3l-1.9-3.3a1 1 0 0 0-1.2-.4l-2.3.9a7.4 7.4 0 0 0-1.7-1l-.3-2.4A1 1 0 0 0 13.2 1h-3.4a1 1 0 0 0-1 .8l-.3 2.4a7.4 7.4 0 0 0-1.7 1l-2.3-.9a1 1 0 0 0-1.2.4L1.4 8a1 1 0 0 0 .2 1.3l2 1.6a7.6 7.6 0 0 0-.1 1 7.6 7.6 0 0 0 .1 1l-2 1.6a1 1 0 0 0-.2 1.3l1.9 3.3a1 1 0 0 0 1.2.4l2.3-.9a7.4 7.4 0 0 0 1.7 1l.3 2.4a1 1 0 0 0 1 .8h3.4a1 1 0 0 0 1-.8l.3-2.4a7.4 7.4 0 0 0 1.7-1l2.3.9a1 1 0 0 0 1.2-.4l1.9-3.3a1 1 0 0 0-.2-1.3l-2-1.6ZM11.5 15a3 3 0 1 1 3-3 3 3 0 0 1-3 3Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconAI = () => (
  <Svg title="AI">
    <path
      d="M12 3l1.8 3.6L17.4 8l-3.6 1.8L12 13.4 10.2 9.8 6.6 8l3.6-1.4L12 3Zm6.4 7.6 1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2ZM5.6 11.4l.8 1.6 1.6.8-1.6.8-.8 1.6-.8-1.6-1.6-.8 1.6-.8.8-1.6Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconCustomers = () => (
  <Svg title="Customers">
    <path
      d="M8 8a4 4 0 1 1 8 0 4 4 0 0 1-8 0Zm-4 12a8 8 0 0 1 16 0v1H4v-1Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconEmployees = () => (
  <Svg title="Employees">
    <path
      d="M7 9a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0Zm-4 12a7 7 0 0 1 14 0v1H3v-1Zm14.5-9.5a3 3 0 1 1 3 3 3 3 0 0 1-3-3Zm2.5 10.5v-1a6 6 0 0 0-2.2-4.7A7.9 7.9 0 0 1 21 21v1Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconInvoices = () => (
  <Svg title="Invoices">
    <path
      d="M6 3h9l3 3v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm8 1H7v16h10V7h-3V4Zm-6 6h6v2H8v-2Zm0 4h6v2H8v-2Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconPayments = () => (
  <Svg title="Payments">
    <path
      d="M4 6h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Zm0 2v2h16V8H4Zm0 4v4h6v-4H4Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconInventory = () => (
  <Svg title="Inventory">
    <path
      d="M12 3 4 7v10l8 4 8-4V7l-8-4Zm0 2.2 5.6 2.8L12 10.8 6.4 8 12 5.2Zm-6 4.4 5 2.5v6.4L6 16.2V9.6Zm12 0v6.6l-5 2.5v-6.4l5-2.7Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconSuppliers = () => (
  <Svg title="Suppliers">
    <path
      d="M3 6h11v8h2l3 3v3h-2.2a2 2 0 0 1-3.8 0H8a2 2 0 0 1-4 0H2v-2a2 2 0 0 1 1-1V7a1 1 0 0 1 1-1Zm3 10a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2ZM4 8v6h1.2a2 2 0 0 1 3.6 0H14V8H4Zm12 2v4h2v-1l-2-3Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconReports = () => (
  <Svg title="Reports">
    <path
      d="M5 19V9h3v10H5Zm5 0V5h3v14h-3Zm5 0v-7h3v7h-3Z"
      fill="currentColor"
    />
  </Svg>
);

export const IconAdmin = () => (
  <Svg title="Admin">
    <path
      d="M12 2 5 5v6c0 5.2 3.6 9.7 7 11 3.4-1.3 7-5.8 7-11V5l-7-3Zm0 3.2 4 1.7v4.1c0 3.6-2.2 6.8-4 8-1.8-1.2-4-4.4-4-8V6.9l4-1.7Z"
      fill="currentColor"
    />
  </Svg>
);
