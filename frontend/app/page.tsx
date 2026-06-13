"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import KeyPanel from "@/components/KeyPanel";
import { Recorder } from "@/lib/audio";
import { backendHealth } from "@/lib/backend";
import { hasKeys, loadKeys } from "@/lib/keys";
import {
  ConvState,
  inConversation,
  initConv,
  runTurn,
  TurnHandlers,
  UiState,
} from "@/lib/conversation";
import type { Keys, Message } from "@/lib/types";

interface LogItem {
  id: number;
  who: "user" | "tenri" | "info";
  text: string;
  sources?: string[];
}

const STATE_LABEL: Record<UiState, string> = {
  idle: "Siaga",
  listening: "Mendengar...",
  thinking: "Berpikir...",
  speaking: "Berbicara...",
};

export default function Home() {
  const [keys, setKeys] = useState<Keys | null>(null);
  const [showKeys, setShowKeys] = useState(false);
  const [ui, setUi] = useState<UiState>("idle");
  const [log, setLog] = useState<LogItem[]>([]);
  const [err, setErr] = useState("");
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [windowOpen, setWindowOpen] = useState(false);
  const [slideLabel, setSlideLabel] = useState("");
  const [health, setHealth] = useState<string>("");

  const convRef = useRef<ConvState>(initConv());
  const historyRef = useRef<Message[]>([]);
  const recorderRef = useRef<Recorder | null>(null);
  const logId = useRef(0);

  const append = useCallback((item: Omit<LogItem, "id">) => {
    setLog((prev) => [...prev, { id: logId.current++, ...item }]);
  }, []);

  useEffect(() => {
    const k = loadKeys();
    if (hasKeys(k)) setKeys(k);
    else setShowKeys(true);
    backendHealth()
      .then((h) =>
        setHealth(`backend ok · ${h.slides} slide · ${h.chunks} chunk · ${h.live_model}`),
      )
      .catch(() => setHealth("backend tak terjangkau — set NEXT_PUBLIC_BACKEND_URL"));
  }, []);

  const handlers: TurnHandlers = {
    onState: setUi,
    onUser: (text) => append({ who: "user", text }),
    onTenri: (text, sources) => append({ who: "tenri", text, sources }),
    onSlide: (index, slideStr) => {
      setSlideLabel(slideStr || `Slide ${index + 1}`);
      append({ who: "info", text: `→ ${slideStr || `Slide ${index + 1}`}` });
    },
    onInfo: (msg) => append({ who: "info", text: msg }),
  };

  async function startRec() {
    if (busy || recording || !keys) return;
    setErr("");
    try {
      const rec = new Recorder();
      recorderRef.current = rec;
      await rec.start();
      setRecording(true);
      setUi("listening");
    } catch (e) {
      setErr(`Mikrofon gagal: ${(e as Error).message}`);
      recorderRef.current = null;
    }
  }

  async function stopRec() {
    if (!recording || !recorderRef.current || !keys) return;
    setRecording(false);
    const blob = await recorderRef.current.stop();
    recorderRef.current = null;
    // Guard tiny/empty recordings (quick taps) — Groq STT rejects them with 400.
    if (blob.size < 1400) {
      setErr("Rekaman terlalu singkat — tahan tombol, lalu bicara dengan jelas.");
      setUi("idle");
      return;
    }
    setBusy(true);
    setUi("thinking");
    try {
      const res = await runTurn(blob, keys, convRef.current, historyRef.current, handlers);
      convRef.current = res.conv;
      historyRef.current = res.history;
      setWindowOpen(inConversation(res.conv));
      setSlideLabel((prev) => prev || `Slide ${res.conv.slideIndex + 1}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
      setUi("idle");
    }
  }

  return (
    <div className="wrap">
      <div className="brand">
        <h1>T E N R I</h1>
        <span className="sub">Voice Companion · Web (BYOK)</span>
      </div>

      {showKeys || !keys ? (
        <KeyPanel
          initial={keys ?? loadKeys()}
          onSaved={(k) => {
            setKeys(k);
            setShowKeys(false);
          }}
        />
      ) : (
        <>
          <div className="panel">
            <button
              className="talk"
              disabled={busy}
              onPointerDown={(e) => {
                e.preventDefault();
                startRec();
              }}
              onPointerUp={(e) => {
                e.preventDefault();
                stopRec();
              }}
              onPointerLeave={() => {
                if (recording) stopRec();
              }}
            >
              {recording ? "● Lepas untuk kirim" : busy ? "..." : "Tahan untuk bicara"}
            </button>

            <div className="status">
              <span>
                <span className={`dot ${ui}`} />
                {STATE_LABEL[ui]}
              </span>
              <span>{windowOpen ? "● percakapan terbuka" : "○ panggil “Tenri”"}</span>
              {slideLabel && <span className="slide">{slideLabel.split("\n")[0]}</span>}
            </div>
            {err && <p className="err" style={{ marginTop: 8 }}>{err}</p>}
          </div>

          <div className="panel">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>Percakapan</strong>
              <button className="ghost" onClick={() => setShowKeys(true)}>
                Ganti API key
              </button>
            </div>
            <div className="log" style={{ marginTop: 12 }}>
              {log.length === 0 && (
                <p className="note">
                  Tahan tombol & <b>mulai dengan menyebut &ldquo;Tenri&rdquo;</b> untuk membuka —
                  mis. <i>&ldquo;Tenri, jelaskan slide ini&rdquo;</i>. Setelah itu tanya atau berdebat
                  bebas. Ucapkan <b>&ldquo;terima kasih&rdquo;</b> untuk menutup. Tanpa &ldquo;Tenri&rdquo;,
                  ia menganggap Anda bicara ke audiens dan diam.
                </p>
              )}
              {log.map((m) => (
                <div key={m.id} className={`msg ${m.who}`}>
                  {m.who !== "info" && <div className="who">{m.who === "user" ? "ANDA" : "TENRI"}</div>}
                  {m.text}
                  {m.sources && m.sources.length > 0 && (
                    <div className="src">sumber: {m.sources.join(", ")}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <p className="note">{health}</p>
    </div>
  );
}
