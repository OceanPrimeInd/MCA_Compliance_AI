import { useState, useEffect, Fragment } from "react";
import { Link } from "../lib/router";
import Markdown from "../lib/markdown";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const VERDICT_LABEL = {
  REQUIRED: "Required",
  NOT_REQUIRED: "Not required",
  CONDITIONAL: "Conditional",
  NOT_ESTABLISHED: "Not established",
};

/**
 * Public, un-gated demo.
 *
 * Side-by-side is the default because the headline promises a comparison, and
 * a single answer cannot show one. Both vessels are asked at once and the
 * clauses whose scope status actually CHANGED between them are marked — that
 * mark is the proof, and it is derived from the engine's real output rather
 * than animated for effect.
 */
export default function Demo() {
  const [openScope, setOpenScope] = useState({}); // { [vesselKey]: "in" | "out" | null }
  const [vessels, setVessels] = useState([]);
  const [suggested, setSuggested] = useState([]);
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [remaining, setRemaining] = useState(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/demo/vessels`)
      .then((r) => r.json())
      .then((d) => {
        setVessels(d.vessels);
        setSuggested(d.suggested_questions);
        setRemaining(d.remaining_today);
      })
      .catch(() => setError("Could not reach the compliance engine."));
  }, []);

  async function askOne(text, vesselKey) {
    const res = await fetch(`${BACKEND_URL}/demo/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, vessel_key: vesselKey }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
    return body;
  }

  async function compare(q) {
    const text = (q ?? question).trim();
    if (!text || !vessels.length) return;
    setQuestion(text);
    setError(null);
    setLoading(true);
    setResults(null);
    try {
      const answered = await Promise.all(
        vessels.map(async (v) => [v.key, await askOne(text, v.key)])
      );
      const byKey = Object.fromEntries(answered);
      setResults(byKey);
      const last = answered[answered.length - 1][1];
      setRemaining(last.remaining_today);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  /**
   * A clause's scope status for one vessel.
   * "in" = used, "out" = excluded by the filter, null = never retrieved.
   */
  function statusOf(result, clause) {
    if (result.sources.some((s) => String(s.clause) === clause)) return "in";
    const dropped = result.filtered_out.find((f) => String(f.clause_number) === clause);
    return dropped ? "out" : null;
  }

  /** Clauses whose status genuinely differs between the two vessels. */
  function flippedClauses() {
    if (!results || vessels.length < 2) return new Set();
    const [a, b] = vessels.map((v) => results[v.key]);
    if (!a || !b) return new Set();

    const all = new Set();
    [a, b].forEach((r) => {
      r.sources.forEach((s) => s.clause && all.add(String(s.clause)));
      r.filtered_out.forEach((f) => f.clause_number && all.add(String(f.clause_number)));
    });

    const flipped = new Set();
    all.forEach((clause) => {
      const sa = statusOf(a, clause);
      const sb = statusOf(b, clause);
      if (sa && sb && sa !== sb) flipped.add(clause);
    });
    return flipped;
  }

  function toggleScope(vesselKey, which) {
    setOpenScope((prev) => ({
      ...prev,
      [vesselKey]: prev[vesselKey] === which ? null : which,
    }));
  }

  const flipped = flippedClauses();

  return (
    <section className="demo">
      <div className="demo__inner">
        <div className="mkt-eyebrow">Live demo — no sign-up</div>
        <h1 className="mkt-h1 demo__title">Same question. Different vessel. Different law.</h1>
        <p className="demo__lede">
          Ask once. Both vessels are checked against SPVC 2025 and Workboat Code Edition 3, and
          you see exactly which provisions bind each one — and which were removed, with the
          reason.
        </p>

        <div className="demo__vessels demo__vessels--static">
          {vessels.map((v) => (
            <div className="demo__vessel-card" key={v.key}>
              <span className="demo__vessel-label">{v.label}</span>
              <span className="demo__vessel-sub">
                {v.vessel_type} · {(v.hull_material || "").toUpperCase()}
              </span>
            </div>
          ))}
        </div>

        <form
          className="demo__form"
          onSubmit={(e) => {
            e.preventDefault();
            compare();
          }}
        >
          <input
            type="text"
            value={question}
            maxLength={300}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about construction, stability, LSA, radio, manning…"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !question.trim()}>
            {loading ? "Checking both…" : "Compare vessels"}
          </button>
        </form>

        <div className="demo__suggested">
          {suggested.map((s) => (
            <button key={s} className="demo__chip" onClick={() => compare(s)} disabled={loading}>
              {s}
            </button>
          ))}
        </div>

        {error && <div className="demo__error">{error}</div>}

        {loading && (
          <div className="demo__loading">Checking both vessels against both codes…</div>
        )}

        {results && flipped.size > 0 && (
          <div className="demo__flip-banner">
            <strong>{flipped.size}</strong> provision{flipped.size === 1 ? "" : "s"} changed
            status between these two vessels — marked{" "}
            <span className="demo__flip-tag">changed</span> below. Same question, same codes,
            different binding law.
          </div>
        )}

        {results && (
          <div className="demo__grid">
            {vessels.map((v) => {
              const r = results[v.key];
              if (!r) return null;
              const verdict = r.verdict;
              return (
                <div className="demo__panel" key={v.key}>
                  <div className="demo__panel-head">{v.label}</div>

                  {verdict && (
                    <div className={`demo__verdict demo__verdict--${verdict.status.toLowerCase()}`}>
                      <span className="demo__verdict-tag">
                        {VERDICT_LABEL[verdict.status] || verdict.status}
                      </span>
                      <span className="demo__verdict-text">{verdict.summary}</span>
                    </div>
                  )}

                  <div className="demo__scope">
                    <button
                      className={`demo__scope-stat demo__scope-stat--out${
                        openScope[v.key] === "out" ? " open" : ""
                      }`}
                      onClick={() => toggleScope(v.key, "out")}
                    >
                      <b>{r.filtered_out.length}</b>
                      <span>filtered out — out of scope</span>
                    </button>
                    <button
                      className={`demo__scope-stat demo__scope-stat--in${
                        openScope[v.key] === "in" ? " open" : ""
                      }`}
                      onClick={() => toggleScope(v.key, "in")}
                    >
                      <b>{r.sources.length}</b>
                      <span>in scope — considered</span>
                    </button>
                  </div>

                  {openScope[v.key] === "out" && (
                    <div className="demo__clause-list">
                      {r.filtered_out.length === 0 && (
                        <div className="demo__ctx-empty">
                          Nothing conflicted with this vessel's specification.
                        </div>
                      )}
                      {r.filtered_out.map((f, i) => (
                        <div
                          className={`demo__drop${
                            flipped.has(String(f.clause_number)) ? " flipped" : ""
                          }`}
                          key={i}
                        >
                          <div className="demo__drop-clause">
                            Clause {f.clause_number} · p.{f.page_number}
                            {flipped.has(String(f.clause_number)) && (
                              <span className="demo__flip-tag">changed</span>
                            )}
                          </div>
                          <div className="demo__drop-reason">{f.reason}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {openScope[v.key] === "in" && (
                    <div className="demo__clause-list">
                      {r.sources.length === 0 && (
                        <div className="demo__ctx-empty">No provision met the threshold.</div>
                      )}
                      {r.sources.map((s, i) => (
                        <div
                          className={`demo__keep${
                            flipped.has(String(s.clause)) ? " flipped" : ""
                          }`}
                          key={i}
                        >
                          <div className="demo__drop-clause">
                            Clause {s.clause} · p.{s.page}
                            {flipped.has(String(s.clause)) && (
                              <span className="demo__flip-tag">changed</span>
                            )}
                          </div>
                          <div className="demo__keep-scope">{s.scope_condition}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <Markdown text={r.answer} className="demo__answer" />

                  {r.execution && (
                    <div className="demo__prov">
                      <div className="demo__prov-head">
                        Execution provenance
                        <span
                          className="demo__prov-info"
                          tabIndex={0}
                          role="note"
                          aria-label="Identifies this run and pins the exact code versions used. Demo runs are not stored; signed-in determinations are written to an append-only record."
                          data-tip="Identifies this run and pins the exact corpus and engine versions that produced it, so the determination can be reproduced. Demo runs are not stored — signed-in determinations are written to an append-only compliance record."
                        >
                          i
                        </span>
                      </div>
                      <dl>
                        <dt>Execution</dt>
                        <dd>{r.execution.execution_id}</dd>
                        <dt>Run at</dt>
                        <dd>{r.execution.executed_at.replace("T", " ").replace("+00:00", " UTC")}</dd>
                        {Object.entries(r.execution.corpus_fingerprints || {}).map(([code, fp]) => (
                          <Fragment key={code}>
                            <dt>{code}</dt>
                            <dd>{fp}</dd>
                          </Fragment>
                        ))}
                        <dt>Engine</dt>
                        <dd>{r.execution.pipeline_version}</dd>
                      </dl>
                      <p className="demo__prov-note">
                        Demo runs are not persisted. Signed-in determinations are written to an
                        append-only compliance record with the same fingerprints.
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {remaining !== null && remaining < 30 && (
          <div className="demo__budget">
            {remaining > 0
              ? `${remaining} demo questions left today.`
              : "Today's shared demo budget is used up."}{" "}
            <Link to="/app">Create a free account</Link> to keep going.
          </div>
        )}

        <div className="demo__cta">
          <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
            Set your own vessel — free
          </Link>
          <Link to="/solution" className="mkt-btn mkt-btn-ghost mkt-btn-lg">
            How it works
          </Link>
        </div>
      </div>
    </section>
  );
}
