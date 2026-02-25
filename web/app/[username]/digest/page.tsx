"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";

type Paper = {
  id: string;
  title: string;
  abstract: string;
  authors: string[];
  url: string;
  published: string;
  topics: string[];
  match_method: string;
};

const CHIP_PALETTES = [
  { bg: "#dbeafe", color: "#1d4ed8", border: "#93c5fd", accent: "#3b82f6" },
  { bg: "#dcfce7", color: "#15803d", border: "#86efac", accent: "#22c55e" },
  { bg: "#fef3c7", color: "#b45309", border: "#fcd34d", accent: "#f59e0b" },
  { bg: "#fce7f3", color: "#be185d", border: "#f9a8d4", accent: "#ec4899" },
  { bg: "#ede9fe", color: "#6d28d9", border: "#c4b5fd", accent: "#8b5cf6" },
  { bg: "#ccfbf1", color: "#0f766e", border: "#5eead4", accent: "#14b8a6" },
];

const PROGRESS_STEPS = [
  { pct: 8,  label: "Connecting to arXiv…" },
  { pct: 25, label: "Fetching recent papers…" },
  { pct: 45, label: "Running keyword filter…" },
  { pct: 70, label: "Running semantic matching…" },
  { pct: 88, label: "Assembling digest…" },
  { pct: 100, label: "Done!" },
];

const PAGE_SIZE = 5;

export default function DigestPage() {
  const { username } = useParams<{ username: string }>();
  const router = useRouter();

  const [phase, setPhase] = useState<"loading" | "results" | "error">("loading");
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState(PROGRESS_STEPS[0].label);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [stats, setStats] = useState<{ fetched: number; matched: number } | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  // Filter + pagination state
  const [allTopics, setAllTopics] = useState<string[]>([]);
  const [activeTopics, setActiveTopics] = useState<Set<string>>(new Set());
  const [topicPaletteMap, setTopicPaletteMap] = useState<Record<string, number>>({});
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);

  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    runDigest();
  }, []);

  async function runDigest() {
    // Grab topics from sessionStorage (set by topic editor page)
    const raw = sessionStorage.getItem(`topics:${username}`);
    const topics = raw ? JSON.parse(raw) : null;

    if (!topics) {
      setErrorMsg("No topics found. Please go back and configure your topics.");
      setPhase("error");
      return;
    }

    // Animate progress while fetch is in flight
    let stepIdx = 0;
    const interval = setInterval(() => {
      stepIdx = Math.min(stepIdx + 1, PROGRESS_STEPS.length - 2); // stop at "Assembling"
      setProgress(PROGRESS_STEPS[stepIdx].pct);
      setProgressLabel(PROGRESS_STEPS[stepIdx].label);
    }, 4500);

    try {
      const res = await fetch("/api/digest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, topics }),
      });

      clearInterval(interval);

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt);
      }

      const data = await res.json();

      // Snap to 100%
      setProgress(100);
      setProgressLabel("Done!");

      // Build topic metadata
      const topicNames: string[] = [];
      const seen = new Set<string>();
      for (const p of data.papers) {
        for (const t of p.topics) {
          if (!seen.has(t)) { topicNames.push(t); seen.add(t); }
        }
      }
      const paletteMap: Record<string, number> = {};
      topicNames.forEach((t, i) => { paletteMap[t] = i % CHIP_PALETTES.length; });

      setAllTopics(topicNames);
      setActiveTopics(new Set(topicNames));
      setTopicPaletteMap(paletteMap);
      setPapers(data.papers);
      setStats(data.stats);

      // Short pause so user sees 100% before results appear
      setTimeout(() => setPhase("results"), 600);
    } catch (err: any) {
      clearInterval(interval);
      setErrorMsg(err.message || "Something went wrong.");
      setPhase("error");
    }
  }

  // ── Filtering & pagination ────────────────────────────────────────────────
  const filteredPapers = papers.filter(p => p.topics.some(t => activeTopics.has(t)));
  const totalPages = Math.ceil(filteredPapers.length / PAGE_SIZE);
  const pagePapers = filteredPapers.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const toggleTopic = (t: string) => {
    setActiveTopics(prev => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });
    setCurrentPage(1);
  };

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  // ── Loading screen ────────────────────────────────────────────────────────
  if (phase === "loading") return (
    <div style={{
      minHeight: "100vh", background: "#f8fafc",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }}>
      <div style={{ width: "100%", maxWidth: 440, padding: "0 24px", textAlign: "center" }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>arXiv Digest</div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", marginBottom: 32 }}>Building your digest…</h2>

        {/* Progress bar */}
        <div style={{ background: "#e2e8f0", borderRadius: 999, height: 8, overflow: "hidden", marginBottom: 14 }}>
          <div style={{
            height: "100%", borderRadius: 999,
            background: "linear-gradient(90deg, #3b82f6, #8b5cf6)",
            width: `${progress}%`,
            transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
          }} />
        </div>

        <div style={{ fontSize: 13, color: "#64748b", fontWeight: 500 }}>{progressLabel}</div>
        <div style={{ fontSize: 12, color: "#cbd5e1", marginTop: 6 }}>{progress}%</div>
      </div>
    </div>
  );

  // ── Error screen ──────────────────────────────────────────────────────────
  if (phase === "error") return (
    <div style={{
      minHeight: "100vh", background: "#f8fafc",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }}>
      <div style={{ textAlign: "center", maxWidth: 400, padding: "0 24px" }}>
        <div style={{ fontSize: 32, marginBottom: 16 }}>⚠️</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>Something went wrong</h2>
        <p style={{ fontSize: 14, color: "#64748b", marginBottom: 24 }}>{errorMsg}</p>
        <button onClick={() => router.push(`/${username}`)} style={{ padding: "10px 24px", fontSize: 14, fontWeight: 600, background: "#3b82f6", color: "#fff", border: "none", borderRadius: 10, cursor: "pointer" }}>← Back to topics</button>
      </div>
    </div>
  );

  // ── Results ───────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>

      {/* Sticky header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 100,
        background: "#f8fafc",
        borderBottom: "1px solid #e2e8f0",
        padding: "14px 24px 12px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.05)",
      }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          {/* Title row */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <button onClick={() => router.push(`/${username}`)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18, color: "#94a3b8", padding: 0 }}>←</button>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", color: "#94a3b8" }}>arXiv Digest · {username}</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>
                {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
              </div>
            </div>
            {stats && (
              <div style={{ marginLeft: "auto", fontSize: 12, color: "#94a3b8", textAlign: "right" }}>
                <div><b style={{ color: "#475569" }}>{stats.matched}</b> matched</div>
                <div>{stats.fetched} fetched</div>
              </div>
            )}
          </div>

          {/* Topic filter chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
            {allTopics.map(t => {
              const pal = CHIP_PALETTES[topicPaletteMap[t] ?? 0];
              const active = activeTopics.has(t);
              return (
                <button key={t} onClick={() => toggleTopic(t)} style={{
                  padding: "5px 14px", borderRadius: 999, fontSize: 12, fontWeight: 600,
                  border: `1.5px solid ${active ? pal.border : "#e2e8f0"}`,
                  background: active ? pal.bg : "#f1f5f9",
                  color: active ? pal.color : "#94a3b8",
                  cursor: "pointer", transition: "all 0.15s",
                }}>
                  {t}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Paper list */}
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "28px 24px 80px" }}>

        {filteredPapers.length === 0 ? (
          <div style={{ textAlign: "center", color: "#94a3b8", padding: "64px 0", fontSize: 15 }}>
            No papers match the selected topics.
          </div>
        ) : (
          <>
            {pagePapers.map(paper => {
              const pal = CHIP_PALETTES[topicPaletteMap[paper.topics[0]] ?? 0];
              const isExpanded = expandedIds.has(paper.id);
              const previewText = paper.abstract.slice(0, 320) + (paper.abstract.length > 320 ? "…" : "");
              const authors = paper.authors.join(", ");

              return (
                <div key={paper.id} style={{
                  border: "1px solid #e2e8f0",
                  borderLeft: `4px solid ${pal.accent}`,
                  borderRadius: 10,
                  padding: "22px 24px",
                  marginBottom: 14,
                  background: "#fff",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
                  transition: "box-shadow 0.15s",
                }}>
                  <a href={paper.url} target="_blank" rel="noreferrer" style={{
                    fontSize: 17, fontWeight: 700, color: "#0f172a",
                    textDecoration: "none", lineHeight: 1.4, display: "block", marginBottom: 6,
                  }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#3b82f6")}
                    onMouseLeave={e => (e.currentTarget.style.color = "#0f172a")}
                  >
                    {paper.title}
                  </a>
                  <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 12 }}>{authors}</div>

                  <div style={{ fontSize: 15, color: "#475569", lineHeight: 1.7 }}>
                    {isExpanded ? paper.abstract : previewText}
                  </div>
                  {paper.abstract.length > 320 && (
                    <button onClick={() => toggleExpand(paper.id)} style={{
                      background: "none", border: "none", cursor: "pointer",
                      fontSize: 12, fontWeight: 600, color: "#3b82f6",
                      padding: 0, marginTop: 8, display: "block",
                    }}>
                      {isExpanded ? "Show less ↑" : "Show more ↓"}
                    </button>
                  )}

                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 16, flexWrap: "wrap" }}>
                    {paper.topics.map(t => {
                      const p = CHIP_PALETTES[topicPaletteMap[t] ?? 0];
                      return (
                        <span key={t} style={{
                          fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 999,
                          background: p.bg, color: p.color, border: `1.5px solid ${p.border}`,
                        }}>{t}</span>
                      );
                    })}
                    <a href={paper.url} target="_blank" rel="noreferrer" style={{
                      marginLeft: "auto", fontSize: 12, fontWeight: 600,
                      color: "#64748b", textDecoration: "none",
                    }}
                      onMouseEnter={e => (e.currentTarget.style.color = "#3b82f6")}
                      onMouseLeave={e => (e.currentTarget.style.color = "#64748b")}
                    >
                      PDF →
                    </a>
                  </div>
                </div>
              );
            })}

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 36 }}>
                <button disabled={currentPage === 1} onClick={() => { setCurrentPage(p => p - 1); window.scrollTo(0, 0); }}
                  style={{ padding: "7px 14px", fontSize: 13, fontWeight: 500, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, cursor: currentPage === 1 ? "not-allowed" : "pointer", color: "#64748b", opacity: currentPage === 1 ? 0.4 : 1 }}>
                  ← Prev
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
                  <button key={n} onClick={() => { setCurrentPage(n); window.scrollTo(0, 0); }}
                    style={{ padding: "7px 14px", fontSize: 13, fontWeight: n === currentPage ? 700 : 500, background: n === currentPage ? "#3b82f6" : "#fff", color: n === currentPage ? "#fff" : "#64748b", border: `1px solid ${n === currentPage ? "#3b82f6" : "#e2e8f0"}`, borderRadius: 8, cursor: "pointer" }}>
                    {n}
                  </button>
                ))}
                <button disabled={currentPage === totalPages} onClick={() => { setCurrentPage(p => p + 1); window.scrollTo(0, 0); }}
                  style={{ padding: "7px 14px", fontSize: 13, fontWeight: 500, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, cursor: currentPage === totalPages ? "not-allowed" : "pointer", color: "#64748b", opacity: currentPage === totalPages ? 0.4 : 1 }}>
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
