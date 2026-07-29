import { useState, useRef, useEffect } from "react";
import { sendChat } from "./api";

const QUICK_PROMPTS = {
  en: ["Tell me a story about being brave", "What happens if I break something by accident?"],
  ta: ["தைரியமான கதை சொல்லு", "தவறுதலாக ஏதாவது உடைத்தால் என்ன செய்வது?"],
};

export default function App() {
  const [language, setLanguage] = useState("en");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastSource, setLastSource] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(text) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    const nextHistory = [...messages, { role: "user", content: trimmed }];
    setMessages(nextHistory);
    setInput("");
    setLoading(true);
    try {
      const data = await sendChat({
        message: trimmed,
        language,
        history: nextHistory.map(({ role, content }) => ({ role, content })),
      });
      setMessages((cur) => [...cur, { role: "assistant", content: data.reply }]);
      setLastSource(data.source_story_title || null);
    } catch (e) {
      setMessages((cur) => [
        ...cur,
        { role: "assistant", content: "I couldn't reach my thinking cap. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <span style={styles.logo}>TIMBA</span>
        <div style={styles.langToggle}>
          {["en", "ta"].map((code) => (
            <button
              key={code}
              onClick={() => setLanguage(code)}
              style={{ ...styles.langBtn, ...(language === code ? styles.langBtnActive : {}) }}
            >
              {code === "en" ? "English" : "தமிழ்"}
            </button>
          ))}
        </div>
      </div>

      <div ref={scrollRef} style={styles.chatArea}>
        {messages.length === 0 && (
          <div style={styles.empty}>Say hello to TIMBA, or try a prompt below.</div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{ ...styles.bubbleRow, justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}
          >
            <div style={{ ...styles.bubble, ...(m.role === "user" ? styles.bubbleUser : styles.bubbleTimba) }}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && <div style={styles.thinking}>TIMBA is thinking...</div>}
      </div>

      {lastSource && (
        <div style={styles.sourceTag}>Grounded in: "{lastSource}"</div>
      )}

      {messages.length === 0 && (
        <div style={styles.prompts}>
          {QUICK_PROMPTS[language].map((p) => (
            <button key={p} style={styles.promptChip} onClick={() => handleSend(p)}>
              {p}
            </button>
          ))}
        </div>
      )}

      <div style={styles.inputRow}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
          placeholder="Ask TIMBA something..."
          style={styles.input}
        />
        <button onClick={() => handleSend(input)} disabled={loading || !input.trim()} style={styles.sendBtn}>
          Send
        </button>
      </div>
    </div>
  );
}

const styles = {
  page: { maxWidth: 480, margin: "0 auto", height: "100vh", display: "flex", flexDirection: "column", fontFamily: "system-ui, sans-serif", background: "#16213E", color: "#F6EFE2" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid #22315A" },
  logo: { fontWeight: 700, fontSize: 20, color: "#D9A868" },
  langToggle: { display: "flex", gap: 6 },
  langBtn: { fontSize: 12, padding: "4px 10px", borderRadius: 999, background: "transparent", color: "#D9A868", border: "1px solid #D9A868", cursor: "pointer" },
  langBtnActive: { background: "#D9A868", color: "#16213E" },
  chatArea: { flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 10 },
  empty: { textAlign: "center", opacity: 0.6, marginTop: 20 },
  bubbleRow: { display: "flex" },
  bubble: { maxWidth: "80%", padding: "10px 14px", borderRadius: 16, fontSize: 14, lineHeight: 1.5 },
  bubbleUser: { background: "#3E8E7E", color: "#F6EFE2" },
  bubbleTimba: { background: "#22315A", color: "#F6EFE2", border: "1px solid rgba(166,105,60,0.3)" },
  thinking: { opacity: 0.6, fontSize: 13, padding: "0 6px" },
  sourceTag: { fontSize: 11, opacity: 0.5, padding: "0 20px 6px" },
  prompts: { display: "flex", flexWrap: "wrap", gap: 8, padding: "0 20px 10px" },
  promptChip: { fontSize: 12, padding: "6px 12px", borderRadius: 999, background: "rgba(166,105,60,0.2)", border: "1px solid #A6693C", color: "#F6EFE2", cursor: "pointer" },
  inputRow: { display: "flex", gap: 8, padding: 16, borderTop: "1px solid #22315A" },
  input: { flex: 1, padding: "10px 14px", borderRadius: 999, background: "#22315A", border: "1px solid #22315A", color: "#F6EFE2", outline: "none" },
  sendBtn: { padding: "10px 18px", borderRadius: 999, background: "#D9A868", color: "#16213E", border: "none", fontWeight: 600, cursor: "pointer" },
};
