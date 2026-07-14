import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchInteractions } from "../slices/interactionsSlice";
import StructuredForm from "./StructuredForm";
import ChatInterface from "./ChatInterface";

const DEMO_HCP_ID = process.env.REACT_APP_DEMO_HCP_ID || "demo-hcp-1";

export default function LogInteractionScreen() {
  const dispatch = useDispatch();
  const items = useSelector((s) => s.interactions.items);

  useEffect(() => {
    dispatch(fetchInteractions(DEMO_HCP_ID));
  }, [dispatch]);

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>Log Interaction</h1>
        <p>Record an HCP interaction using a structured form or by chatting with the AI assistant.</p>
      </div>

      <div className="log-columns">
        <div className="card form-panel">
          <h2 className="panel-title">Interaction Details</h2>
          <StructuredForm hcpId={DEMO_HCP_ID} />
        </div>

        <div className="card chat-panel">
          <h2 className="panel-title">AI Assistant</h2>
          <p className="panel-subtitle">Log Interaction details here via chat</p>
          <ChatInterface hcpId={DEMO_HCP_ID} />
        </div>
      </div>

      <div className="interaction-list">
        <h3 style={{ fontSize: 15 }}>Recent interactions</h3>
        {items.length === 0 && <p style={{ color: "#98a2b3", fontSize: 14 }}>No interactions logged yet.</p>}
        {items.map((it) => (
          <div className="interaction-item" key={it.id}>
            <div className="meta">
              <span>{it.interaction_type} • {new Date(it.created_at).toLocaleString()} • via {it.channel}</span>
              {it.sentiment && <span className={`badge ${it.sentiment}`}>{it.sentiment}</span>}
            </div>
            <div>{it.summary || it.raw_notes}</div>
            {it.topics_discussed && it.topics_discussed.length > 0 && (
              <div style={{ marginTop: 6, fontSize: 12, color: "#667085" }}>
                Topics: {it.topics_discussed.join(", ")}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
