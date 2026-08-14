import { useState } from "react";
import { Link } from "../lib/router";

const FAQS = [
  {
    q: "Does it know my vessel, or just the Code?",
    a: "Your vessel. You set length overall, area category of operation, vessel type, hull material and passenger count once. Every question after that is filtered against it \u2014 clauses that cannot bind your vessel are removed before the answer is written, not mentioned and then dismissed.",
  },
  {
    q: "Which codes does it cover?",
    a: "MCA Sport or Pleasure Vessel Code 2025 and MCA Workboat Code Edition 3, both fully indexed and queryable in the same question. Uncrewed vessels (WB3 Annex 2 and MGN 664), the MGN/MIN/MSN amendment stream, MSN 1871 and the Recreational Craft Regulations are queued next.",
  },
  {
    q: "Can it compare two codes for the same vessel?",
    a: "Yes \u2014 that is the point of holding both. Ask what changes for your vessel between SPVC 2025 and Workboat Code Edition 3 and you get a side-by-side answer citing the governing clause in each. Retrieval is kept separate per code, so a difference claim is grounded in both documents rather than blended into one.",
  },
  {
    q: "What happens when the answer isn't in the Code?",
    a: "It says so, and names where the answer is likely to sit instead \u2014 the Merchant Shipping Regulations, a commercially licensed ISO or BSI standard, or Certifying Authority discretion. It does not guess. For a professional carrying liability, a reliable refusal is worth more than a confident answer with no source.",
  },
  {
    q: "Is the answer legally binding?",
    a: "No. OceanGRC is a reference tool, not a regulatory authority, and nothing here is an indication of MCA endorsement. Verify anything material with the MCA or your Certifying Authority before acting on it.",
  },
  {
    q: "Why does it quote the clause instead of summarising?",
    a: "Because a summary is not defensible. What you file in a design justification note needs to be the Code's own language with its clause number and page. The prose around the quote is packaging; the quoted clause is the product.",
  },
  {
    q: "What if the answer sits in a table?",
    a: "Many tables lose their row and column structure during PDF extraction. Where that has happened the tool names the table and page and marks the verdict as requiring visual confirmation, rather than inferring an intersection value it cannot actually read. A fabricated table value is the most damaging output a tool like this can produce.",
  },
  {
    q: "How do you decide a clause doesn't apply?",
    a: "Scope conditions are parsed deterministically from the Code's own wording \u2014 phrases like \"vessels of less than 12 metres\" and \"area category of operation 0 or 1\" \u2014 and inherited from parent clauses to their children. Every exclusion records the exact phrase it fired on, so it is auditable. Exclusion is conservative: anything ambiguous is kept, because hiding a binding clause is the one failure that cannot be recovered from.",
  },
  {
    q: "Is my data private?",
    a: "Sign-in and storage run on Supabase with row-level security, so your account can only ever read its own vessel profiles and history. Your vessel specification is used to filter answers and is not shared.",
  },
  {
    q: "Do you ingest ISO or BSI standards?",
    a: "No. Those are commercially licensed and reproducing them would be a copyright breach. MCA and gov.uk publications are Crown copyright under the Open Government Licence, which permits commercial reuse with attribution \u2014 those we do ingest. Where an answer depends on ISO 12215 or ISO 12217 the tool names the standard and stops.",
  },
  {
    q: "Who is this built for?",
    a: "Naval architects, small-craft designers, marine surveyors, compliance consultants and Certifying Authorities working in the 3\u201315m band. It is a design-stage and assessment tool, not a fleet operations platform \u2014 there are no certificate reminders or maintenance schedules here.",
  },
  {
    q: "What does the 13 December 2026 deadline mean for me?",
    a: "Workboat Code Edition 3 came into force on 13 December 2023. Transitional arrangements end on 13 December 2026 \u2014 vessels certificated under the Brown Code, the MGN 280(M) technical annex, or Edition 2 Amendment 1 must meet Edition 3 by their next renewal examination or by that date.",
  },
];

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`mkt-faq-item ${open ? "open" : ""}`}>
      <button className="mkt-faq-q" onClick={() => setOpen(!open)}>
        <span>{q}</span>
        <span className="mkt-faq-mark">{open ? "\u2212" : "+"}</span>
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
          <h1 className="mkt-h1">The questions a professional asks first</h1>
          <p className="mkt-hero-sub">
            If something is not covered here, email us and we will add it.
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
            <a href="mailto:hello@oceangrc.com" className="mkt-btn mkt-btn-primary mkt-btn-lg">
              Email us
            </a>
            <Link to="/app" className="mkt-btn mkt-btn-ghost-invert mkt-btn-lg">
              Start free
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
