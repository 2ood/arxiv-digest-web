"use client";

import { useState, useEffect, useCallback } from "react";

type Topic = {
  id: string;
  name: string;
  enabled: boolean;
  terms: string[];
  description: string;
};

const BADGE_COLORS = [
  "bg-sky-900 text-sky-300 border-sky-700",
  "bg-violet-900 text-violet-300 border-violet-700",
  "bg-emerald-900 text-emerald-300 border-emerald-700",
  "bg-amber-900 text-amber-300 border-amber-700",
  "bg-rose-900 text-rose-300 border-rose-700",
];

function slugify(name: string) {
  return name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
}

export default function Page() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "error">("idle");
  const [triggering, setTriggering] = useState(false);
  const [triggerStatus, setTriggerStatus] = useState<"idle" | "ok" | "error">("idle");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newTermInputs, setNewTermInputs] = useState<Record<string, string>>({});
  const [addingTopic, setAddingTopic] = useState(false);
  const [newTopicName, setNewTopicName] = useState("");
  const [newTopicDesc, setNewTopicDesc] = useState("");

  useEffect(() => {
    fetch("/api/topics")
      .then((r) => r.json())
      .then(setTopics);
  }, []);

  const save = useCallback(async (updated: Topic[]) => {
    setSaving(true);
    setSaveStatus("idle");
    try {
      const r = await fetch("/api/topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updated),
      });
      setSaveStatus(r.ok ? "saved" : "error");
    } catch {
      setSaveStatus("error");
    }
    setSaving(false);
    setTimeout(() => setSaveStatus("idle"), 2500);
  }, []);

  const updateTopics = (updated: Topic[]) => {
    setTopics(updated);
    save(updated);
  };

  const toggleEnabled = (id: string) => {
    updateTopics(topics.map((t) => (t.id === id ? { ...t, enabled: !t.enabled } : t)));
  };

  const removeTerm = (topicId: string, term: string) => {
    updateTopics(
      topics.map((t) =>
        t.id === topicId ? { ...t, terms: t.terms.filter((x) => x !== term) } : t
      )
    );
  };

  const addTerm = (topicId: string) => {
    const val = newTermInputs[topicId]?.trim();
    if (!val) return;
    const topic = topics.find((t) => t.id === topicId);
    if (!topic || topic.terms.includes(val)) return;
    updateTopics(
      topics.map((t) => (t.id === topicId ? { ...t, terms: [...t.terms, val] } : t))
    );
    setNewTermInputs((prev) => ({ ...prev, [topicId]: "" }));
  };

  const updateDescription = (topicId: string, desc: string) => {
    setTopics(topics.map((t) => (t.id === topicId ? { ...t, description: desc } : t)));
  };

  const saveDescription = (topicId: string) => {
    save(topics);
  };

  const removeTopic = (id: string) => {
    updateTopics(topics.filter((t) => t.id !== id));
  };

  const addTopic = () => {
    if (!newTopicName.trim()) return;
    const newTopic: Topic = {
      id: slugify(newTopicName),
      name: newTopicName.trim(),
      enabled: true,
      terms: [],
      description: newTopicDesc.trim(),
    };
    updateTopics([...topics, newTopic]);
    setNewTopicName("");
    setNewTopicDesc("");
    setAddingTopic(false);
    setExpandedId(newTopic.id);
  };

  const triggerDigest = async () => {
    setTriggering(true);
    setTriggerStatus("idle");
    try {
      const r = await fetch("/api/trigger", { method: "POST" });
      setTriggerStatus(r.ok ? "ok" : "error");
    } catch {
      setTriggerStatus("error");
    }
    setTriggering(false);
    setTimeout(() => setTriggerStatus("idle"), 3000);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" style={{ fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}>
      {/* Import font */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        .term-chip { transition: all 0.1s; }
        .term-chip:hover .remove-btn { opacity: 1; }
        .remove-btn { opacity: 0; transition: opacity 0.1s; }
        .topic-card { transition: border-color 0.15s; }
        input:focus, textarea:focus { outline: none; }
        ::selection { background: #7c3aed44; }
      `}</style>

      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div>
          <div className="text-xs text-zinc-500 tracking-widest uppercase mb-1">Research Radar</div>
          <h1 className="text-lg font-semibold text-zinc-100" style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}>
            arXiv Digest
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {saveStatus === "saved" && (
            <span className="text-xs text-emerald-400 tracking-wide">✓ saved</span>
          )}
          {saveStatus === "error" && (
            <span className="text-xs text-rose-400 tracking-wide">✗ save failed</span>
          )}
          <button
            onClick={triggerDigest}
            disabled={triggering}
            className="flex items-center gap-2 px-4 py-2 text-xs border border-zinc-700 rounded text-zinc-300 hover:border-violet-500 hover:text-violet-300 transition-colors disabled:opacity-50"
          >
            {triggering ? (
              <span className="animate-pulse">sending…</span>
            ) : triggerStatus === "ok" ? (
              <span className="text-emerald-400">✓ triggered</span>
            ) : triggerStatus === "error" ? (
              <span className="text-rose-400">✗ failed</span>
            ) : (
              <>
                <span>▶</span>
                <span>Run digest now</span>
              </>
            )}
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        {/* Section header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-sm font-medium text-zinc-300" style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}>
              Topics
            </h2>
            <p className="text-xs text-zinc-600 mt-1">
              {topics.filter((t) => t.enabled).length} of {topics.length} active
            </p>
          </div>
          <button
            onClick={() => setAddingTopic(true)}
            className="text-xs px-3 py-1.5 border border-dashed border-zinc-700 rounded text-zinc-500 hover:border-zinc-500 hover:text-zinc-300 transition-colors"
          >
            + new topic
          </button>
        </div>

        {/* New topic form */}
        {addingTopic && (
          <div className="mb-4 border border-violet-800 rounded-lg p-4 bg-violet-950/20">
            <div className="text-xs text-violet-400 mb-3 tracking-wide">NEW TOPIC</div>
            <input
              autoFocus
              value={newTopicName}
              onChange={(e) => setNewTopicName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addTopic()}
              placeholder="Topic name…"
              className="w-full bg-transparent border-b border-zinc-700 pb-1 mb-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500"
            />
            <textarea
              value={newTopicDesc}
              onChange={(e) => setNewTopicDesc(e.target.value)}
              placeholder="Semantic description (used for embedding search)…"
              rows={2}
              className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-xs text-zinc-300 placeholder:text-zinc-600 resize-none focus:border-violet-700"
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={addTopic}
                className="text-xs px-3 py-1.5 bg-violet-700 hover:bg-violet-600 rounded text-white transition-colors"
              >
                Create
              </button>
              <button
                onClick={() => { setAddingTopic(false); setNewTopicName(""); setNewTopicDesc(""); }}
                className="text-xs px-3 py-1.5 text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Topic cards */}
        <div className="space-y-3">
          {topics.map((topic, idx) => {
            const colorClass = BADGE_COLORS[idx % BADGE_COLORS.length];
            const isExpanded = expandedId === topic.id;

            return (
              <div
                key={topic.id}
                className={`topic-card border rounded-lg ${
                  topic.enabled ? "border-zinc-800 bg-zinc-900/50" : "border-zinc-800/50 bg-zinc-900/20 opacity-60"
                } ${isExpanded ? "border-zinc-700" : ""}`}
              >
                {/* Card header */}
                <div className="flex items-center gap-3 px-4 py-3">
                  {/* Toggle */}
                  <button
                    onClick={() => toggleEnabled(topic.id)}
                    className={`w-8 h-4 rounded-full transition-colors flex-shrink-0 ${
                      topic.enabled ? "bg-violet-600" : "bg-zinc-700"
                    }`}
                    style={{ position: "relative" }}
                    title={topic.enabled ? "Disable" : "Enable"}
                  >
                    <span
                      className="absolute top-0.5 w-3 h-3 bg-white rounded-full transition-transform"
                      style={{ transform: topic.enabled ? "translateX(18px)" : "translateX(2px)" }}
                    />
                  </button>

                  {/* Name */}
                  <button
                    className="flex-1 text-left text-sm font-medium text-zinc-200 hover:text-white transition-colors"
                    style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}
                    onClick={() => setExpandedId(isExpanded ? null : topic.id)}
                  >
                    {topic.name}
                  </button>

                  {/* Term count */}
                  <span className="text-xs text-zinc-600">{topic.terms.length} terms</span>

                  {/* Expand chevron */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : topic.id)}
                    className="text-zinc-600 hover:text-zinc-400 transition-colors text-xs"
                  >
                    {isExpanded ? "▲" : "▼"}
                  </button>

                  {/* Delete */}
                  <button
                    onClick={() => removeTopic(topic.id)}
                    className="text-zinc-700 hover:text-rose-500 transition-colors text-xs ml-1"
                    title="Remove topic"
                  >
                    ✕
                  </button>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-zinc-800/50 pt-4">
                    {/* Description */}
                    <div className="mb-4">
                      <div className="text-xs text-zinc-600 mb-1.5 tracking-wide">SEMANTIC DESCRIPTION</div>
                      <textarea
                        value={topic.description}
                        onChange={(e) => updateDescription(topic.id, e.target.value)}
                        onBlur={() => saveDescription(topic.id)}
                        rows={2}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded p-2 text-xs text-zinc-400 placeholder:text-zinc-700 resize-none focus:border-zinc-600"
                      />
                    </div>

                    {/* Terms */}
                    <div className="mb-3">
                      <div className="text-xs text-zinc-600 mb-2 tracking-wide">KEYWORDS & SYNONYMS</div>
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {topic.terms.map((term) => (
                          <span
                            key={term}
                            className={`term-chip relative flex items-center gap-1 px-2 py-0.5 text-xs border rounded ${colorClass}`}
                          >
                            {term}
                            <button
                              className="remove-btn ml-0.5 hover:text-white"
                              onClick={() => removeTerm(topic.id, term)}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>

                      {/* Add term input */}
                      <div className="flex gap-2">
                        <input
                          value={newTermInputs[topic.id] ?? ""}
                          onChange={(e) =>
                            setNewTermInputs((prev) => ({ ...prev, [topic.id]: e.target.value }))
                          }
                          onKeyDown={(e) => e.key === "Enter" && addTerm(topic.id)}
                          placeholder="add term and press Enter…"
                          className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-300 placeholder:text-zinc-700 focus:border-zinc-600"
                        />
                        <button
                          onClick={() => addTerm(topic.id)}
                          className="text-xs px-3 py-1.5 border border-zinc-700 rounded text-zinc-500 hover:text-zinc-300 hover:border-zinc-500 transition-colors"
                        >
                          add
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer note */}
        <div className="mt-10 pt-6 border-t border-zinc-900 text-xs text-zinc-700 leading-relaxed">
          Changes are saved automatically to Vercel KV and picked up by the next digest run.
          The pipeline runs daily at 08:00 UTC on weekdays.
        </div>
      </main>
    </div>
  );
}
