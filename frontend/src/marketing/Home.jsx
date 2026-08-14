import { Link } from "../lib/router";

const FEATURES = [
  {
    icon: "🎯",
    title: "Filtered to your vessel",
    body: "Enter length, area category, passenger count and build once. Clauses that cannot bind your vessel are removed before the answer is written — not mentioned and then dismissed.",
  },
  {
    icon: "⚖️",
    title: "One question, several codes",
    body: "Ask across SPVC 2025 and Workboat Code Edition 3 at once. See exactly what changes for your vessel between them — the question a single-code tool cannot answer.",
  },
  {
    icon: "📎",
    title: "The clause, not a summary",
    body: "Every answer returns the governing clause verbatim with its number and page, formatted to paste straight into a design justification note.",
  },
  {
    icon: "🛑",
    title: "It tells you when it doesn't know",
    body: "When the answer sits in the Regulations, in a licensed ISO standard, or in Certifying Authority discretion, it says so and names where. It does not guess.",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Set your vessel",
    body: "Length overall, area category of operation, vessel type, hull material, passengers. Thirty seconds, once.",
  },
  {
    n: "02",
    title: "Ask in plain English",
    body: "No need to restate the vessel, and no need to know the clause number. Ask the way you'd ask a colleague.",
  },
  {
    n: "03",
    title: "Get a binding verdict",
    body: "A direct applicability verdict for your vessel, the exact statutory anchor, and the Code's own words underneath it.",
  },
];

const AUDIENCES = [
  {
    title: "Naval architects & designers",
    body: "Know which requirements bind a hull before it is built — and what changes if the length crosses a threshold.",
  },
  {
    title: "Marine surveyors",
    body: "Find the governing clause during an examination, with the page reference you can show the owner.",
  },
  {
    title: "Compliance consultants",
    body: "Run an Edition 2 to Edition 3 gap check against a specific vessel instead of reading both codes side by side.",
  },
  {
    title: "Certifying Authorities",
    body: "Cross-check a determination quickly, with the source text quoted rather than paraphrased.",
  },
];

export default function Home() {
  return (
    <>
      <section className="mkt-hero">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">
            Workboat Code Edition 3 · Transitional deadline 13 December 2026
          </div>
          <h1 className="mkt-h1">
            Not what the Code says.
            <br />
            What binds <em>your</em> vessel.
          </h1>
          <p className="mkt-hero-sub">
            Most compliance tools read the regulation back to you and leave you to work out whether
            it applies. OceanGRC holds your vessel's verified specification and filters every answer
            to the clauses that can actually bind it — across SPVC 2025 and Workboat Code Edition 3.
          </p>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Start free
            </Link>
            <Link to="/solution" className="mkt-btn mkt-btn-ghost mkt-btn-lg">
              See how it works
            </Link>
          </div>
          <div className="mkt-hero-stats">
            <div className="mkt-stat">
              <div className="mkt-stat-num">2</div>
              <div className="mkt-stat-label">MCA codes indexed</div>
            </div>
            <div className="mkt-stat">
              <div className="mkt-stat-num">3,449</div>
              <div className="mkt-stat-label">Clauses scope-tagged</div>
            </div>
            <div className="mkt-stat">
              <div className="mkt-stat-num">100%</div>
              <div className="mkt-stat-label">Answers cited to a clause</div>
            </div>
          </div>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">What makes it different</div>
            <h2 className="mkt-h2">
              A search tool finds the clause. This one works out whether it applies.
            </h2>
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
            <h2 className="mkt-h2">Set the vessel once. Every answer narrows to it.</h2>
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
            <h2 className="mkt-h2">Built for the people who sign off the decision</h2>
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

      <section className="mkt-section mkt-section-alt">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">The deadline</div>
            <h2 className="mkt-h2">13 December 2026</h2>
          </div>
          <div className="mkt-note">
            Workboat Code Edition 3 came into force on 13 December 2023 under the Merchant Shipping
            (Small Workboats and Pilot Boats) Regulations 2023. Transitional arrangements end on{" "}
            <strong>13 December 2026</strong> — vessels certificated under the Brown Code, the MGN
            280(M) technical annex, or Workboat Code Edition 2 Amendment 1 must meet Edition 3 by
            their next renewal examination or by that date. Ask what changes for a specific vessel,
            and get the clause that governs it.
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Ask it something you already know the answer to.</h2>
          <p className="mkt-cta-sub">
            That is how a professional decides whether to trust a tool. Set your vessel, ask fifteen
            questions free, and check the citations yourself. No card required.
          </p>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Start free
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
