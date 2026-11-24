import React, { useEffect, useRef, useState } from "react";
import { sendChat } from "./api.js";

// A new session starts on every page load.
const newSessionId = () => "s-" + Math.random().toString(36).slice(2, 10);

function Meta({ md }) {
  const cached = md.resolution_source === "LLM_CACHE";
  return (
    <div className="meta">
      <span className={"badge " + (cached ? "cache" : "live")} data-testid="meta-source">
        {md.resolution_source}
      </span>
      <span className="chip">
        model <b data-testid="meta-model">{md.model}</b>
      </span>
      <span className="chip">
        latency <b data-testid="meta-latency">{md.latency_ms} ms</b>
      </span>
      <span className="chip">
        input tokens <b data-testid="meta-input-tokens">{md.input_tokens}</b>
      </span>
      <span className="chip">
        output tokens <b data-testid="meta-output-tokens">{md.output_tokens}</b>
      </span>
      {md.key_id && (
        <span className="chip">
          {md.key_id}
          {md.fallback_attempts > 0 ? `, after ${md.fallback_attempts} failed` : ""}
        </span>
      )}
    </div>
  );
}

export default function App() {
  const [sessionId] = useState(newSessionId);
  const [items, setItems] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [simulate, setSimulate] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput(""); // input is empty right after sending
    setItems((prev) => [...prev, { kind: "user", text }]);
    setBusy(true);
    try {
      const data = await sendChat({
        sessionId,
        message: text,
        systemPrompt,
        simulateFailure: simulate.trim(),
      });
      setItems((prev) => [...prev, { kind: "assistant", text: data.reply, md: data.metadata }]);
    } catch (err) {
      setItems((prev) => [...prev, { kind: "error", text: err.message }]);
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Chat</h1>
        <span className="session">session {sessionId}</span>
      </header>

      <details className="settings">
        <summary>Session settings</summary>
        <label>
          System prompt
          <textarea
            data-testid="system-prompt-input"
            rows={2}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Optional. Example: Answer like a patient tutor."
          />
        </label>
        <label>
          Simulate key failure (for demos)
          <input
            value={simulate}
            onChange={(e) => setSimulate(e.target.value)}
            placeholder="key_1=429 or *=429"
          />
        </label>
      </details>

      <main>
        {items.length === 0 && (
          <p className="empty">Send a message to start. Each reply shows where it came from.</p>
        )}
        {items.map((it, i) =>
          it.kind === "user" ? (
            <div key={i} className="row user">
              <div className="bubble">{it.text}</div>
            </div>
          ) : it.kind === "error" ? (
            <div key={i} className="row">
              <div className="error" role="alert">{it.text}</div>
            </div>
          ) : (
            <div key={i} className="row">
              <div className="assistant" data-testid="assistant-message">
                <div className="reply">{it.text}</div>
                <Meta md={it.md} />
              </div>
            </div>
          )
        )}
        {busy && <div className="row"><div className="thinking">Thinking…</div></div>}
        <div ref={endRef} />
      </main>

      <footer>
        <textarea
          data-testid="chat-input"
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type a message. Enter sends, Shift+Enter adds a line."
        />
        <button data-testid="send-button" onClick={send} disabled={busy}>
          Send
        </button>
      </footer>
    </div>
  );
}
