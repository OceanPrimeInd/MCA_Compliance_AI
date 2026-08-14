import { useState, useEffect } from "react";
import { api } from "../lib/api";

/**
 * The Compliance Record.
 *
 * Not a chat history. A dated, append-only account of which provisions were
 * relied on and which were excluded, against which corpus version — the thing
 * a professional carrying PI liability actually needs when a decision is
 * questioned two years later.
 *
 * The impact search is the reason the record exists: when a clause changes,
 * it answers "which of my past decisions rested on it?" — a question a tool
 * that only answers questions cannot address at any price.
 */
export default function ComplianceRecord() {
  const [records, setRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [note, setNote] = useState(null);
  const [impactQuery, setImpactQuery] = useState("");
  const [impact, setImpact] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listProvenance()
      .then((d) => {
        setRecords(d.records);
        setSummary(d.summary);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function showNote(id) {
    setBusy(true);
    try {
      const d = await api.designNote(id);
      setNote({ id, text: d.design_note });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runImpact(e) {
    e.preventDefault();
    const clauses = impactQuery
      .split(/[,\s]+/)
      .map((c) => c.trim())
      .filter(Boolean);
    if (!clauses.length) return;
    setBusy(true);
    try {
      setImpact(await api.impact(clauses));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rec">
      <div className="rec__head">
        <h2>Compliance record</h2>
        <p>
          Every determination, with the clauses relied on, the clauses excluded and why, and
          the corpus version it was decided against.
        </p>
      </div>

      {summary && (
        <div className="rec__summary">
          <div className="rec__stat">
            <b>{summary.decisions_recorded}</b>
            <span>determinations</span>
          </div>
          <div className="rec__stat">
            <b>{summary.unverified_citations}</b>
            <span>unverified citations</span>
          </div>
          {summary.first_recorded && (
            <div className="rec__stat rec__stat--wide">
              <b>{summary.first_recorded.slice(0, 10)}</b>
              <span>record begins</span>
            </div>
          )}
        </div>
      )}

      <form className="rec__impact-form" onSubmit={runImpact}>
        <label>A clause changed — what does it affect?</label>
        <div className="rec__impact-row">
          <input
            value={impactQuery}
            onChange={(e) => setImpactQuery(e.target.value)}
            placeholder="e.g. 5.6.3.1, 8.3.2"
          />
          <button type="submit" disabled={busy || !impactQuery.trim()}>
            Check impact
          </button>
        </div>
      </form>

      {impact && (
        <div className={`rec__impact${impact.affected_count ? " hit" : ""}`}>
          {impact.affected_count === 0 ? (
            <>No past determination relied on {impact.queried_clauses.join(", ")}.</>
          ) : (
            <>
              <strong>
                {impact.affected_count} past determination
                {impact.affected_count === 1 ? "" : "s"} relied on{" "}
                {impact.queried_clauses.join(", ")}
              </strong>
              {impact.affected.map((a) => (
                <div className="rec__impact-item" key={a.id}>
                  #{a.id} · {a.asked_at.slice(0, 10)} — {a.question}
                  {a.vessel && (
                    <span className="rec__impact-vessel">
                      {a.vessel.length_overall}m · Cat {a.vessel.area_category}
                    </span>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {error && <div className="rec__error">{error}</div>}

      {records.length === 0 && !error && (
        <div className="rec__empty">
          No determinations recorded yet. Ask a question and it will appear here.
        </div>
      )}

      {records.map((r) => (
        <div className="rec__item" key={r.id}>
          <div className="rec__item-head">
            <span className="rec__item-id">#{r.id}</span>
            <span className="rec__item-date">{r.asked_at.replace("T", " ").slice(0, 16)}</span>
            {r.vessel && (
              <span className="rec__item-vessel">
                {r.vessel.length_overall}m · Cat {r.vessel.area_category}
              </span>
            )}
            {!r.citations_verified && <span className="rec__warn">⚠ unverified</span>}
            <button className="rec__note-btn" onClick={() => showNote(r.id)} disabled={busy}>
              Design note
            </button>
          </div>
          <div className="rec__item-q">{r.question}</div>
          <div className="rec__item-clauses">
            <span className="rec__used">{r.clauses_used.length} relied on</span>
            <span className="rec__excl">{r.clauses_excluded.length} excluded</span>
            <span className="rec__fp">
              {Object.entries(r.corpus_fingerprints || {})
                .map(([k, v]) => `${k}@${v}`)
                .join("  ")}
            </span>
          </div>
        </div>
      ))}

      {note && (
        <div className="rec__note-overlay" onClick={() => setNote(null)}>
          <div className="rec__note" onClick={(e) => e.stopPropagation()}>
            <div className="rec__note-head">
              <span>Design note — record #{note.id}</span>
              <button onClick={() => navigator.clipboard?.writeText(note.text)}>Copy</button>
              <button onClick={() => setNote(null)}>✕</button>
            </div>
            <pre>{note.text}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
