import { useState } from "react";
import { Link, useRoute } from "../lib/router";

const LINKS = [
  { to: "/solution", label: "Solution" },
  { to: "/documents", label: "What You'll Need" },
  { to: "/pricing", label: "Pricing" },
  { to: "/faq", label: "FAQ" },
];

export default function Nav() {
  const { path } = useRoute();
  const [open, setOpen] = useState(false);

  return (
    <header className="mkt-nav">
      <div className="mkt-nav-inner">
        <Link to="/" className="mkt-logo">
          <span className="mkt-logo-mark">⚓</span> Compliance AI
        </Link>

        <nav className={`mkt-nav-links ${open ? "open" : ""}`}>
          {LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={`mkt-nav-link ${path === l.to ? "active" : ""}`}
              onClick={() => setOpen(false)}
            >
              {l.label}
            </Link>
          ))}
          <Link to="/app" className="mkt-btn mkt-btn-primary mkt-nav-cta" onClick={() => setOpen(false)}>
            Try it free
          </Link>
        </nav>

        <button
          className="mkt-nav-toggle"
          aria-label="Toggle menu"
          onClick={() => setOpen(!open)}
        >
          {open ? "✕" : "☰"}
        </button>
      </div>
    </header>
  );
}
