import { supabase } from "./supabase";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

async function authHeaders() {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) throw new Error("Not signed in");
  return {
    Authorization: `Bearer ${session.access_token}`,
    "Content-Type": "application/json",
  };
}

async function request(path, options = {}) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers: await authHeaders(),
  });

  if (!res.ok) {
    // The backend returns a usable message in `detail` for 400/422/429.
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body — keep the status message */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }

  return res.status === 204 ? null : res.json();
}

export const api = {
  /** Which codes this deployment can answer against. Public — no auth needed. */
  async listCodes() {
    const res = await fetch(`${BACKEND_URL}/codes`);
    if (!res.ok) throw new Error("Could not load code catalogue");
    return res.json();
  },

  getVessel: () => request("/vessel"),

  saveVessel: (profile) =>
    request("/vessel", { method: "PUT", body: JSON.stringify(profile) }),

  clearVessel: () => request("/vessel", { method: "DELETE" }),

  ask: (question, codeIds = null) =>
    request("/ask", {
      method: "POST",
      body: JSON.stringify({ question, code_ids: codeIds }),
    }),

  /** Every determination made for this account, newest first. */
  listProvenance: (limit = 50) => request(`/provenance?limit=${limit}`),

  /** Dated, attributable text for a design justification file. */
  designNote: (recordId) => request(`/provenance/${recordId}/design-note`),

  /** Which past determinations relied on clauses that have now changed. */
  impact: (clauses, codeId = null) =>
    request("/provenance/impact", {
      method: "POST",
      body: JSON.stringify({ clauses, code_id: codeId }),
    }),

  /** One question against two or more codes, kept side by side. */
  compare: (question, codeIds) =>
    request("/compare", {
      method: "POST",
      body: JSON.stringify({ question, code_ids: codeIds }),
    }),
};

export { BACKEND_URL };
