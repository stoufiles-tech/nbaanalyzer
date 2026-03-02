import { useState, useRef, useEffect } from "react";
import { api } from "../api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTED_PROMPTS = [
  "Who are the best PG values this season?",
  "Which teams can afford a max player?",
  "Who is the most overpaid player?",
  "Best teams for cap flexibility?",
];

export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (question: string) => {
    if (!question.trim() || loading) return;
    const q = question.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);
    try {
      const data = await api.chatWithAnalyst(q);
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-chat">
      <div className="ai-chat-messages">
        {messages.length === 0 && (
          <div className="ai-chat-welcome">
            <h3>NBA AI Analyst</h3>
            <p>Ask me anything about the 2025-26 season — cap situations, player values, trade ideas, and more.</p>
            <div className="suggested-prompts">
              {SUGGESTED_PROMPTS.map((p) => (
                <button key={p} className="prompt-chip" onClick={() => send(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            <div className="chat-bubble">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="chat-message assistant">
            <div className="chat-bubble chat-loading">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="ai-chat-input-row">
        <input
          className="ai-chat-input"
          placeholder="Ask the analyst..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          disabled={loading}
        />
        <button
          className="ai-chat-send"
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
