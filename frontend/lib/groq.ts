import type { Message } from "./types";

// All calls go directly from the browser to Groq using the USER's own key.
// (BYOK Cara A.) If Groq blocks browser CORS, these throw — that is the R1 gate.
const GROQ_BASE = "https://api.groq.com/openai/v1";
const STT_MODEL = "whisper-large-v3-turbo";

/** Transcribe a recorded audio blob via Groq Whisper. */
export async function transcribe(audio: Blob, groqKey: string): Promise<string> {
  const form = new FormData();
  form.append("file", audio, "speech.webm");
  form.append("model", STT_MODEL);
  form.append("language", "id");
  form.append("temperature", "0");

  const res = await fetch(`${GROQ_BASE}/audio/transcriptions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${groqKey}` },
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Groq STT ${res.status}: ${await safeText(res)}`);
  }
  const data = await res.json();
  return (data.text ?? "").trim();
}

/** Non-streaming chat completion (MVP). Streaming comes in Phase 2. */
export async function chat(
  messages: Message[],
  groqKey: string,
  opts: { model: string; max_tokens: number },
): Promise<string> {
  const res = await fetch(`${GROQ_BASE}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${groqKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: opts.model,
      messages,
      max_tokens: opts.max_tokens,
      temperature: 0.6,
      stream: false,
    }),
  });
  if (!res.ok) {
    throw new Error(`Groq chat ${res.status}: ${await safeText(res)}`);
  }
  const data = await res.json();
  return (data.choices?.[0]?.message?.content ?? "").trim();
}

/** Cheap validity + CORS check for the Groq key (R1 gate). */
export async function testGroqKey(groqKey: string): Promise<void> {
  const res = await fetch(`${GROQ_BASE}/models`, {
    headers: { Authorization: `Bearer ${groqKey}` },
  });
  if (!res.ok) throw new Error(`Groq key invalid (${res.status})`);
}

async function safeText(res: Response): Promise<string> {
  try {
    return (await res.text()).slice(0, 200);
  } catch {
    return "";
  }
}
