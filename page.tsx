"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const [username, setUsername] = useState("");
  const router = useRouter();

  const go = () => {
    const clean = username.trim().toLowerCase().replace(/\s+/g, "-");
    if (clean) router.push(`/${clean}`);
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f8fafc",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }}>
      <div style={{ width: "100%", maxWidth: 420, padding: "0 24px" }}>

        <div style={{ marginBottom: 40, textAlign: "center" }}>
          <div style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            width: 52, height: 52, borderRadius: 14,
            background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
            marginBottom: 20,
            boxShadow: "0 8px 24px rgba(59,130,246,0.25)",
          }}>
            <span style={{ fontSize: 24 }}>◈</span>
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 6 }}>
            Research Radar
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: "#0f172a", letterSpacing: "-0.6px", margin: 0 }}>
            arXiv Digest
          </h1>
          <p style={{ fontSize: 14, color: "#94a3b8", marginTop: 8, lineHeight: 1.6 }}>
            Your daily personalized feed of AI research papers.
          </p>
        </div>

        <div style={{
          background: "#fff",
          border: "1px solid #e2e8f0",
          borderRadius: 16,
          padding: "32px 28px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
        }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: "#475569", display: "block", marginBottom: 8 }}>
            Enter your username
          </label>
          <input
            autoFocus
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === "Enter" && go()}
            placeholder="e.g. kyungmin"
            style={{
              width: "100%",
              padding: "12px 16px",
              fontSize: 16,
              fontWeight: 500,
              border: "1.5px solid #e2e8f0",
              borderRadius: 10,
              outline: "none",
              color: "#0f172a",
              background: "#f8fafc",
              boxSizing: "border-box",
              transition: "border-color 0.15s",
            }}
            onFocus={e => (e.target.style.borderColor = "#3b82f6")}
            onBlur={e => (e.target.style.borderColor = "#e2e8f0")}
          />
          <p style={{ fontSize: 12, color: "#cbd5e1", marginTop: 8 }}>
            New usernames start with default topics. Returning users load their saved topics.
          </p>
          <button
            onClick={go}
            disabled={!username.trim()}
            style={{
              marginTop: 20,
              width: "100%",
              padding: "13px",
              fontSize: 15,
              fontWeight: 700,
              color: "#fff",
              background: username.trim()
                ? "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)"
                : "#e2e8f0",
              border: "none",
              borderRadius: 10,
              cursor: username.trim() ? "pointer" : "not-allowed",
              transition: "opacity 0.15s",
            }}
          >
            Continue →
          </button>
        </div>

      </div>
    </div>
  );
}
