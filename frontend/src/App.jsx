import { useState, useEffect, useRef } from "react";
import * as storage from "./lib/storage";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const EXAMPLES = [
  "Do I need a kill cord on my rigid inflatable boat?",
  "How many liferafts do I need for 20 passengers in area category 1?",
  "Can I operate my vessel single-handed?",
];

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
          <span className="chip" key={i}>
            <span className="chip-dot" style={{ background: scoreColor(s.score) }} />
            {s.clause} · p.{s.page}
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
                Clause {s.clause} — p.{s.page} (relevance {s.score.toFixed(2)})
              </div>
              <div className="cited-text">{s.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusRow({ elapsed, fromCache, verified }) {
  return (
    <div className="status-row">
      <span className="badge badge-time">{elapsed.toFixed(1)}s</span>
      {fromCache && <span className="badge badge-cache">⚡ cached</span>}
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
        <p>{msg.content}</p>
        {msg.role === "assistant" && msg.sources && (
          <>
            <SourceChips sources={msg.sources} />
            {msg.topScore < 0.45 && (
              <div className="low-confidence">
                ⚠ Weak match to the Code — verify with the MCA or a Certifying Authority.
              </div>
            )}
            <StatusRow elapsed={msg.elapsed} fromCache={msg.fromCache} verified={msg.verified} />
          </>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [conversationId, setConversationId] = useState(uuid());
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    setConversations(storage.listConversations());
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function startNewConversation() {
    setConversationId(uuid());
    setMessages([]);
    setError(null);
  }

  function openConversation(conv) {
    setConversationId(conv.id);
    setMessages(storage.loadConversation(conv.id));
    setError(null);
  }

  function removeConversation(id, e) {
    e.stopPropagation();
    storage.deleteConversation(id);
    setConversations(storage.listConversations());
    if (id === conversationId) startNewConversation();
  }

  function persist(finalMessages) {
    if (finalMessages.length === 0) return;
    const title = finalMessages[0].content.slice(0, 45);
    storage.saveConversation(conversationId, title, finalMessages);
    setConversations(storage.listConversations());
  }

  async function ask(question) {
    if (!question.trim() || loading) return;
    setError(null);
    const userMsg = { role: "user", content: question };
    const withUser = [...messages, userMsg];
    setMessages(withUser);
    setInput("");
    setLoading(true);

    const start = performance.now();
    try {
      const res = await fetch(`${BACKEND_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        throw new Error(`${res.status} ${res.statusText}`);
      }
      const result = await res.json();
      const elapsed = (performance.now() - start) / 1000;
      const topScore = result.sources?.[0]?.score ?? 0;

      const assistantMsg = {
        role: "assistant",
        content: result.answer,
        sources: result.sources,
        topScore,
        elapsed,
        fromCache: result.from_cache,
        verified: result.verified,
      };
      const finalMessages = [...withUser, assistantMsg];
      setMessages(finalMessages);
      persist(finalMessages);
    } catch (e) {
      setError(`Something went wrong: ${e.message}`);
    } finally {
      setLoading(false);
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
          <div className="brand-title">⚓ MCA Compliance AI</div>
          <div className="brand-sub">SPVC 2025 — Beta reference tool</div>
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

        <div className="sidebar-footer">
          Answers are generated from the Code and are not a substitute for advice from the
          MCA or a Certifying Authority.
        </div>
      </aside>

      <main className="main">
        <div className="main-inner">
          <h1 className="page-title">Ask about the Sport or Pleasure Vessel Code</h1>
          <p className="page-sub">
            Ask a question in plain English — every answer is cited against the Code.
          </p>

          {messages.length === 0 && (
            <div className="examples">
              {EXAMPLES.map((ex) => (
                <button key={ex} className="example-btn" onClick={() => ask(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          )}

          <div className="thread">
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

          <form className="input-row" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about the SPVC..."
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              ↑
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
