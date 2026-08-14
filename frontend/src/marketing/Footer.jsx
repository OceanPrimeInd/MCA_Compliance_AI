import { Link } from "../lib/router";

export default function Footer() {
  return (
    <footer className="mkt-footer">
      <div className="mkt-footer-inner">
        <div className="mkt-footer-brand">
          <div className="mkt-logo">
            <span className="mkt-logo-mark">⚓</span> OceanGRC
          </div>
          <p className="mkt-footer-tag">
            Applicability-filtered answers from the MCA Sport or Pleasure Vessel Code 2025 and
            Workboat Code Edition 3. A professional reference tool — not a substitute for advice
            from the MCA or a Certifying Authority, and not an indication of MCA endorsement.
          </p>
        </div>

        <div className="mkt-footer-cols">
          <div className="mkt-footer-col">
            <div className="mkt-footer-heading">Product</div>
            <Link to="/solution">How it works</Link>
            <Link to="/documents">Codes covered</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="/faq">FAQ</Link>
          </div>
          <div className="mkt-footer-col">
            <div className="mkt-footer-heading">Get started</div>
            <Link to="/app">Start free</Link>
          </div>
          <div className="mkt-footer-col">
            <div className="mkt-footer-heading">Contact</div>
            <a href="mailto:hello@oceangrc.com">hello@oceangrc.com</a>
          </div>
        </div>
      </div>

      <div className="mkt-footer-bottom">
        <span>
          © {new Date().getFullYear()} OceanGRC. Code text is Crown copyright, reproduced under the
          Open Government Licence. Always verify against the official published Code.
        </span>
      </div>
    </footer>
  );
}
