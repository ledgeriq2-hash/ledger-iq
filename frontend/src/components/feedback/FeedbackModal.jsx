import React, { useState } from "react";

import feedbackApi from "../../api/feedbackApi.js";
import Modal from "../ui/Modal.jsx";
import Button from "../ui/Button.jsx";
import Select from "../ui/Select.jsx";

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
    } catch {
      setError("Could not send feedback");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} title="Send Feedback" onClose={onClose}>
      <p className="u-text-muted u-m-0">
        Share issues or ideas to help us improve during the soft launch.
      </p>

      {error && <div className="formError">{error}</div>}
      {sent && <div className="formHelper">Thanks for the feedback!</div>}

      <form onSubmit={handleSubmit} className="formStack">
        <Select
          label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          options={categories}
        />

        <label className="formField">
          <span className="formLabel">Message</span>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
            required
            className="kit-textarea"
          />
        </label>

        <div className="modalActions">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Sending..." : "Submit"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default FeedbackModal;

