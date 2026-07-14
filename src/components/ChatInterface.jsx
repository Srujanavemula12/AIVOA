import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendAgentMessage, appendChatMessage } from "../slices/interactionsSlice";

export default function ChatInterface({ hcpId }) {
  const dispatch = useDispatch();
  const chatLog = useSelector((s) => s.interactions.chatLog);
  const activeInteraction = useSelector((s) => s.interactions.activeInteraction);
 
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    dispatch(appendChatMessage({ role: "user", text: message }));
    setSending(true);
    const toSend = message;
    setMessage("");
    try {
     await dispatch(sendAgentMessage({ hcpId, message: toSend, interactionId: activeInteraction?.id })).unwrap();
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <div className="chat-window">
        {chatLog.length === 0 && (
          <p style={{ color: "#98a2b3", fontSize: 14 }}>
            Try: "Just wrapped up a call with Dr. Rao, discussed Cardivex
            dosing for elderly patients, she seemed positive and wants
            samples sent next week."
          </p>
        )}
        {chatLog.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.toolCalls && m.toolCalls.length > 0 && (
              <div>
                {m.toolCalls.map((t, j) => (
                  <span key={j} className="tool-tag">{t}</span>
                ))}
              </div>
            )}
            {m.text}
          </div>
        ))}
        {sending && <div className="chat-bubble agent">thinking...</div>}
      </div>
      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          placeholder={
            'Log interaction details here (e.g., "Met Dr. Smith, discussed ' +
            'Prodo-X efficacy, positive sentiment, shared brochure") or ask for help.'
          }
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button className="btn-primary" type="submit" disabled={sending}>
          Log
        </button>
      </form>
    </div>
  );
}
