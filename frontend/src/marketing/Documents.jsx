import { Link } from "../lib/router";

const CODES = [
  {
    title: "MCA Sport or Pleasure Vessel Code 2025",
    body: "Sport and pleasure vessels in commercial use. Construction, stability, machinery, fire safety, radio, manning and area categories of operation. Live and indexed.",
  },
  {
    title: "MCA Workboat Code Edition 3",
    body: "Small workboats and pilot boats, in force since 13 December 2023 under SI 2023/1216. Supersedes the original Code, Edition 2, and MGN 280(M). Live and indexed.",
  },
];

const ROADMAP = [
  {
    title: "WB3 Annex 2 — uncrewed vessels",
    body: "ROUVs under 24m certificated under Edition 3, plus the MGN 664 innovative-technology route. Largely an extension of the Workboat Code work already done.",
  },
  {
    title: "MGN / MIN / MSN amendment stream",
    body: "The notices that continuously amend the codes above. Small documents, high frequency — and the difference between a current answer and a stale one.",
  },
  {
    title: "MSN 1871 — small fishing vessels under 15m",
    body: "Self-contained, in-band, and a distinct designer and builder population the current corpora do not reach.",
  },
  {
    title: "Recreational Craft Regulations 2017 / UKCA",
    body: "The largest small-craft designer population in the 3–15m band. See the licensing note below — the answer ceiling here is genuinely lower, and we would rather say so.",
  },
];

const VESSEL_INPUTS = [
  "Length overall in metres — the single most decisive input, since thresholds at 12m, 15m and 24m change which regime applies.",
  "Area category of operation, 0 to 6 — determines a large share of equipment and construction requirements.",
  "Vessel type — workboat, pilot boat, commercial RIB, sport or pleasure.",
  "Hull material and passenger count — used for construction and life-saving appliance scope.",
];

export default function Documents() {
  return (
    <>
      <section className="mkt-hero mkt-hero-sm">
        <div className="mkt-hero-inner">
          <div className="mkt-eyebrow">Codes covered</div>
          <h1 className="mkt-h1">Two MCA codes, queryable together</h1>
          <p className="mkt-hero-sub">
            Every answer is drawn only from the indexed text of these documents. Nothing is answered
            from general knowledge of maritime regulation, which is why the tool can tell you when
            something is not in the Code at all.
          </p>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Indexed now</div>
            <h2 className="mkt-h2">Live and answerable today</h2>
          </div>
          <div className="mkt-grid mkt-grid-2">
            {CODES.map((c) => (
              <div className="mkt-card" key={c.title}>
                <div className="mkt-card-title">{c.title}</div>
                <div className="mkt-card-body">{c.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mkt-section mkt-section-alt">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">What you'll set up</div>
            <h2 className="mkt-h2">One vessel profile, then you never restate it</h2>
          </div>
          <ul className="mkt-check-list">
            {VESSEL_INPUTS.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mkt-section">
        <div className="mkt-section-inner">
          <div className="mkt-section-head">
            <div className="mkt-eyebrow">Queued next</div>
            <h2 className="mkt-h2">Ranked by value per unit of build effort</h2>
          </div>
          <div className="mkt-grid mkt-grid-2">
            {ROADMAP.map((r) => (
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
          <div className="mkt-note">
            <strong>On licensing, plainly:</strong> MCA and gov.uk publications are Crown copyright
            released under the Open Government Licence, which permits commercial reuse with
            attribution — those we ingest. ISO and BSI harmonised standards such as ISO 12215 and
            ISO 12217 are commercially licensed and are <strong>not</strong> ingested. Where an
            answer depends on one, the tool names the standard by number and stops there rather than
            reproducing text it has no right to serve.
          </div>
        </div>
      </section>

      <section className="mkt-cta-banner">
        <div className="mkt-cta-inner">
          <h2 className="mkt-h2">Set your vessel and start asking.</h2>
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
