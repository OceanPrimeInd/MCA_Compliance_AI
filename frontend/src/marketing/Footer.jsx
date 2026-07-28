import { Link } from "../lib/router";

export default function Footer() {
  return (
    <footer className="mkt-footer">
      <div className="mkt-footer-inner">
        <div className="mkt-footer-brand">
          <div className="mkt-logo">
            <span className="mkt-logo-mark">⚓</span> Compliance AI
          </div>
          <p className="mkt-footer-tag">
            A cited, plain-English reference tool for the Sport or Pleasure Vessel Code 2025.
            Not a substitute for advice from the MCA or a Certifying Authority.
          </p>
        </div>

        <div className="mkt-footer-cols">
          <div className="mkt-footer-col">
            <div className="mkt-footer-heading">Product</div>
            <Link to="/solution">Solution</Link>
            <Link to="/documents">What You'll Need</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="/faq">FAQ</Link>
          </div>
          <div className="mkt-footer-col">
            <div className="mkt-footer-heading">Get started</div>
            <Link to="/app">Try it free</Link>
          </div>
          <div className="mkt-footer-col">
            <div className="mkt-footer-heading">Contact</div>
            <a href="mailto:hello@compliance-ai.example">hello@compliance-ai.example</a>
          </div>
        </div>
      </div>

      <div className="mkt-footer-bottom">
        <span>© {new Date().getFullYear()} Compliance AI. Beta reference tool — always verify against the official Code.</span>
      </div>
    </footer>
  );
}
