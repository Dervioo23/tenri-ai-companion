"use client";

import { useState } from "react";
import { DEFAULT_VOICE_ID, saveKeys } from "@/lib/keys";
import { testGroqKey } from "@/lib/groq";
import { testElevenKey } from "@/lib/elevenlabs";
import type { Keys } from "@/lib/types";

export default function KeyPanel({
  initial,
  onSaved,
}: {
  initial: Keys;
  onSaved: (k: Keys) => void;
}) {
  const [groq, setGroq] = useState(initial.groq);
  const [elevenlabs, setEleven] = useState(initial.elevenlabs);
  const [voiceId, setVoiceId] = useState(initial.voiceId || DEFAULT_VOICE_ID);
  const [status, setStatus] = useState<"idle" | "testing" | "ok" | "err">("idle");
  const [msg, setMsg] = useState("");

  async function testAndSave() {
    setStatus("testing");
    setMsg("Menguji koneksi langsung browser → provider (juga menguji CORS)...");
    try {
      // These calls go straight to the providers with the user's keys. If the
      // browser is blocked by CORS, this is where we'd find out (R1 gate).
      await testGroqKey(groq.trim());
      await testElevenKey(elevenlabs.trim());
      const keys: Keys = {
        groq: groq.trim(),
        elevenlabs: elevenlabs.trim(),
        voiceId: voiceId.trim() || DEFAULT_VOICE_ID,
      };
      saveKeys(keys);
      setStatus("ok");
      setMsg("Koneksi berhasil. Key tersimpan di browser ini saja.");
      onSaved(keys);
    } catch (e) {
      setStatus("err");
      setMsg(
        `Gagal: ${(e as Error).message}. ` +
          "Jika ini error CORS/Network, provider memblokir panggilan langsung dari browser — " +
          "kita perlu thin-proxy di backend (lihat R1 di rencana).",
      );
    }
  }

  return (
    <div className="panel">
      <strong>API Key Anda (BYOK)</strong>
      <p className="note">
        Tenri memakai <b>API key Anda sendiri</b>. Key disimpan <b>hanya di browser ini</b>{" "}
        (sessionStorage, hilang saat tab ditutup) dan <b>tidak pernah dikirim ke server kami</b> —
        hanya langsung ke Groq & ElevenLabs.
      </p>

      <label>Groq API Key</label>
      <input
        type="password"
        value={groq}
        onChange={(e) => setGroq(e.target.value)}
        placeholder="gsk_..."
        autoComplete="off"
      />

      <label>ElevenLabs API Key</label>
      <input
        type="password"
        value={elevenlabs}
        onChange={(e) => setEleven(e.target.value)}
        placeholder="sk_..."
        autoComplete="off"
      />

      <label>ElevenLabs Voice ID (opsional)</label>
      <input
        type="text"
        value={voiceId}
        onChange={(e) => setVoiceId(e.target.value)}
        placeholder={DEFAULT_VOICE_ID}
        autoComplete="off"
      />

      <div className="row" style={{ marginTop: 12 }}>
        <button onClick={testAndSave} disabled={status === "testing" || !groq || !elevenlabs}>
          {status === "testing" ? "Menguji..." : "Test & Simpan"}
        </button>
        <span className={status === "err" ? "err" : status === "ok" ? "ok" : "note"}>{msg}</span>
      </div>

      <p className="note" style={{ marginTop: 12 }}>
        Dapatkan key: <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">Groq</a>{" "}
        · <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer">ElevenLabs</a>
      </p>
    </div>
  );
}
