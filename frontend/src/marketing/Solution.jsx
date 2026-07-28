import { Link } from "../lib/router";

const OLD_VS_NEW = [
  {
    old: "Ctrl+F through a 100+ page PDF and hope you picked the right keyword.",
    new: "Ask the question in plain English and get pointed straight at the relevant clause.",
  },
  {
    old: "Rely on whoever on the team happens to remember that clause.",
    new: "Every question gets the same, source-grounded answer — every time.",
  },
  {
    old: "No easy way to double-check a colleague's read of the Code.",
    new: "Every answer ships with its citation and a confidence score, so it's auditable on the spot.",
  },
  {
    old: "Get it wrong quietly, find out later.",
    new: "Weak matches are flagged as unverified before you ever act on them.",
  },
];

const BENEFITS = [
  {
    title: "Speed",
    body: "Turn a 10-minute manual lookup into a question typed in plain English and a cited answer back in seconds.",
  },
  {
    title: "Consistency",
    body: "Every answer is grounded in the same indexed Code, so the answer doesn't change depending on who asks or who's answering.",
  },
  {
    title: "Auditability",
    body: "Every response carries the clause number, page, relevance score, and a verified/unverified flag — so you can show your working.",
  },
  {
    title: "Lower risk",
    body: "Low-confidence matches are surfaced explicitly instead of being presented with false confidence.",
  },
];

export default function Solution() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">Why we built it</div>
          <h1 className="mkt-h1">The Code is long. Getting it wrong isn't an option.</h1>
          <p className="mkt-hero-sub">
            The Sport or Pleasure Vessel Code 2025 covers construction, stability, machinery, fire
            safety, radio, and manning — hundreds of clauses deep. Finding the right one by hand is
            slow, and a wrong read has real safety and compliance consequences. Compliance AI turns
            that lookup into a single question.
          </p>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Before / after</div>
            <h2 className="mkt-h2">The old way vs. Compliance AI</h2>
          </div>
          <div className="mkt-compare">
            <div className="mkt-compare-col mkt-compare-old">
              <div className="mkt-compare-heading">Without Compliance AI</div>
              {OLD_VS_NEW.map((r, i) => (
                <div className="mkt-compare-row" key={`old-${i}`}>
                  {r.old}
                </div>
              ))}
            </div>
            <div className="mkt-compare-col mkt-compare-new">
              <div className="mkt-compare-heading">With Compliance AI</div>
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
            <h2 className="mkt-h2">Grounded in the Code — not a general-purpose chatbot</h2>
          </div>
          <div className="mkt-flow">
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">1. Parsed &amp; chunked</div>
              <div className="mkt-flow-body">
                The Sport or Pleasure Vessel Code 2025 is parsed clause by clause and split into
                indexed chunks, each tagged with its clause number and page.
              </div>
            </div>
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">2. Retrieved</div>
              <div className="mkt-flow-body">
                When you ask a question, the system searches that index for the clauses most
                relevant to what you actually asked — this is retrieval-augmented generation (RAG),
                not free-form guessing.
              </div>
            </div>
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">3. Answered &amp; scored</div>
              <div className="mkt-flow-body">
                The answer is generated only from the retrieved clauses, then scored for relevance.
                Scores of 0.6+ show green, 0.45–0.6 show amber, and below 0.45 show red with an
                explicit "weak match" warning.
              </div>
            </div>
            <div className="mkt-flow-step">
              <div className="mkt-flow-title">4. Verified &amp; saved</div>
              <div className="mkt-flow-body">
                Citations are checked against the source text and marked verified or unverified.
                Your conversation is saved securely to your account so you can find it again.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Why teams choose it</div>
            <h2 className="mkt-h2">Built to be checked, not just trusted blindly</h2>
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
          <h2 className="mkt-h2">See it answer your first question.</h2>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Try it free
            </Link>
            <Link to="/documents" className="mkt-btn mkt-btn-ghost-invert mkt-btn-lg">
              What you'll need
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
