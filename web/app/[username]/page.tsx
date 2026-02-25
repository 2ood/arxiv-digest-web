"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";

type Topic = {
  id: string;
  name: string;
  enabled: boolean;
  terms: string[];
  description: string;
};

const CHIP_PALETTES = [
  { bg: "#dbeafe", color: "#1d4ed8", border: "#93c5fd" },
  { bg: "#dcfce7", color: "#15803d", border: "#86efac" },
  { bg: "#fef3c7", color: "#b45309", border: "#fcd34d" },
  { bg: "#fce7f3", color: "#be185d", border: "#f9a8d4" },
  { bg: "#ede9fe", color: "#6d28d9", border: "#c4b5fd" },
  { bg: "#ccfbf1", color: "#0f766e", border: "#5eead4" },
];

function slugify(name: string) {
  return name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
}

export default function UserPage() {
  const { username } = useParams<{ username: string }>();
  const router = useRouter();

  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newTermInputs, setNewTermInputs] = useState<Record<string, string>>({});
  const [addingTopic, setAddingTopic] = useState(false);
  const [newTopicName, setNewTopicName] = useState("");
  const [newTopicDesc, setNewTopicDesc] = useState("");

  useEffect(() => {
    fetch(`/api/topics/${username}`)
      .then(r => r.json())
      .then(data => { setTopics(data); setLoading(false); });
  }, [username]);

  const persist = useCallback(async (updated: Topic[]) => {
    setSaving(true);
    await fetch(`/api/topics/${username}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topics: updated }),
    });
    setSaving(false);
  }, [username]);

  const updateTopics = (updated: Topic[]) => {
    setTopics(updated);
    persist(updated);
  };

  const toggleEnabled = (id: string) =>
    updateTopics(topics.map(t => t.id === id ? { ...t, enabled: !t.enabled } : t));

  const removeTerm = (topicId: string, term: string) =>
    updateTopics(topics.map(t => t.id === topicId ? { ...t, terms: t.terms.filter(x => x !== term) } : t));

  const addTerm = (topicId: string) => {
    const val = newTermInputs[topicId]?.trim();
    if (!val) return;
    const topic = topics.find(t => t.id === topicId);
    if (!topic || topic.terms.includes(val)) return;
    updateTopics(topics.map(t => t.id === topicId ? { ...t, terms: [...t.terms, val] } : t));
    setNewTermInputs(p => ({ ...p, [topicId]: "" }));
  };

  const removeTopic = (id: string) => updateTopics(topics.filter(t => t.id !== id));

  const addTopic = () => {
    if (!newTopicName.trim()) return;
    const t: Topic = {
      id: slugify(newTopicName),
      name: newTopicName.trim(),
      enabled: true,
      terms: [],
      description: newTopicDesc.trim(),
    };
    updateTopics([...topics, t]);
    setNewTopicName(""); setNewTopicDesc(""); setAddingTopic(false);
    setExpandedId(t.id);
  };

  const showDigest = () => {
    // Save topics to sessionStorage so digest page can read them without re-fetching
    sessionStorage.setItem(`topics:${username}`, JSON.stringify(topics));
    router.push(`/${username}/digest`);
  };

  if (loading) return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "system-ui, sans-serif", color: "#94a3b8", fontSize: 14 }}>
      Loading topics…
    </div>
  );

  const enabledCount = topics.filter(t => t.enabled).length;

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>

      {/* Header */}
      <header style={{ background: "#fff", borderBottom: "1px solid #e2e8f0", padding: "14px 24px", display: "flex", alignItems: "center", gap: 12, position: "sticky", top: 0, zIndex: 50, boxShadow: "0 1px 8px rgba(0,0,0,0.04)" }}>
        <button onClick={() => router.push("/")} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18, color: "#94a3b8", padding: "0 4px 0 0", lineHeight: 1 }}>←</button>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", color: "#94a3b8" }}>arXiv Digest</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>{username}</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {saving && <span style={{ fontSize: 12, color: "#94a3b8" }}>Saving…</span>}
          <button
            onClick={showDigest}
            disabled={enabledCount === 0}
            style={{
              padding: "10px 22px",
              fontSize: 14, fontWeight: 700,
              color: "#fff",
              background: enabledCount > 0 ? "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)" : "#e2e8f0",
              border: "none", borderRadius: 10, cursor: enabledCount > 0 ? "pointer" : "not-allowed",
              boxShadow: enabledCount > 0 ? "0 4px 14px rgba(59,130,246,0.3)" : "none",
              transition: "all 0.15s",
            }}
          >
            Show Digest →
          </button>
        </div>
      </header>

      <main style={{ maxWidth: 760, margin: "0 auto", padding: "32px 24px 80px" }}>

        {/* Section header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: 0 }}>Topics</h2>
            <p style={{ fontSize: 13, color: "#94a3b8", marginTop: 3 }}>{enabledCount} of {topics.length} active</p>
          </div>
          <button
            onClick={() => setAddingTopic(true)}
            style={{ fontSize: 13, padding: "7px 14px", border: "1.5px dashed #cbd5e1", borderRadius: 8, background: "none", color: "#94a3b8", cursor: "pointer" }}
          >
            + New topic
          </button>
        </div>

        {/* New topic form */}
        {addingTopic && (
          <div style={{ marginBottom: 16, border: "1.5px solid #c4b5fd", borderRadius: 12, padding: "20px", background: "#faf5ff" }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#8b5cf6", marginBottom: 12 }}>New Topic</div>
            <input
              autoFocus
              value={newTopicName}
              onChange={e => setNewTopicName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && addTopic()}
              placeholder="Topic name…"
              style={{ width: "100%", background: "none", border: "none", borderBottom: "1.5px solid #ddd6fe", paddingBottom: 6, marginBottom: 12, fontSize: 15, fontWeight: 600, color: "#0f172a", outline: "none", boxSizing: "border-box" }}
            />
            <textarea
              value={newTopicDesc}
              onChange={e => setNewTopicDesc(e.target.value)}
              placeholder="Semantic description for embedding search…"
              rows={2}
              style={{ width: "100%", background: "#fff", border: "1px solid #e9d5ff", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#374151", resize: "none", outline: "none", boxSizing: "border-box" }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button onClick={addTopic} style={{ padding: "7px 16px", fontSize: 13, fontWeight: 600, background: "#8b5cf6", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" }}>Create</button>
              <button onClick={() => { setAddingTopic(false); setNewTopicName(""); setNewTopicDesc(""); }} style={{ padding: "7px 16px", fontSize: 13, color: "#94a3b8", background: "none", border: "none", cursor: "pointer" }}>Cancel</button>
            </div>
          </div>
        )}

        {/* Topic cards */}
        <div>
          {topics.map((topic, idx) => {
            const palette = CHIP_PALETTES[idx % CHIP_PALETTES.length];
            const isExpanded = expandedId === topic.id;
            return (
              <div key={topic.id} style={{
                border: `1px solid ${isExpanded ? "#cbd5e1" : "#e2e8f0"}`,
                borderLeft: `4px solid ${topic.enabled ? palette.border : "#e2e8f0"}`,
                borderRadius: 12,
                background: "#fff",
                marginBottom: 10,
                opacity: topic.enabled ? 1 : 0.55,
                transition: "all 0.15s",
                boxShadow: isExpanded ? "0 4px 16px rgba(0,0,0,0.06)" : "0 1px 3px rgba(0,0,0,0.03)",
              }}>
                {/* Card header */}
                <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "14px 16px" }}>
                  {/* Toggle */}
                  <div
                    onClick={() => toggleEnabled(topic.id)}
                    style={{
                      width: 36, height: 20, borderRadius: 10,
                      background: topic.enabled ? palette.bg : "#f1f5f9",
                      border: `1.5px solid ${topic.enabled ? palette.border : "#e2e8f0"}`,
                      position: "relative", cursor: "pointer", flexShrink: 0, transition: "all 0.15s",
                    }}
                  >
                    <div style={{
                      position: "absolute", top: 2, width: 12, height: 12, borderRadius: "50%",
                      background: topic.enabled ? palette.color : "#cbd5e1",
                      left: topic.enabled ? 18 : 2, transition: "left 0.15s",
                    }} />
                  </div>

                  <button
                    onClick={() => setExpandedId(isExpanded ? null : topic.id)}
                    style={{ flex: 1, textAlign: "left", background: "none", border: "none", cursor: "pointer", fontSize: 15, fontWeight: 600, color: "#0f172a" }}
                  >
                    {topic.name}
                  </button>

                  <span style={{ fontSize: 12, color: "#cbd5e1" }}>{topic.terms.length} terms</span>

                  <button onClick={() => setExpandedId(isExpanded ? null : topic.id)} style={{ background: "none", border: "none", cursor: "pointer", color: "#cbd5e1", fontSize: 12 }}>
                    {isExpanded ? "▲" : "▼"}
                  </button>
                  <button onClick={() => removeTopic(topic.id)} style={{ background: "none", border: "none", cursor: "pointer", color: "#fca5a5", fontSize: 13 }}>✕</button>
                </div>

                {/* Expanded */}
                {isExpanded && (
                  <div style={{ padding: "0 16px 16px", borderTop: "1px solid #f1f5f9" }}>
                    {/* Description */}
                    <div style={{ marginTop: 14, marginBottom: 14 }}>
                      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 6 }}>Semantic Description</div>
                      <textarea
                        value={topic.description}
                        onChange={e => setTopics(topics.map(t => t.id === topic.id ? { ...t, description: e.target.value } : t))}
                        onBlur={() => persist(topics)}
                        rows={2}
                        style={{ width: "100%", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "#475569", resize: "none", outline: "none", boxSizing: "border-box" }}
                      />
                    </div>

                    {/* Terms */}
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Keywords & Synonyms</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                      {topic.terms.map(term => (
                        <span key={term} style={{
                          display: "inline-flex", alignItems: "center", gap: 4,
                          padding: "4px 10px", borderRadius: 999, fontSize: 12, fontWeight: 500,
                          background: palette.bg, color: palette.color,
                          border: `1.5px solid ${palette.border}`,
                        }}>
                          {term}
                          <button onClick={() => removeTerm(topic.id, term)} style={{ background: "none", border: "none", cursor: "pointer", color: palette.color, fontSize: 13, lineHeight: 1, padding: 0, opacity: 0.6 }}>×</button>
                        </span>
                      ))}
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        value={newTermInputs[topic.id] ?? ""}
                        onChange={e => setNewTermInputs(p => ({ ...p, [topic.id]: e.target.value }))}
                        onKeyDown={e => e.key === "Enter" && addTerm(topic.id)}
                        placeholder="Add term and press Enter…"
                        style={{ flex: 1, padding: "8px 12px", fontSize: 13, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, outline: "none", color: "#0f172a" }}
                      />
                      <button
                        onClick={() => addTerm(topic.id)}
                        style={{ padding: "8px 14px", fontSize: 13, background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 8, cursor: "pointer", color: "#475569", fontWeight: 500 }}
                      >
                        Add
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
