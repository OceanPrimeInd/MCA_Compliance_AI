import { useState, useEffect, useRef } from "react";
import * as storage from "./lib/storage";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { supabase } from "./lib/supabase";
import Login from "./components/Login";
import VesselProfile, { VesselBadge } from "./components/VesselProfile";
import CompareCodes from "./components/CompareCodes";
import ComplianceRecord from "./components/ComplianceRecord";
import { api } from "./lib/api";
import Markdown from "./lib/markdown";
import "./components/vessel.css";
import { RouterProvider, useRoute } from "./lib/router";
import Nav from "./marketing/Nav";
import Footer from "./marketing/Footer";
import Home from "./marketing/Home";
import Solution from "./marketing/Solution";
import Documents from "./marketing/Documents";
import Pricing from "./marketing/Pricing";
import FAQ from "./marketing/FAQ";
import Demo from "./marketing/Demo";
import "./marketing/marketing.css";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function uuid() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}

function scoreColor(score) {
  if (score >= 0.6) return "#0F7B5F";
  if (score >= 0.45) return "#B5720B";
  return "#C0392B";
}

function SourceChips({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  return (
    <div className="sources">
      <div className="chip-row">
        {sources.map((s, i) => (
          <span className="chip" key={i} title={s.code_name || ""}>
            <span className="chip-dot" style={{ background: scoreColor(s.score) }} />
            {s.clause} · p.{s.page}
            {s.code_name && (
              <span className="chip-code">
                {s.code_name.includes("Workboat") ? "WBC3" : "SPVC"}
              </span>
            )}
          </span>
        ))}
      </div>
      <button className="expander" onClick={() => setOpen(!open)}>
        {open ? "Hide cited clause text" : "View cited clause text"}
      </button>
      {open && (
        <div className="cited-block">
          {sources.map((s, i) => (
            <div key={i} className="cited-item">
              <div className="cited-label">
                {s.code_name ? `${s.code_name} — ` : ""}Clause {s.clause} — p.{s.page}{" "}
                (relevance {s.score.toFixed(2)})
              </div>
              <div className="cited-text">{s.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusRow({ elapsed, fromCache, verified, modelUsed }) {
  // A fallback provider answered. Worth surfacing: the reserve model follows the
  // strict verdict rules less reliably, so the reader should weigh it knowing that.
  const isFallback = modelUsed && !String(modelUsed).startsWith("gemini-3.5");
  return (
    <div className="status-row">
      <span className="badge badge-time">{elapsed.toFixed(1)}s</span>
      {fromCache && <span className="badge badge-cache">⚡ cached</span>}
      {isFallback && (
        <span className="badge badge-fallback" title={`Answered by ${modelUsed}`}>
          ↯ reserve model
        </span>
      )}
      <span className={verified ? "badge badge-verified" : "badge badge-unverified"}>
        {verified ? "✓ verified" : "⚠ unverified citation"}
      </span>
    </div>
  );
}

function ChatMessage({ msg }) {
  return (
    <div className={`msg-row ${msg.role}`}>
      {msg.role === "assistant" && <div className="avatar">⚓</div>}
      <div className="msg-bubble">
        {msg.role === "assistant" ? (
          <>
            {msg.verdictGuard && (
              <div className="guard-note">
                <strong>Safety downgrade</strong> — the engine first stated{" "}
                {msg.verdictGuard.downgraded_from.replace("_", " ").toLowerCase()}.{" "}
                {msg.verdictGuard.reason}
              </div>
            )}
            <Markdown text={msg.content} />
          </>
        ) : (
          <p>{msg.content}</p>
        )}
        {msg.role === "assistant" && msg.sources && (
          <>
            <SourceChips sources={msg.sources} />
            {msg.topScore < 0.45 && (
              <div className="low-confidence">
                ⚠ Weak match to the Code — verify with the MCA or a Certifying Authority.
              </div>
            )}
            <StatusRow
              elapsed={msg.elapsed}
              fromCache={msg.fromCache}
              verified={msg.verified}
              modelUsed={msg.modelUsed}
            />
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Two contrasting vessels that sit on opposite sides of the Code's own
 * thresholds — 12m and 15m for length, and the Category 0/1 vs 2-6 split.
 * Switching between them re-runs the last question, so the change in the
 * answer is the demonstration.
 */
const DEMO_VESSELS = [
  {
    key: "small",
    label: "11m · Cat 2",
    profile: {
      vessel_type: "workboat",
      length_overall: 11,
      area_category: 2,
      hull_material: "GRP",
      passenger_count: 8,
    },
  },
  {
    key: "large",
    label: "18.5m · Cat 0",
    profile: {
      vessel_type: "workboat",
      length_overall: 18.5,
      area_category: 0,
      hull_material: "Aluminium",
      passenger_count: 30,
    },
  },
];

function matchesPreset(vessel, preset) {
  if (!vessel) return false;
  return (
    Number(vessel.length_overall) === preset.profile.length_overall &&
    Number(vessel.area_category) === preset.profile.area_category
  );
}

function VesselSwitcher({ vessel, onSwitch, busy }) {
  return (
    <div className="vessel-switcher">
      <span className="vessel-switcher__label">Switch vessel</span>
      {DEMO_VESSELS.map((v) => (
        <button
          key={v.key}
          className={`vessel-switcher__btn${matchesPreset(vessel, v) ? " active" : ""}`}
          onClick={() => onSwitch(v.profile)}
          disabled={busy}
        >
          {v.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Debug Context Mode.
 *
 * Shows what the applicability filter removed and why. The dropped clauses are
 * the evidence that filtering happened at all — an answer alone cannot prove a
 * clause was excluded rather than simply never retrieved.
 */
function ContextDebugPanel({ msg, vessel, onClose }) {
  const dropped = msg?.filteredOut ?? [];
  const kept = msg?.sources ?? [];

  return (
    <aside className="ctx-panel">
      <div className="ctx-panel__head">
        <div>
          <div className="ctx-panel__title">Context Layer</div>
          <div className="ctx-panel__sub">
            {vessel
              ? `${vessel.length_overall}m · Category ${vessel.area_category} · ${vessel.passenger_count} pax`
              : "No vessel set — filtering inactive"}
          </div>
        </div>
        <button className="ctx-panel__close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      {!msg && <div className="ctx-empty">Ask a question to see what gets filtered.</div>}

      {msg && (
        <>
          <div className="ctx-stat-row">
            <div className="ctx-stat ctx-stat--drop">
              <div className="ctx-stat__num">{dropped.length}</div>
              <div className="ctx-stat__label">dropped</div>
            </div>
            <div className="ctx-stat ctx-stat--keep">
              <div className="ctx-stat__num">{kept.length}</div>
              <div className="ctx-stat__label">used</div>
            </div>
          </div>

          <div className="ctx-section-title">Excluded — cannot bind this vessel</div>
          {dropped.length === 0 ? (
            <div className="ctx-empty">
              Nothing excluded for this question. Every retrieved clause is in scope.
            </div>
          ) : (
            dropped.map((d, i) => (
              <div className="ctx-drop" key={i}>
                <div className="ctx-drop__clause">
                  Clause {d.clause_number} · p.{d.page_number}
                  {d.code_name && <span className="ctx-drop__code">{d.code_name}</span>}
                </div>
                <div className="ctx-drop__reason">{d.reason}</div>
              </div>
            ))
          )}

          <div className="ctx-section-title">Used — in scope</div>
          {kept.map((s, i) => (
            <div className="ctx-keep" key={i}>
              <div className="ctx-keep__clause">
                Clause {s.clause} · p.{s.page}
                {s.code_name && <span className="ctx-drop__code">{s.code_name}</span>}
              </div>
              {s.scope_condition && (
                <div className="ctx-keep__scope">{s.scope_condition}</div>
              )}
            </div>
          ))}
        </>
      )}
    </aside>
  );
}

function ChatApp() {
  const { user, signOut } = useAuth();
  const [conversationId, setConversationId] = useState(uuid());
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [vessel, setVessel] = useState(null);
  const [showVesselForm, setShowVesselForm] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [mode, setMode] = useState("ask"); // "ask" | "compare"
  const scrollRef = useRef(null);

  // Last question asked, so switching vessel can re-run it without retyping.
  const lastQuestionRef = useRef(null);

  async function refreshConversations() {
    setConversations(await storage.listConversations(user.id));
  }

  useEffect(() => {
    refreshConversations();
    api
      .getVessel()
      .then(setVessel)
      .catch(() => setVessel(null));
  }, [user.id]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function startNewConversation() {
    setConversationId(uuid());
    setMessages([]);
    setError(null);
  }

  async function openConversation(conv) {
    setConversationId(conv.id);
    setMessages(await storage.loadConversation(user.id, conv.id));
    setError(null);
  }

  async function removeConversation(id, e) {
    e.stopPropagation();
    await storage.deleteConversation(user.id, id);
    await refreshConversations();
    if (id === conversationId) startNewConversation();
  }

  async function persist(finalMessages) {
    if (finalMessages.length === 0) return;
    const title = finalMessages[0].content.slice(0, 45);
    await storage.saveConversation(user.id, user.email, conversationId, title, finalMessages);
    await refreshConversations();
  }

  async function ask(question, { replaceThread = false } = {}) {
    if (!question.trim() || loading) return;
    setError(null);
    lastQuestionRef.current = question;

    const userMsg = { role: "user", content: question };
    const base = replaceThread ? [] : messages;
    const withUser = [...base, userMsg];
    setMessages(withUser);
    setInput("");
    setLoading(true);

    const start = performance.now();
    try {
      const result = await api.ask(question);
      const elapsed = (performance.now() - start) / 1000;
      const topScore = result.sources?.[0]?.score ?? 0;

      const assistantMsg = {
        role: "assistant",
        content: result.answer,
        sources: result.sources,
        verdict: result.verdict,
        verdictGuard: result.verdict_guard,
        modelUsed: result.model_used,
        filteredOut: result.filtered_out ?? [],
        filteringActive: result.filtering_active,
        codesSearched: result.codes_searched ?? [],
        vessel: result.vessel,
        topScore,
        elapsed,
        fromCache: result.from_cache,
        verified: result.verified,
      };
      const finalMessages = [...withUser, assistantMsg];
      setMessages(finalMessages);
      await persist(finalMessages);
    } catch (e) {
      setError(`Something went wrong: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Save a new vessel, then immediately re-ask the last question against it.
   *
   * The re-ask is the demonstration: same words, same corpus, different
   * binding clauses. Answering from cache would undermine it, but the cache is
   * partitioned by vessel scope so a switched vessel is always a genuine miss.
   */
  async function switchVessel(profile) {
    setSwitching(true);
    setError(null);
    try {
      const saved = await api.saveVessel(profile);
      setVessel(saved);
      setShowVesselForm(false);
      if (lastQuestionRef.current) {
        await ask(lastQuestionRef.current, { replaceThread: true });
      }
    } catch (e) {
      setError(`Could not switch vessel: ${e.message}`);
    } finally {
      setSwitching(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    ask(input);
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">⚓ OceanGRC</div>
          <div className="brand-sub">SPVC 2025 · Workboat Code Ed 3 — Beta reference tool</div>
        </div>
        <button className="new-conv" onClick={startNewConversation}>
          ＋ New conversation
        </button>

        <div className="sidebar-heading">Recent conversations</div>
        <div className="conv-list">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`conv-item ${c.id === conversationId ? "active" : ""}`}
              onClick={() => openConversation(c)}
            >
              <span className="conv-title">{c.title || "Untitled"}</span>
              <button className="conv-del" onClick={(e) => removeConversation(c.id, e)}>
                ×
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <div className="conv-empty">No conversations yet</div>
          )}
        </div>

        <div className="sidebar-user">
          <span className="sidebar-user-email">{user.email}</span>
          <button className="sidebar-signout" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="main-inner">
          <h1 className="page-title">Ask the Code — answered for your vessel</h1>
          <p className="page-sub">
            SPVC 2025 and Workboat Code Edition 3. Clauses that cannot bind your vessel are
            removed before the answer is written.
          </p>

          <div className="mode-tabs">
            <button
              className={`mode-tab${mode === "ask" ? " active" : ""}`}
              onClick={() => setMode("ask")}
            >
              Ask
            </button>
            <button
              className={`mode-tab${mode === "compare" ? " active" : ""}`}
              onClick={() => setMode("compare")}
            >
              Compare codes
            </button>
            <button
              className={`mode-tab${mode === "record" ? " active" : ""}`}
              onClick={() => setMode("record")}
            >
              Record
            </button>
          </div>

          <div className="ctx-bar">
            <VesselBadge vessel={vessel} onEdit={() => setShowVesselForm((v) => !v)} />
            <VesselSwitcher vessel={vessel} onSwitch={switchVessel} busy={switching || loading} />
            <button
              className={`ctx-toggle${debugMode ? " active" : ""}`}
              onClick={() => setDebugMode((d) => !d)}
            >
              {debugMode ? "◧ Context on" : "◧ Show context"}
            </button>
          </div>

          {showVesselForm && (
            <VesselProfile
              compact
              onSaved={(saved) => {
                setVessel(saved);
                setShowVesselForm(false);
              }}
            />
          )}

          {switching && (
            <div className="ctx-switching">
              Re-running your last question against the new vessel…
            </div>
          )}

          {mode === "compare" && <CompareCodes vessel={vessel} />}
          {mode === "record" && <ComplianceRecord />}

          <div className="thread" hidden={mode !== "ask"}>
            {messages.map((m, i) => (
              <ChatMessage key={i} msg={m} />
            ))}
            {loading && (
              <div className="msg-row assistant">
                <div className="avatar">⚓</div>
                <div className="msg-bubble">
                  <div className="typing">Searching the Code…</div>
                </div>
              </div>
            )}
            {error && <div className="error-banner">{error}</div>}
            <div ref={scrollRef} />
          </div>

          <form className="input-row" onSubmit={handleSubmit} hidden={mode !== "ask"}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. How often must I run fire drills?"
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              ↑
            </button>
          </form>
        </div>
      </main>

      {debugMode && (
        <ContextDebugPanel
          msg={[...messages].reverse().find((m) => m.role === "assistant")}
          vessel={vessel}
          onClose={() => setDebugMode(false)}
        />
      )}
    </div>
  );
}

function Gate() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="auth-loading">Loading…</div>;
  }

  return user ? <ChatApp /> : <Login />;
}

const MARKETING_ROUTES = {
  "/": Home,
  "/solution": Solution,
  "/documents": Documents,
  "/pricing": Pricing,
  "/faq": FAQ,
  "/demo": Demo,
};

function MarketingSite() {
  const { path } = useRoute();
  const Page = MARKETING_ROUTES[path] || Home;

  return (
    <div className="mkt-page">
      <Nav />
      <Page />
      <Footer />
    </div>
  );
}

function Site() {
  const { path } = useRoute();

  if (path === "/app") {
    return (
      <AuthProvider>
        <Gate />
      </AuthProvider>
    );
  }

  return <MarketingSite />;
}

export default function App() {
  return (
    <RouterProvider>
      <Site />
    </RouterProvider>
  );
}