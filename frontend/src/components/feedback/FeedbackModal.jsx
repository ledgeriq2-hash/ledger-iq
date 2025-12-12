import React, { useState } from "react";
import feedbackApi from "../../api/feedbackApi.js";

const categories = [
  { value: "bug", label: "Bug" },
  { value: "idea", label: "Idea" },
  { value: "confusion", label: "Confusion" },
  { value: "other", label: "Other" },
];

const FeedbackModal = ({ open, onClose }) => {
  const [category, setCategory] = useState("bug");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [sent, setSent] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await feedbackApi.submit({ category, message });
      setSent(true);
      setMessage("");
      setCategory("bug");
      setTimeout(() => setSent(false), 2000);
    } catch (err) {
      setError("Could not send feedback");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,23,42,0.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: "#fff",
          padding: "1.25rem",
          borderRadius: "10px",
          width: "400px",
          boxShadow: "0 10px 30px rgba(15,23,42,0.15)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Send Feedback</h3>
          <button onClick={onClose} style={{ background: "transparent", border: "none", fontSize: "1.1rem" }}>
            ✕
          </button>
        </div>
        <p style={{ margin: "0.25rem 0 0.75rem", color: "#475569" }}>
          Share issues or ideas to help us improve during the soft launch.
        </p>
        {error && <div style={{ color: "#b91c1c", marginBottom: "0.5rem" }}>{error}</div>}
        {sent && <div style={{ color: "#0f766e", marginBottom: "0.5rem" }}>Thanks for the feedback!</div>}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.9rem" }}>
            Category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ padding: "0.45rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              {categories.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem", fontSize: "0.9rem" }}>
            Message
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              required
              style={{ padding: "0.6rem", borderRadius: "6px", border: "1px solid #cbd5e1", resize: "vertical" }}
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            style={{
              padding: "0.55rem 0.75rem",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              opacity: submitting ? 0.7 : 1,
            }}
          >
            {submitting ? "Sending..." : "Submit"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default FeedbackModal;
