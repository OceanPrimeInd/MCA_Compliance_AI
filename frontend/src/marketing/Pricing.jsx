import { Link } from "../lib/router";

const TIERS = [
  {
    name: "Free",
    price: "£0",
    period: "",
    tagline: "Satisfy yourself the answers are trustworthy.",
    cta: "Start free",
    features: [
      "15 questions, one-off",
      "Both codes, full applicability filtering",
      "Verbatim clause text with page reference",
      "1 vessel profile",
      "No card required",
    ],
  },
  {
    name: "Practitioner",
    price: "£240",
    period: "/ year",
    tagline: "Sole practitioner or one-person design consultancy.",
    cta: "Start Practitioner",
    highlight: true,
    features: [
      "400 questions / month",
      "Cross-code comparison",
      "Copy as design note",
      "Unlimited vessel profiles",
      "Email support",
    ],
  },
  {
    name: "Practice",
    price: "£600",
    period: "/ year",
    tagline: "Small design practice, two to three architects.",
    cta: "Start Practice",
    features: [
      "1,500 questions / month",
      "3 seats",
      "Shared vessel profiles",
      "Better value per question",
      "Priority email support",
    ],
  },
  {
    name: "Consultancy",
    price: "£1,800",
    period: "/ year",
    tagline: "Multi-seat consultancy, Certifying Authority or builder.",
    cta: "Talk to us",
    features: [
      "6,000 questions / month",
      "10 seats",
      "Export and audit trail",
      "Best value per question",
      "Onboarding session",
    ],
  },
];

export default function Pricing() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">Pricing</div>
          <h1 className="mkt-h1">Priced as a professional reference, not a fleet system.</h1>
          <p className="mkt-hero-sub">
            One person can expense a Practitioner seat without an approval process. Every tier
            includes the full applicability filter and both codes — higher tiers buy volume and
            seats, never better answers.
          </p>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-grid mkt-grid-4">
            {TIERS.map((t) => (
              <div
                className={`mkt-card mkt-price-card${t.highlight ? " mkt-price-card-highlight" : ""}`}
                key={t.name}
              >
                <div className="mkt-card-title">{t.name}</div>
                <div className="mkt-price">
                  <span className="mkt-price-num">{t.price}</span>
                  <span className="mkt-price-period">{t.period}</span>
                </div>
                <div className="mkt-card-body">{t.tagline}</div>
                <ul className="mkt-check-list">
                  {t.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                <Link
                  to="/app"
                  className={`mkt-btn ${t.highlight ? "mkt-btn-primary" : "mkt-btn-ghost"}`}
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
          <div className="mkt-note">
            <strong>How the allowance works:</strong> allowances are metered in tokens and shown to
            you as questions. When you reach the limit the tool stops and offers a top-up — it never
            quietly shortens answers or degrades quality. A compliance tool that gets worse without
            telling you is more dangerous than one that stops.
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Try fifteen questions before you decide.</h2>
          <p className="mkt-cta-sub">
            Ask things you already know the answer to, and check the citations against the Code
            yourself. That is the only sensible way to evaluate this.
          </p>
          <div className="mkt-hero-cta">
            <Link to="/app" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Start free
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
