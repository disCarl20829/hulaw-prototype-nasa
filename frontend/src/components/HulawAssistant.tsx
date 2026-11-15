import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { ApiError, sendChat } from "../services/hulaw-api";
import type { MascotMood } from "../types";

// Mascot moods map to the images in public/hulaw-mascot. The mood comes from the
// backend's combined index for the loaded location ("default" while there is no data).
const mascotSrc = (mood: MascotMood) => `${import.meta.env.BASE_URL}hulaw-mascot/${mood}_mascot.png`;
const MOOD_TEXT: Record<MascotMood, string> = { default: "No drought signal loaded yet", happy: "Near normal or wetter conditions", moderate: "Moderate dryness signal", negative: "Severe dryness signal" };

interface Message { from: "user" | "hulaw" | "error"; text: string; tools?: string[] }
// SMAP satellite files are about 650 MB per day. When the backend does not have the file
// for a date yet it must download it from NASA first, so the user is warned before asking.
const NEEDS_SMAP = /\bsoil\s+moisture\b|\bsmap\b/i;

const MODAL: Record<"overlay" | "card" | "title" | "text" | "actions", CSSProperties> = {
  overlay: { position: "absolute", inset: 0, zIndex: 2, display: "grid", placeItems: "center", padding: 16, background: "rgba(6,11,16,.8)" },
  card: { display: "grid", gap: 10, padding: 16, border: "1px solid rgba(108,190,190,.3)", borderRadius: 12, background: "#14232c" },
  title: { fontSize: 13 },
  text: { margin: 0, color: "#b8c5cf", fontSize: 11, lineHeight: 1.55 },
  actions: { display: "flex", justifyContent: "flex-end", gap: 8 },
};

interface Props { mood?: MascotMood; location?: { name: string; latitude: number; longitude: number } }

export default function HulawAssistant({ mood = "default", location }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [smapPrompt, setSmapPrompt] = useState<string | null>(null); // question waiting for the SMAP warning to be accepted
  const smapAccepted = useRef(false); // warn once per visit
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages, sending, open]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    if (NEEDS_SMAP.test(text) && !smapAccepted.current) { setSmapPrompt(text); return; }
    void send(text);
  }

  async function send(text: string) {
    setDraft("");
    setMessages((m) => [...m, { from: "user", text }]);
    setSending(true);
    try {
      const response = await sendChat(text, location);
      setMessages((m) => [...m, { from: "hulaw", text: response.reply, tools: response.tools_used }]);
    } catch (error) {
      const message = error instanceof ApiError && error.status === 503
        ? "The AI assistant is not configured on the backend yet (Azure OpenAI settings are missing)."
        : error instanceof Error ? error.message : "The assistant could not answer.";
      setMessages((m) => [...m, { from: "error", text: message }]);
    } finally { setSending(false); }
  }

  return <div className="hulaw-assistant">
    {open && <section className="assistant-panel" style={{ position: "relative" }} role="dialog" aria-modal="false" aria-labelledby="assistant-title">
      <div className="assistant-head"><div className="assistant-title"><img className="assistant-mascot" src={mascotSrc(mood)} alt="" /><div><strong id="assistant-title">Hulaw AI Assistant</strong><span>{location ? `Location: ${location.name}` : "Philippines drought intelligence"}</span></div></div><button type="button" className="assistant-close" onClick={() => setOpen(false)} aria-label="Close assistant">×</button></div>
      <div className="assistant-messages" aria-live="polite">
        <div className="assistant-welcome"><img className="assistant-avatar" src={mascotSrc(mood)} alt="" /><div><strong>Hi! I’m Hulaw.</strong><p>Ask me about rainfall, soil moisture or vegetation for the location you selected on the map. My answers use the same NASA data as the charts.</p></div></div>
        {messages.map((m, i) => <div className={`assistant-msg ${m.from}`} key={i}><p>{m.text}</p>{!!m.tools?.length && <span>Data used: {m.tools.join(", ")}</span>}</div>)}
        {sending && <div className="assistant-msg hulaw pending"><p>Checking the data…</p></div>}
        <div ref={end} />
      </div>
      <form className="assistant-compose" onSubmit={submit}><input aria-label="Message Hulaw AI" placeholder="Ask about drought conditions…" value={draft} maxLength={1000} onChange={(e) => setDraft(e.target.value)} disabled={sending} /><button type="submit" disabled={sending || !draft.trim()} aria-label="Send message">↑</button></form>
      <p className="assistant-footnote">AI answers can be wrong. Not an official drought warning.</p>
      {smapPrompt && <div className="assistant-modal" style={MODAL.overlay} role="alertdialog" aria-modal="true" aria-labelledby="smap-title" aria-describedby="smap-text">
        <div className="assistant-modal-card" style={MODAL.card}>
          <strong id="smap-title" style={MODAL.title}>Soil moisture can take a while</strong>
          <p id="smap-text" style={MODAL.text}>SMAP satellite files are about 650 MB for each day. If the file for your date is not on the server yet, Hulaw has to download it from NASA first, which usually takes several minutes. You may be asked to repeat the question later.</p>
          <div className="assistant-modal-actions" style={MODAL.actions}>
            <button type="button" onClick={() => setSmapPrompt(null)}>Cancel</button>
            <button type="button" className="primary" autoFocus onClick={() => { const text = smapPrompt; smapAccepted.current = true; setSmapPrompt(null); void send(text); }}>Continue</button>
          </div>
        </div>
      </div>}
    </section>}
    <button className="hulaw-fab" type="button" onClick={() => setOpen((value) => !value)} aria-label={open ? "Close Hulaw AI assistant" : "Open Hulaw AI assistant"} aria-expanded={open} title={MOOD_TEXT[mood]}>
      <img src={mascotSrc(mood)} alt="" /><span className={`fab-status ${mood}`} />
    </button>
  </div>;
}
