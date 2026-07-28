import { Link } from "../lib/router";

const FEATURES = [
  {
    icon: "💬",
    title: "Plain-English answers",
    body: "Ask in your own words instead of scanning a 100+ page code for the clause you need.",
  },
  {
    icon: "📎",
    title: "Clause-level citations",
    body: "Every answer links back to the exact clause and page number it was drawn from — nothing is unsourced.",
  },
  {
    icon: "🟢",
    title: "Confidence scoring",
    body: "A green / amber / red score shows how strong the match to the Code really is, so you know when to double-check.",
  },
  {
    icon: "⚠",
    title: "Verified vs unverified flags",
    body: "Weak matches are flagged automatically, so a shaky answer never quietly passes as a solid one.",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Ask",
    body: "Type your question the way you'd ask a colleague — no keyword-perfect search required.",
  },
  {
    n: "02",
    title: "Retrieve",
    body: "The system searches the indexed Sport or Pleasure Vessel Code 2025 for the clauses that actually answer it.",
  },
  {
    n: "03",
    title: "Verify",
    body: "You get the answer plus the source clauses, page numbers, and a confidence score to sanity-check it yourself.",
  },
];

const AUDIENCES = [
  { title: "Skippers & owners", body: "Check what the Code requires before you buy, refit, or set out." },
  { title: "Training providers", body: "Answer student questions on the spot, with a citation to back it up." },
  { title: "Surveyors & Certifying Authorities", body: "Cross-check clauses quickly during inspections and sign-off." },
  { title: "Brokers & insurers", body: "Get a fast, defensible read on compliance questions during due diligence." },
];

export default function Home() {
  return (
    <>
      <section className="mkt-hero">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">Built for the Sport or Pleasure Vessel Code 2025</div>
          <h1 className="mkt-h1">
            Ask the Code a question.
            <br />
            Get a cited answer in seconds.
          </h1>
          <p className="mkt-hero-sub">
            Compliance AI reads the Sport or Pleasure Vessel Code so you don't have to. Every
            answer comes back with the clause, the page, and a confidence score — so you always
            know how far to trust it.
          </p>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Try it free
            </Link>
            <Link to="/solution" className="mkt-btn mkt-btn-ghost mkt-btn-lg">
              See how it works
            </Link>
          </div>
          <div className="mkt-hero-stats">
            <div className="mkt-stat">
              <div className="mkt-stat-num">100%</div>
              <div className="mkt-stat-label">Answers cited to a clause</div>
            </div>
            <div className="mkt-stat">
              <div className="mkt-stat-num">~2–6s</div>
              <div className="mkt-stat-label">Typical response time</div>
            </div>
            <div className="mkt-stat">
              <div className="mkt-stat-num">2025</div>
              <div className="mkt-stat-label">Code edition indexed</div>
            </div>
          </div>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Why teams use it</div>
            <h2 className="mkt-h2">Everything you need to trust the answer, not just read it</h2>
          </div>
          <div className="mkt-grid mkt-grid-4">
            {FEATURES.map((f) => (
              <div className="mkt-card" key={f.title}>
                <div className="mkt-card-icon">{f.icon}</div>
                <div className="mkt-card-title">{f.title}</div>
                <div className="mkt-card-body">{f.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-section mkt-section-alt">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">How it works</div>
            <h2 className="mkt-h2">Ask, retrieve, verify — every time</h2>
          </div>
          <div className="mkt-steps">
            {STEPS.map((s) => (
              <div className="mkt-step" key={s.n}>
                <div className="mkt-step-n">{s.n}</div>
                <div className="mkt-step-title">{s.title}</div>
                <div className="mkt-step-body">{s.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Who it's for</div>
            <h2 className="mkt-h2">Built around anyone who has to work with the Code</h2>
          </div>
          <div className="mkt-grid mkt-grid-4">
            {AUDIENCES.map((a) => (
              <div className="mkt-card mkt-card-plain" key={a.title}>
                <div className="mkt-card-title">{a.title}</div>
                <div className="mkt-card-body">{a.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Stop digging through the Code by hand.</h2>
          <p className="mkt-cta-sub">
            Sign up, ask your first question, and see the citation and confidence score come back
            — no credit card required.
          </p>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Try it free
            </Link>
            <Link to="/pricing" className="mkt-btn mkt-btn-ghost-invert mkt-btn-lg">
              See pricing
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
