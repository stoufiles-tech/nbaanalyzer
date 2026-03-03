import { useState } from "react";

export default function DataQualityBanner() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div
      className="data-quality-banner"
      style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: 8,
        padding: "0.75rem 1rem",
        marginBottom: "1rem",
        display: "flex",
        alignItems: "flex-start",
        gap: "0.75rem",
        fontSize: "0.85rem",
        color: "#94a3b8",
      }}
    >
      <span style={{ fontSize: "1.1rem", lineHeight: 1 }}>i</span>
      <div style={{ flex: 1 }}>
        <strong style={{ color: "#e2e8f0" }}>Salary Data Note:</strong>{" "}
        Salary figures are <em>base salary</em> from Basketball-Reference, not official
        cap hits. Trade bonuses, incentives, and structured deal adjustments are not
        reflected. Use the cap-hit override feature for manual corrections.
      </div>
      <button
        onClick={() => setDismissed(true)}
        style={{
          background: "none",
          border: "none",
          color: "#64748b",
          cursor: "pointer",
          fontSize: "1.1rem",
          padding: "0 0.25rem",
          lineHeight: 1,
        }}
        aria-label="Dismiss"
      >
        x
      </button>
    </div>
  );
}
