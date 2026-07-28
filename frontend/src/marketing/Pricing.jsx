import { Link } from "../lib/router";

const TIERS = [
  {
    name: "Free",
    price: "£0",
    period: "",
    tagline: "Try it before you rely on it.",
    cta: "Try it free",
    features: [
      "20 questions / month",
      "Full clause citations",
      "Confidence scoring",
      "1 user, conversation history",
      "Community support",
    ],
  },
  {
    name: "Starter",
    price: "£29",
    period: "/ month",
    tagline: "For skippers, small operators & training providers.",
    cta: "Start Starter",
    highlight: true,
    features: [
      "Unlimited questions",
      "Full clause citations",
      "Confidence scoring",
      "1 seat, full conversation history",
      "Email support",
    ],
  },
  {
    name: "Professional",
    price: "£89",
    period: "/ seat / month",
    tagline: "For surveyors, Certifying Authorities & brokers.",
    cta: "Start Professional",
    features: [
      "Everything in Starter",
      "Up to 10 team seats",
      "Export & audit trail",
      "Usage analytics",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    tagline: "For fleets, MCA-approved bodies & training organisations.",
    cta: "Talk to us",
    features: [
      "Everything in Professional",
      "SSO",
      "Custom document ingestion",
      "Uptime SLA",
      "Dedicated support",
    ],
  },
];

export default function Pricing() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">Pricing — draft for review</div>
          <h1 className="mkt-h1">Simple plans, priced to match how you use it</h1>
          <p className="mkt-hero-sub">
            No card required for Free. Cancel anytime on paid plans.
          </p>
        </div>
      </section>

      <div className="mkt-section-inner mkt-draft-banner">
        <strong>Draft pricing.</strong> Figures below are placeholders for internal review — confirm
        before publishing externally.
      </div>

      <section className="mkt-section mkt-pricing-section">
        <div className="mkt-section-inner">
          <div className="mkt-grid mkt-grid-4 mkt-pricing-grid">
            {TIERS.map((t) => (
              <div className={`mkt-price-card ${t.highlight ? "mkt-price-highlight" : ""}`} key={t.name}>
                {t.highlight && <div className="mkt-price-badge">Most popular</div>}
                <div className="mkt-price-name">{t.name}</div>
                <div className="mkt-price-tagline">{t.tagline}</div>
                <div className="mkt-price-amount">
                  {t.price}
                  <span className="mkt-price-period">{t.period}</span>
                </div>
                <ul className="mkt-price-features">
                  {t.features.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
                <Link
                  to="/app"
                  className={`mkt-btn ${t.highlight ? "mkt-btn-primary" : "mkt-btn-ghost"} mkt-price-cta`}
                >
                  {t.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-section mkt-section-alt">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Billing</div>
            <h2 className="mkt-h2">A few things worth knowing</h2>
          </div>
          <div className="mkt-grid mkt-grid-2">
            <div className="mkt-card mkt-card-plain">
              <div className="mkt-card-title">No lock-in</div>
              <div className="mkt-card-body">Monthly billing on Starter and Professional — upgrade, downgrade, or cancel any time.</div>
            </div>
            <div className="mkt-card mkt-card-plain">
              <div className="mkt-card-title">Enterprise is custom</div>
              <div className="mkt-card-body">Seats, SLA, and custom document ingestion are scoped per organisation — talk to us for a quote.</div>
            </div>
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Start on Free, upgrade when you need to.</h2>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Try it free
            </Link>
            <Link to="/faq" className="mkt-btn mkt-btn-ghost-invert mkt-btn-lg">
              Read the FAQ
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
