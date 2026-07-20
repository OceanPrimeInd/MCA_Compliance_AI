import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);

    try {
      if (mode === "signin") {
        const { error } = await signIn(email, password);
        if (error) setError(error.message);
      } else {
        const { error } = await signUp(email, password);
        if (error) setError(error.message);
        else setInfo("Check your email to confirm your account, then sign in.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="brand-title" style={{ marginBottom: "0.2rem" }}>
          ⚓ Compliance AI
        </div>
        <div className="brand-sub" style={{ marginBottom: "1.6rem" }}>
          Sport or Pleasure Vessel 2025 — Beta reference tool
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />

          {mode !== "magic" && (
            <>
              <label>Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </>
          )}

          {error && <div className="auth-error">{error}</div>}
          {info && <div className="auth-info">{info}</div>}

          <button type="submit" disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "signin"
              ? "Sign in"
              : mode === "signup"
              ? "Create account"
              : "Send magic link"}
          </button>
        </form>

        <div className="auth-switch">
          {mode !== "signin" && (
            <button type="button" onClick={() => setMode("signin")}>Have an account? Sign in</button>
          )}
          {mode !== "signup" && (
            <button type="button" onClick={() => setMode("signup")}>Need an account? Sign up</button>
          )}
        </div>
      </div>
    </div>
  );
}
