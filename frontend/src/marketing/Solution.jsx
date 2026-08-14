import { Link } from "../lib/router";

const OLD_VS_NEW = [
  {
    old: "You get the clause text and work out yourself whether it binds your vessel.",
    new: "Clauses that cannot bind your vessel are removed before the answer is written.",
  },
  {
    old: "You restate the length and area category in every question, and hope you remembered.",
    new: "The vessel is held once and applied to every question automatically.",
  },
  {
    old: "One code per tool. Comparing regimes means reading both documents side by side.",
    new: "One question across SPVC 2025 and Workboat Code Edition 3, answered as a difference.",
  },
  {
    old: "A confident answer whether or not the source exists.",
    new: "An explicit refusal that names where the answer actually sits.",
  },
];

const BENEFITS = [
  {
    title: "Applicability, not search",
    body: "Requirements carry machine-readable scope — length bounds, area categories, passenger thresholds — parsed from the Code's own wording and inherited down the clause hierarchy.",
  },
  {
    title: "Defensible on paper",
    body: "Verbatim clause text with number and page, so what you file is the Code's language rather than a paraphrase of it.",
  },
  {
    title: "Cross-code by design",
    body: "Retrieval sets are kept separate per code, so a difference claim is grounded in both documents rather than blended into one answer.",
  },
  {
    title: "Conservative by construction",
    body: "A clause is excluded only on an explicit, parsed conflict. Anything ambiguous is kept — hiding a binding clause is the one failure that cannot be recovered from.",
  },
];

export default function Solution() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">How it works</div>
          <h1 className="mkt-h1">A librarian finds the page. A colleague knows your boat.</h1>
          <p className="mkt-hero-sub">
            Ask a general compliance tool how often you need fire drills and it reads you the clause.
            Correct, and incomplete — you still have to establish whether that clause binds an 11.8m
            Category 2 vessel carrying eight passengers. OceanGRC answers that part first.
          </p>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Before / after</div>
            <h2 className="mkt-h2">Regulatory search vs. applicability</h2>
          </div>
          <div className="mkt-compare">
            <div className="mkt-compare-col mkt-compare-old">
              <div className="mkt-compare-heading">A search tool over the Code</div>
              {OLD_VS_NEW.map((r, i) => (
                <div className="mkt-compare-row" key={`old-${i}`}>
                  {r.old}
                </div>
              ))}
            </div>
            <div className="mkt-compare-col mkt-compare-new">
              <div className="mkt-compare-heading">OceanGRC</div>
              {OLD_VS_NEW.map((r, i) => (
                <div className="mkt-compare-row" key={`new-${i}`}>
                  {r.new}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mkt-section mkt-section-alt">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Under the hood</div>
            <h2 className="mkt-h2">Where the intelligence actually lives</h2>
          </div>
          <div className="mkt-flow">
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">1. Parsed clause by clause</div>
              <div className="mkt-flow-body">
                Each code is split into clause-level chunks carrying its clause number, section and
                page. Contents pages and parser artefacts are removed so they can never be retrieved
                as if they were statutory content.
              </div>
            </div>
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">2. Scope conditions extracted</div>
              <div className="mkt-flow-body">
                Phrases like "vessels of less than 12 metres" and "area category of operation 0 or 1"
                are parsed into structured bounds and inherited from parent clauses to children —
                deterministically, so every exclusion is reproducible and auditable rather than a
                model's opinion.
              </div>
            </div>
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">3. Filtered before generation</div>
              <div className="mkt-flow-body">
                Retrieval scores the whole corpus, then removes clauses that conflict with your
                vessel, then takes the top results. Out-of-scope clauses never occupy a slot, so the
                model is never in a position to cite one.
              </div>
            </div>
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">4. Answered, cited, checked</div>
              <div className="mkt-flow-body">
                The answer is written only from the surviving clauses, in a fixed three-part format:
                verdict, statutory anchor, verbatim extract. Every citation is verified against what
                was actually retrieved. Where a table's structure was lost in extraction, the answer
                says so instead of inferring the value.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Design principles</div>
            <h2 className="mkt-h2">Built to be checked, not trusted blindly</h2>
          </div>
          <div className="mkt-grid mkt-grid-4">
            {BENEFITS.map((b) => (
              <div className="mkt-card mkt-card-plain" key={b.title}>
                <div className="mkt-card-title">{b.title}</div>
                <div className="mkt-card-body">{b.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Set a vessel and see the answer change.</h2>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Start free
            </Link>
            <Link to="/documents" className="mkt-btn mkt-btn-ghost-invert mkt-btn-lg">
              Codes covered
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
