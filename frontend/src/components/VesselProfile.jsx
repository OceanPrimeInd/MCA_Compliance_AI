import { useState, useEffect } from "react";
import { api } from "../lib/api";

/**
 * The context layer's input surface.
 *
 * Captured once, then applied to every question — the user never restates their
 * vessel. This is the difference between "what does the Code say" and "what do
 * I have to do", and it is why answers can be filtered before the model sees
 * them rather than after.
 */

const VESSEL_TYPES = [
  { value: "workboat", label: "Workboat" },
  { value: "pilot boat", label: "Pilot boat" },
  { value: "commercial rib", label: "Commercial RIB" },
  { value: "sport", label: "Sport vessel" },
  { value: "pleasure", label: "Pleasure vessel" },
];

const HULL_MATERIALS = ["GRP", "Aluminium", "Steel", "Timber", "Composite", "Other"];

const AREA_CATEGORIES = [
  { value: 0, label: "Category 0 — Unlimited" },
  { value: 1, label: "Category 1 — Up to 150 miles from safe haven" },
  { value: 2, label: "Category 2 — Up to 60 miles from safe haven" },
  { value: 3, label: "Category 3 — Up to 20 miles from safe haven" },
  { value: 4, label: "Category 4 — Up to 20 miles, favourable weather" },
  { value: 5, label: "Category 5 — Up to 20 miles, categorised waters" },
  { value: 6, label: "Category 6 — Up to 3 miles, categorised waters" },
];

const EMPTY = {
  vessel_type: "workboat",
  length_overall: "",
  area_category: 2,
  hull_material: "GRP",
  passenger_count: 0,
};

export default function VesselProfile({ onSaved, compact = false }) {
  const [form, setForm] = useState(EMPTY);
  const [existing, setExisting] = useState(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getVessel()
      .then((profile) => {
        if (cancelled) return;
        if (profile) {
          setExisting(profile);
          setForm({ ...profile, length_overall: String(profile.length_overall) });
        }
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("ready"));
    return () => {
      cancelled = true;
    };
  }, []);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setError(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const loa = parseFloat(form.length_overall);
    if (Number.isNaN(loa) || loa <= 0) {
      setError("Enter the length overall in metres.");
      return;
    }

    setStatus("saving");
    try {
      const saved = await api.saveVessel({
        vessel_type: form.vessel_type,
        length_overall: loa,
        area_category: Number(form.area_category),
        hull_material: form.hull_material,
        passenger_count: Number(form.passenger_count) || 0,
      });
      setExisting(saved);
      setStatus("ready");
      onSaved?.(saved);
    } catch (err) {
      setError(err.message);
      setStatus("ready");
    }
  }

  if (status === "loading") {
    return <div className="vessel-panel vessel-panel--loading">Loading vessel profile…</div>;
  }

  return (
    <form className={`vessel-panel${compact ? " vessel-panel--compact" : ""}`} onSubmit={handleSubmit}>
      <div className="vessel-panel__head">
        <h2>{existing ? "Vessel profile" : "Set up your vessel"}</h2>
        <p>
          Entered once. Every answer is then filtered to the clauses that actually bind
          this vessel — you never restate it.
        </p>
      </div>

      <div className="vessel-grid">
        <label className="vessel-field">
          <span>Vessel type</span>
          <select value={form.vessel_type} onChange={(e) => update("vessel_type", e.target.value)}>
            {VESSEL_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        <label className="vessel-field">
          <span>Length overall (m)</span>
          <input
            type="number"
            step="0.1"
            min="0.1"
            max="100"
            placeholder="e.g. 11.8"
            value={form.length_overall}
            onChange={(e) => update("length_overall", e.target.value)}
            required
          />
        </label>

        <label className="vessel-field vessel-field--wide">
          <span>Area category of operation</span>
          <select
            value={form.area_category}
            onChange={(e) => update("area_category", e.target.value)}
          >
            {AREA_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>

        <label className="vessel-field">
          <span>Hull material</span>
          <select
            value={form.hull_material}
            onChange={(e) => update("hull_material", e.target.value)}
          >
            {HULL_MATERIALS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label className="vessel-field">
          <span>Passengers carried</span>
          <input
            type="number"
            min="0"
            max="500"
            value={form.passenger_count}
            onChange={(e) => update("passenger_count", e.target.value)}
          />
        </label>
      </div>

      {error && <div className="vessel-error">{error}</div>}

      <div className="vessel-actions">
        <button type="submit" className="btn-primary" disabled={status === "saving"}>
          {status === "saving" ? "Saving…" : existing ? "Update vessel" : "Lock in vessel"}
        </button>
        {existing && (
          <span className="vessel-current">
            Currently: {existing.length_overall}m {existing.vessel_type}, Category{" "}
            {existing.area_category}
          </span>
        )}
      </div>
    </form>
  );
}

/** Compact always-visible summary for the question screen. */
export function VesselBadge({ vessel, onEdit }) {
  if (!vessel) {
    return (
      <button className="vessel-badge vessel-badge--empty" onClick={onEdit}>
        ⚠ No vessel set — answers will be general. Add your vessel →
      </button>
    );
  }
  return (
    <button className="vessel-badge" onClick={onEdit}>
      <span className="vessel-badge__dot" />
      {vessel.length_overall}m {vessel.vessel_type} · Category {vessel.area_category} ·{" "}
      {vessel.hull_material} · {vessel.passenger_count} pax
      <span className="vessel-badge__edit">Edit</span>
    </button>
  );
}
