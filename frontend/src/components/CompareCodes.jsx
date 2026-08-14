import { useState, useEffect } from "react";
import { api } from "../lib/api";
import Markdown from "../lib/markdown";

/**
 * Cross-code comparison.
 *
 * The feature a single-code product cannot ship: one question, two codes,
 * answered as a difference for a specific vessel. Requires at least two codes
 * selected, because a comparison of one thing is just an answer.
 */
export default function CompareCodes({ vessel, onResult }) {
  const [codes, setCodes] = useState([]);
  const [selected, setSelected] = useState([]);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .listCodes()
      .then(({ codes }) => {
        const available = codes.filter((c) => c.available);
        setCodes(available);
        // Preselect everything available — comparison is the default intent here.
        setSelected(available.map((c) => c.code_id));
      })
      .catch(() => setError("Could not load the code catalogue."));
  }, []);

  function toggle(codeId) {
    setSelected((prev) =>
      prev.includes(codeId) ? prev.filter((c) => c !== codeId) : [...prev, codeId]
    );
  }

  async function submit(event) {
    event.preventDefault();
    if (selected.length < 2) {
      setError("Select at least two codes to compare.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await api.compare(question, selected);
      setResult(res);
      onResult?.(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="cmp">
      <div className="cmp__head">
        <h2>Compare codes</h2>
        <p>
          One question, answered as a difference between codes — for{" "}
          {vessel
            ? `your ${vessel.length_overall}m Category ${vessel.area_category} vessel`
            : "a general vessel (set a profile for a sharper answer)"}
          .
        </p>
      </div>

      {codes.length > 0 && selected.length < 2 && (
        <div className="cmp__hint">
          Select at least two codes — a comparison of one code is just an answer.
        </div>
      )}

      <div className="cmp__codes">
        {codes.map((c) => (
          <button
            key={c.code_id}
            type="button"
            className={`cmp__code${selected.includes(c.code_id) ? " active" : ""}`}
            onClick={() => toggle(c.code_id)}
          >
            <span className="cmp__code-check">
              {selected.includes(c.code_id) ? "✓" : ""}
            </span>
            {c.short_name}
          </button>
        ))}
        {codes.length === 0 && <div className="cmp__empty">No codes available.</div>}
      </div>

      <form className="cmp__form" onSubmit={submit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What changes for my vessel between these codes?"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim() || selected.length < 2}>
          {loading ? "Comparing…" : "Compare"}
        </button>
      </form>

      {error && <div className="cmp__error">{error}</div>}

      {loading && (
        <div className="cmp__loading">
          <span className="cmp__spinner" aria-hidden="true" />
          Retrieving from {selected.length} codes and comparing… this can take up to a minute
          if the primary model is busy.
        </div>
      )}

      {result && (
        <div className="cmp__result">
          <div className="cmp__result-meta">
            Compared: {result.codes_compared.join(" · ")}
            {result.from_cache && <span className="cmp__cached">⚡ cached</span>}
            <span className={result.verified ? "cmp__ok" : "cmp__warn"}>
              {result.verified ? "✓ citations verified" : "⚠ unverified citation"}
            </span>
          </div>
          <Markdown text={result.answer} className="cmp__answer" />

          {result.sources?.length > 0 && (
            <details className="cmp__sources">
              <summary>{result.sources.length} clauses retrieved</summary>
              {result.sources.map((s, i) => (
                <div className="cmp__source" key={i}>
                  <div className="cmp__source-label">
                    {s.code_name} — Clause {s.clause}, p.{s.page}
                  </div>
                  <div className="cmp__source-text">{s.text}</div>
                </div>
              ))}
            </details>
          )}
        </div>
      )}
    </div>
  );
}
