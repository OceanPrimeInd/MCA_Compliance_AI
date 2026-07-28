import { Link } from "../lib/router";

const READY = [
  {
    title: "Your email address",
    body: "That's all you need to create an account — a magic link or email/password sign-in gets you into the app. No credit card for the free tier.",
  },
  {
    title: "The vessel category you operate under",
    body: "Knowing whether you're asking about a Category 0–6(A) vessel, a sail training vessel, etc. helps you phrase sharper questions and interpret the clauses you get back.",
  },
  {
    title: "The area of the Code you're checking",
    body: "Construction, stability, machinery, fire safety, radio, or manning — you don't need the clause number, just a rough idea of the topic.",
  },
  {
    title: "Any certificate you're cross-checking",
    body: "If you're validating against an existing Certificate of Compliance or survey report, having it open alongside the chat makes it easy to compare.",
  },
];

const NOT_NEEDED = [
  "Full vessel documentation upload — the current version answers from the published Code itself, not from documents you provide.",
  "Payment details for the free tier — no card required to start asking questions.",
  "Any personal or financial information beyond the email used to sign in.",
];

export default function Documents() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">Getting started</div>
          <h1 className="mkt-h1">What you'll need before you ask</h1>
          <p className="mkt-hero-sub">
            Compliance AI is built directly on the Sport or Pleasure Vessel Code 2025 — there's
            nothing to upload to get an answer. A little context just helps you ask sharper
            questions.
          </p>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Have this handy</div>
            <h2 className="mkt-h2">Nothing mandatory beyond an email — this just helps</h2>
          </div>
          <div className="mkt-grid mkt-grid-2">
            {READY.map((r) => (
              <div className="mkt-card mkt-card-plain" key={r.title}>
                <div className="mkt-card-title">{r.title}</div>
                <div className="mkt-card-body">{r.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-section mkt-section-alt">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">What we don't ask for</div>
            <h2 className="mkt-h2">On purpose, we keep onboarding light</h2>
          </div>
          <ul className="mkt-check-list">
            {NOT_NEEDED.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-note">
            <strong>Roadmap:</strong> support for uploading your own vessel-specific documents
            (Safety Management System manuals, survey reports, certificates) so answers can be
            cross-checked against your own paperwork, not just the published Code, is planned for
            a future release.
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">That's it — you're ready to ask.</h2>
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
