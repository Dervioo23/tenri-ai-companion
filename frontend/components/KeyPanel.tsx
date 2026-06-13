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
  const [groqMsg, setGroqMsg] = useState("");
  const [elevenMsg, setElevenMsg] = useState("");
  const [hint, setHint] = useState("");

  async function probe(label: string, fn: () => Promise<void>): Promise<boolean> {
    try {
      await fn();
      return true;
    } catch (e) {
      const m = (e as Error).message || String(e);
      // "Failed to fetch" = the request never completed (network/extension/VPN),
      // NOT a CORS block — both providers send Access-Control-Allow-Origin: *.
      // A 401/403 = the request DID reach the provider but the key was rejected.
      let reason = m;
      if (/failed to fetch|networkerror|load failed/i.test(m)) {
        reason = "tak sampai ke server (jaringan / ekstensi pemblokir / VPN — bukan CORS)";
      } else if (/\b(401|403)\b|invalid/i.test(m)) {
        reason = `${m} — key ditolak. Pastikan key benar & lengkap, atau buat key baru di dashboard provider.`;
      }
      setHint(`${label}: ${reason}`);
      return false;
    }
  }

  async function testAndSave() {
    setStatus("testing");
    setGroqMsg("menguji...");
    setElevenMsg("menunggu...");
    setHint("");

    const groqOk = await probe("Groq", () => testGroqKey(groq.trim()));
    setGroqMsg(groqOk ? "✓ terhubung" : "✗ gagal");

    setElevenMsg("menguji...");
    const elevenOk = await probe("ElevenLabs", () => testElevenKey(elevenlabs.trim()));
    setElevenMsg(elevenOk ? "✓ terhubung" : "✗ gagal");

    if (groqOk && elevenOk) {
      const keys: Keys = {
        groq: groq.trim(),
        elevenlabs: elevenlabs.trim(),
        voiceId: voiceId.trim() || DEFAULT_VOICE_ID,
      };
      saveKeys(keys);
      setStatus("ok");
      setHint("Koneksi berhasil. Key tersimpan di browser ini saja.");
      onSaved(keys);
    } else {
      setStatus("err");
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
        {(groqMsg || elevenMsg) && (
          <span className="note">
            Groq: <b className={groqMsg.startsWith("✓") ? "ok" : groqMsg.startsWith("✗") ? "err" : ""}>{groqMsg}</b>
            {"   "}·{"   "}
            ElevenLabs: <b className={elevenMsg.startsWith("✓") ? "ok" : elevenMsg.startsWith("✗") ? "err" : ""}>{elevenMsg}</b>
          </span>
        )}
      </div>
      {hint && (
        <p className={status === "err" ? "err" : "ok"} style={{ marginTop: 8 }}>
          {hint}
        </p>
      )}

      <p className="note" style={{ marginTop: 12 }}>
        Dapatkan key: <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">Groq</a>{" "}
        · <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noreferrer">ElevenLabs</a>
      </p>
    </div>
  );
}
