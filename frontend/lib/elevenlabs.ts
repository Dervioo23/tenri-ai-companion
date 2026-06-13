// ElevenLabs TTS direct from the browser with the USER's key (BYOK Cara A).
// MVP uses the non-streaming REST endpoint and plays the returned MP3.
// WebSocket streaming (first-voice ~fast) is Phase 2.
const ELEVEN_BASE = "https://api.elevenlabs.io/v1";
const TTS_MODEL = "eleven_flash_v2_5";

/** Synthesize `text` and play it. Resolves when playback finishes. */
export async function speak(
  text: string,
  elevenKey: string,
  voiceId: string,
): Promise<void> {
  const clean = (text || "").trim();
  if (!clean) return;

  const res = await fetch(`${ELEVEN_BASE}/text-to-speech/${voiceId}`, {
    method: "POST",
    headers: {
      "xi-api-key": elevenKey,
      "Content-Type": "application/json",
      Accept: "audio/mpeg",
    },
    body: JSON.stringify({
      text: clean,
      model_id: TTS_MODEL,
      voice_settings: { stability: 0.5, similarity_boost: 0.65 },
    }),
  });
  if (!res.ok) {
    throw new Error(`ElevenLabs TTS ${res.status}: ${await safeText(res)}`);
  }
  const blob = await res.blob();
  await playBlob(blob);
}

function playBlob(blob: Blob): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    const done = () => {
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.onended = done;
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("audio playback failed"));
    };
    audio.play().catch(reject);
  });
}

/** Cheap validity + CORS check for the ElevenLabs key (R1 gate). */
export async function testElevenKey(elevenKey: string): Promise<void> {
  const res = await fetch(`${ELEVEN_BASE}/voices`, {
    headers: { "xi-api-key": elevenKey },
  });
  if (!res.ok) throw new Error(`ElevenLabs key invalid (${res.status})`);
}

async function safeText(res: Response): Promise<string> {
  try {
    return (await res.text()).slice(0, 200);
  } catch {
    return "";
  }
}
