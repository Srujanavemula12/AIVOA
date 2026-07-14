import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { createInteraction } from "../slices/interactionsSlice";

const emptyForm = {
  hcpName: "",
  interactionType: "visit",
  date: "",
  time: "",
  attendees: "",
  topics: "",
  materials: [],
  samples: [],
  sentiment: "positive",
  outcomes: "",
  followUpActions: "",
};

export default function StructuredForm({ hcpId }) {
  const dispatch = useDispatch();
  const activeInteraction = useSelector((s) => s.interactions.activeInteraction);

  const [form, setForm] = useState(emptyForm);
  const [materialInput, setMaterialInput] = useState("");
  const [sampleInput, setSampleInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [suggestedFollowups, setSuggestedFollowups] = useState([]);

  // Whenever the chat panel logs/edits an interaction, mirror it here so the
  // structured form and the chat stay in sync (same underlying record).
  useEffect(() => {
    if (!activeInteraction) return;
    const created = activeInteraction.created_at ? new Date(activeInteraction.created_at) : null;
    setForm({
      hcpName: activeInteraction.hcp_name || "",
      interactionType: activeInteraction.interaction_type || "visit",
      date: created ? created.toISOString().slice(0, 10) : "",
      time: created ? created.toTimeString().slice(0, 5) : "",
      attendees: (activeInteraction.attendees || []).join(", "),
      topics: activeInteraction.summary || (activeInteraction.topics_discussed || []).join(", "),
      materials: activeInteraction.materials_shared || [],
      samples: activeInteraction.samples_distributed || [],
      sentiment: activeInteraction.sentiment || "positive",
      outcomes: activeInteraction.outcomes || "",
      followUpActions: activeInteraction.follow_up_actions || "",
    });
    setSuggestedFollowups(activeInteraction.suggested_followups || []);
  }, [activeInteraction]);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const addMaterial = () => {
    if (!materialInput.trim()) return;
    setForm((f) => ({ ...f, materials: [...f.materials, materialInput.trim()] }));
    setMaterialInput("");
  };

  const addSample = () => {
    if (!sampleInput.trim()) return;
    setForm((f) => ({ ...f, samples: [...f.samples, sampleInput.trim()] }));
    setSampleInput("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.topics.trim() && !form.hcpName.trim()) return;
    setSubmitting(true);
    try {
      await dispatch(
        createInteraction({
          hcp_id: hcpId,
          interaction_type: form.interactionType,
          channel: "structured",
          raw_notes: form.topics,
          summary: form.topics.slice(0, 160),
          hcp_name: form.hcpName,
          attendees: form.attendees ? form.attendees.split(",").map((a) => a.trim()).filter(Boolean) : [],
          materials_shared: form.materials,
          samples_distributed: form.samples,
          sentiment: form.sentiment,
          outcomes: form.outcomes,
          follow_up_actions: form.followUpActions,
        })
      ).unwrap();
      setForm(emptyForm);
      setSuggestedFollowups([]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-row">
        <div>
          <label>HCP Name</label>
          <input
            type="text"
            placeholder="Search or select HCP..."
            value={form.hcpName}
            onChange={update("hcpName")}
          />
        </div>
        <div>
          <label>Interaction Type</label>
          <select value={form.interactionType} onChange={update("interactionType")}>
            <option value="visit">Meeting</option>
            <option value="call">Call</option>
            <option value="email">Email</option>
            <option value="conference">Conference / event</option>
          </select>
        </div>
      </div>

      <div className="form-row">
        <div>
          <label>Date</label>
          <input type="date" value={form.date} onChange={update("date")} />
        </div>
        <div>
          <label>Time</label>
          <input type="time" value={form.time} onChange={update("time")} />
        </div>
      </div>

      <label>Attendees</label>
      <input
        type="text"
        placeholder="Enter names or search..."
        value={form.attendees}
        onChange={update("attendees")}
      />

      <label>Topics Discussed</label>
      <textarea
        placeholder="Enter key discussion points..."
        value={form.topics}
        onChange={update("topics")}
      />
      <button type="button" className="link-btn">
        🎙 Summarize from Voice Note (Requires Consent)
      </button>

      <label>Materials Shared / Samples Distributed</label>
      <div className="chip-section">
        <div className="chip-section-label">Materials Shared</div>
        <div className="chip-list">
          {form.materials.length === 0 && <span className="chip-empty">No materials added.</span>}
          {form.materials.map((m, i) => (
            <span className="chip" key={i}>{m}</span>
          ))}
        </div>
        <div className="chip-add-row">
          <input
            type="text"
            placeholder="e.g. Brochure"
            value={materialInput}
            onChange={(e) => setMaterialInput(e.target.value)}
          />
          <button type="button" className="btn-secondary" onClick={addMaterial}>🔍 Search/Add</button>
        </div>
      </div>

      <div className="chip-section">
        <div className="chip-section-label">Samples Distributed</div>
        <div className="chip-list">
          {form.samples.length === 0 && <span className="chip-empty">No samples added.</span>}
          {form.samples.map((s, i) => (
            <span className="chip" key={i}>{s}</span>
          ))}
        </div>
        <div className="chip-add-row">
          <input
            type="text"
            placeholder="e.g. Cardivex 10mg"
            value={sampleInput}
            onChange={(e) => setSampleInput(e.target.value)}
          />
          <button type="button" className="btn-secondary" onClick={addSample}>+ Add Sample</button>
        </div>
      </div>

      <label>Observed/Inferred HCP Sentiment</label>
      <div className="radio-group">
        {[
          { value: "positive", emoji: "🙂", label: "Positive" },
          { value: "neutral", emoji: "😐", label: "Neutral" },
          { value: "negative", emoji: "🙁", label: "Negative" },
        ].map((opt) => (
          <label key={opt.value} className="radio-option">
            <input
              type="radio"
              name="sentiment"
              value={opt.value}
              checked={form.sentiment === opt.value}
              onChange={update("sentiment")}
            />
            {opt.emoji} {opt.label}
          </label>
        ))}
      </div>

      <label>Outcomes</label>
      <textarea
        placeholder="Key outcomes or agreements..."
        value={form.outcomes}
        onChange={update("outcomes")}
      />

      <label>Follow-up Actions</label>
      <textarea
        placeholder="What needs to happen next..."
        value={form.followUpActions}
        onChange={update("followUpActions")}
      />

      {suggestedFollowups.length > 0 && (
        <div className="ai-suggestions">
          <div className="chip-section-label">AI Suggested Follow-ups</div>
          <ul>
            {suggestedFollowups.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      <button className="btn-primary" type="submit" disabled={submitting}>
        {submitting ? "Saving..." : "Log Interaction"}
      </button>
    </form>
  );
}
