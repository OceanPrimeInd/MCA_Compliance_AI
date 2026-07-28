import { useState } from "react";
import { Link } from "../lib/router";

const FAQS = [
  {
    q: "Is the answer legally binding?",
    a: "No. Compliance AI is a reference tool, not a legal or regulatory authority. Always verify anything important with the MCA or a Certifying Authority before acting on it — especially anything flagged as a weak match.",
  },
  {
    q: "What does the confidence score mean?",
    a: "Green (0.6+) means a strong match to the Code. Amber (0.45–0.6) means a moderate match worth a second look. Red (below 0.45) means a weak match — the app will explicitly warn you to verify it manually.",
  },
  {
    q: "What's the difference between 'verified' and 'unverified citation'?",
    a: "Verified means the cited clause text was checked and does exist in the source Code as quoted. Unverified means that check didn't pass — treat the citation with extra caution and check the Code directly.",
  },
  {
    q: "What document is this actually built on?",
    a: "The Sport or Pleasure Vessel Code 2025. Answers are generated only from that indexed text, not from general knowledge, so anything outside the Code won't be answered from thin air.",
  },
  {
    q: "Is my data private?",
    a: "Your conversations are stored in a Postgres database (via Supabase) with row-level security enabled, meaning your account can only ever read or write its own conversation history — not anyone else's.",
  },
  {
    q: "Do I need to upload any documents?",
    a: "No, not for the current version — it answers from the published Code itself. See 'What You'll Need' for what (if anything) helps you get sharper answers.",
  },
  {
    q: "Can I use this on my phone?",
    a: "Yes — it's a responsive web app. Sign in with your email in any modern mobile browser.",
  },
  {
    q: "How is this different from searching the PDF myself?",
    a: "Ctrl+F only finds exact keyword matches. Compliance AI understands the intent behind a plain-English question and points you to the clause that actually answers it, even if you don't know the right terminology.",
  },
  {
    q: "Do you offer team or enterprise plans?",
    a: "Yes — see the Pricing page for Professional (team seats) and Enterprise (custom ingestion, SSO, SLA) options.",
  },
  {
    q: "How do I get started?",
    a: "Sign up with your email, ask your first question, and you'll see the answer along with its citation and confidence score. No credit card required for the Free plan.",
  },
];

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`mkt-faq-item ${open ? "open" : ""}`}>
      <button className="mkt-faq-q" onClick={() => setOpen(!open)}>
        <span>{q}</span>
        <span className="mkt-faq-icon">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="mkt-faq-a">{a}</div>}
    </div>
  );
}

export default function FAQ() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">FAQ</div>
          <h1 className="mkt-h1">Questions people actually ask</h1>
          <p className="mkt-hero-sub">
            If something's not covered here, reach out and we'll add it.
          </p>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner mkt-faq-list">
          {FAQS.map((f) => (
            <FAQItem key={f.q} q={f.q} a={f.a} />
          ))}
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Still have a question?</h2>
          <div className="mkt-hero-cta">
            <a href="mailto:hello@compliance-ai.example" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Email us
            </a>
            <Link to="/app" className="mkt-btn mkt-btn-ghost-invert mkt-btn-lg">
              Try it free
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
