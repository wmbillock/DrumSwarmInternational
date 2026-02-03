import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import type { Show, WorkLogEntry, SystemHealth, LLMUsageResponse } from "../types";
import * as v1 from "../services/v1";
import { formatMode, formatRole, formatTimestamp } from "../utils/formatters";
import { DataTable } from "../ui";

const QUICK_START_STEPS = [
  { num: 1, label: "Design a Show", desc: "Create and refine your show concept with AI design staff", to: "/design" },
  { num: 2, label: "Approve the Spec", desc: "Review the brief and approve when ready", to: "/shows" },
  { num: 3, label: "Publish the Show", desc: "Publish the approved show to make it available for seasons", to: "/shows" },
  { num: 4, label: "Create a Season", desc: "Group published shows into a season with competitions", to: "/seasons" },
  { num: 5, label: "Launch a Tour", desc: "Assign corps and send them on tour to execute", to: "/tour" },
  { num: 6, label: "Run Competitions", desc: "Corps perform shows autonomously through rehearsal modes", to: "/tour" },
  { num: 7, label: "Review Results", desc: "Score performances, rank results, and crown champions", to: "/finals" },
];

const VITALS_TOOLTIPS: Record<string, string> = {
  "Active Corps": "Number of corps currently in an active lifecycle state",
  "Agents on Field": "AI agents currently assigned and working",
  "Reps Completed": "Work units finished vs total assigned",
  "Failed Reps": "Work units that errored and need retry or reassignment",
  "Stale Reps": "Work units stuck without progress — metronome may reclaim these",
  "Failure Rate": "Percentage of reps that failed across all corps",
};

export function CommandCenter() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [workLog, setWorkLog] = useState<WorkLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cleanupMsg, setCleanupMsg] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState(false);
  const [llmUsage, setLlmUsage] = useState<LLMUsageResponse | null>(null);
  const [guideOpen, setGuideOpen] = useState(() => {
    return !localStorage.getItem("dci-guide-seen");
  });

  const toggleGuide = () => {
    setGuideOpen(prev => {
      if (!prev) return true;
      localStorage.setItem("dci-guide-seen", "1");
      return false;
    });
  };

  const refresh = useCallback(async () => {
    try {
      const [h, s, l, u] = await Promise.allSettled([
        v1.getSystemHealth(),
        v1.listDBShows(),
        v1.getGlobalWorkLog(30),
        v1.getLLMUsage(),
      ]);
      if (h.status === "fulfilled") setHealth(h.value);
      if (s.status === "fulfilled") setShows(s.value);
      if (l.status === "fulfilled") setWorkLog(l.value);
      if (u.status === "fulfilled") setLlmUsage(u.value);

      const anyFailed = [h, s, l].some(r => r.status === "rejected");
      if (anyFailed) {
        const reasons = [h, s, l]
          .filter((r): r is PromiseRejectedResult => r.status === "rejected")
          .map(r => r.reason?.message || "Unknown error");
        setError(`Some data failed to load: ${reasons.join("; ")}`);
      } else {
        setError(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const iv = setInterval(refresh, 15000);
    return () => clearInterval(iv);
  }, [refresh]);

  if (loading) return <div className="page-loading">Loading Command Center...</div>;

  const activeShows = shows.filter(s => s.status === "active");
  const providerRows = llmUsage
    ? llmUsage.providers.map(p => ({
        ...p,
        status_label: p.name === llmUsage.active_provider ? "ACTIVE" : "standby",
        requests: p.stats.requests,
        successes: p.stats.successes,
        failures: p.stats.failures,
        tokens: `${p.stats.total_input_tokens.toLocaleString()} / ${p.stats.total_output_tokens.toLocaleString()} / ${p.stats.total_cached_tokens.toLocaleString()}`,
      }))
    : [];

  return (
    <div className="page-content command-center">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Command Center</h1>
        <button className="small quick-start-toggle" onClick={toggleGuide}>
          ? Quick Start
        </button>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button className="small" style={{ marginLeft: 8 }} onClick={refresh}>Retry</button>
        </div>
      )}

      {/* Quick Start Guide */}
      {guideOpen && (
        <div className="quick-start-guide">
          <div className="quick-start-header">
            <h3 className="quick-start-title">Quick Start Guide</h3>
            <button className="small" onClick={() => { setGuideOpen(false); localStorage.setItem("dci-guide-seen", "1"); }}>
              Dismiss
            </button>
          </div>
          <div className="quick-start-steps">
            {QUICK_START_STEPS.map(step => (
              <Link key={step.num} to={step.to} className="quick-start-step">
                <span className="quick-start-num">{step.num}</span>
                <div className="quick-start-step-content">
                  <span className="quick-start-step-label">{step.label}</span>
                  <span className="quick-start-step-desc">{step.desc}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* System Vitals */}
      <div className="vitals-grid">
        <div className="vital-card" data-tooltip-id="main" data-tooltip-content={VITALS_TOOLTIPS["Active Corps"]}>
          <span className="vital-value">{health?.active_corps ?? 0}</span>
          <span className="vital-label">Active Corps</span>
        </div>
        <div className="vital-card" data-tooltip-id="main" data-tooltip-content={VITALS_TOOLTIPS["Agents on Field"]}>
          <span className="vital-value">{health?.active_agents ?? 0}</span>
          <span className="vital-label">Agents on Field</span>
        </div>
        <div className="vital-card" data-tooltip-id="main" data-tooltip-content={VITALS_TOOLTIPS["Reps Completed"]}>
          <span className="vital-value">{health?.completed_reps ?? 0}/{health?.total_reps ?? 0}</span>
          <span className="vital-label">Reps Completed</span>
        </div>
        <div className="vital-card" data-tooltip-id="main" data-tooltip-content={VITALS_TOOLTIPS["Failed Reps"]}>
          <span className="vital-value">{health?.failed_reps ?? 0}</span>
          <span className="vital-label">Failed Reps</span>
        </div>
        <div className="vital-card" data-tooltip-id="main" data-tooltip-content={VITALS_TOOLTIPS["Stale Reps"]}>
          <span className="vital-value">{health?.stale_reps ?? 0}</span>
          <span className="vital-label">Stale Reps</span>
        </div>
        <div className="vital-card" data-tooltip-id="main" data-tooltip-content={VITALS_TOOLTIPS["Failure Rate"]}>
          <span className="vital-value">{((health?.failure_rate ?? 0) * 100).toFixed(1)}%</span>
          <span className="vital-label">Failure Rate</span>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8, gap: 8, alignItems: "center" }}>
        {cleanupMsg && <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{cleanupMsg}</span>}
        <button
          className="small"
          disabled={cleaning}
          onClick={async () => {
            setCleaning(true);
            setCleanupMsg(null);
            try {
              const r = await v1.adminCleanup();
              setCleanupMsg(`Cleaned: ${r.timed_out_sessions} stale sessions, ${r.disbanded_corps} orphan corps`);
              refresh();
            } catch (e: any) {
              setCleanupMsg(`Cleanup failed: ${e.message}`);
            } finally {
              setCleaning(false);
            }
          }}
        >
          {cleaning ? "Cleaning..." : "Clean Up Stale"}
        </button>
      </div>

      {/* Corps Status */}
      {health?.corps_summaries && health.corps_summaries.length > 0 && (
        <section className="cc-section">
          <h2>Corps on the Field</h2>
          <div className="corps-status-grid">
            {health.corps_summaries.map(c => (
              <div key={c.id} className="corps-status-card clickable" onClick={() => navigate(`/corps/${c.id}`)}>
                <div className="corps-status-header">
                  <span className="corps-status-name">{c.name}</span>
                  {c.mode && <span className={`badge mode-${c.mode}`}>{formatMode(c.mode)}</span>}
                </div>
                <div className="corps-status-stats">
                  <span>{c.agents_active}/{c.agents_total} agents</span>
                  <span>{c.reps_completed}/{c.reps_total} reps</span>
                  {c.failures > 0 && <span className="text-danger">{c.failures} failures</span>}
                </div>
                {c.reps_total > 0 && (
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${(c.reps_completed / c.reps_total) * 100}%` }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Active Shows */}
      <section className="cc-section">
        <h2>Active Shows ({activeShows.length})</h2>
        {activeShows.length === 0 && <p className="empty">No active shows. Create and activate a show to begin.</p>}
        <DataTable<Show & Record<string, unknown>>
          columns={[
            { key: "title", label: "Show", render: (v) => String(v || "—") },
            { key: "corps_name", label: "Corps", render: (v) => String(v || "—") },
            { key: "reps_completed", label: "Progress", render: (_v, row) => `${row.reps_completed ?? 0}/${row.reps_total ?? 0}` },
            { key: "final_score", label: "Score", render: (v) => v != null ? Number(v).toFixed(1) : "—" },
            { key: "created_at", label: "Created", render: (v) => {
              const ts = formatTimestamp(String(v));
              return <span title={ts.title}>{ts.label}</span>;
            } },
          ]}
          data={activeShows as (Show & Record<string, unknown>)[]}
          onRowClick={(row) => row.corps_id && navigate(`/corps/${row.corps_id}`)}
          emptyMessage="No active shows. Create and activate a show to begin."
        />
      </section>

      {/* Agent Usage — LLM Provider Stats */}
      <section className="cc-section">
        <h2>Agent Usage</h2>
        {!llmUsage ? (
          <p className="empty">LLM usage data unavailable.</p>
        ) : (
          <>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
              Router active since {llmUsage.started_at ? formatTimestamp(llmUsage.started_at).label : "unknown"}
              {" | "}Total requests: {llmUsage.total_requests}
              {" | "}Total failures: {llmUsage.total_failures}
            </div>
            <DataTable<Record<string, unknown>>
              columns={[
                { key: "name", label: "Provider", render: (v) => (
                  <span style={{ fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)" }}>{String(v)}</span>
                ) },
                { key: "status_label", label: "Status", render: (v) => String(v) },
                { key: "capabilities", label: "Capabilities", render: (_v, row) => (
                  <>
                    {row.capabilities.supports_images && <span className="badge" style={{ marginRight: 4 }}>IMG</span>}
                    {row.capabilities.supports_native_tools && <span className="badge" style={{ marginRight: 4 }}>TOOLS</span>}
                    {row.capabilities.supports_caching && <span className="badge">CACHE</span>}
                    {!row.capabilities.supports_images && !row.capabilities.supports_native_tools && !row.capabilities.supports_caching && (
                      <span style={{ color: "var(--text-secondary)" }}>text-only</span>
                    )}
                  </>
                ) },
                { key: "requests", label: "Requests" },
                { key: "successes", label: "OK" },
                { key: "failures", label: "Fail", render: (v) => (
                  <span style={Number(v) > 0 ? { color: "var(--stage-red, #ff4444)" } : {}}>
                    {String(v)}
                  </span>
                ) },
                { key: "tokens", label: "Tokens (in/out/cached)", render: (v) => (
                  <span style={{ fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)", fontSize: 11 }}>
                    {String(v)}
                  </span>
                ) },
              ]}
              data={providerRows as Record<string, unknown>[]}
              emptyMessage="No LLM providers reported."
            />

            {llmUsage.failover_events.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <h3 style={{ fontSize: 14, marginBottom: 4 }}>Recent Failovers ({llmUsage.failover_events.length})</h3>
                <div className="activity-list">
                  {llmUsage.failover_events.slice().reverse().slice(0, 10).map((ev, i) => (
                    <div key={i} className="activity-row">
                      <span className="activity-time" title={formatTimestamp(ev.timestamp).title}>
                        {formatTimestamp(ev.timestamp).label}
                      </span>
                      <span className="activity-type" style={{ color: "var(--stage-red, #ff4444)" }}>FAILOVER</span>
                      <span className="activity-detail">
                        {ev.from_provider} &rarr; {ev.to_provider}: {ev.error_snippet.slice(0, 80)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {/* Recent Activity */}
      <section className="cc-section">
        <h2>Recent Activity</h2>
        {workLog.length === 0 && <p className="empty">No activity recorded yet.</p>}
        <div className="activity-list">
          {workLog.slice(0, 20).map(w => (
            <div key={w.id} className="activity-row">
              <span className="activity-type">{w.event_type}</span>
              <span className="activity-role">{w.nickname || formatRole(w.role)}</span>
              <span className="activity-detail">{w.details?.slice(0, 120)}</span>
              <span className="activity-time" title={formatTimestamp(w.timestamp).title}>
                {formatTimestamp(w.timestamp).label}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
