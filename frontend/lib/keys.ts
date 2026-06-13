import type { Keys } from "./types";

// BYOK Cara A: keys live ONLY in the browser, in sessionStorage (cleared when the
// tab closes). They are NEVER sent to our backend — only directly to Groq/
// ElevenLabs from the browser. Do not move this to localStorage.
const STORAGE_KEY = "tenri.keys.v1";
export const DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"; // ElevenLabs "Rachel"

export function loadKeys(): Keys {
  if (typeof window === "undefined") {
    return { groq: "", elevenlabs: "", voiceId: DEFAULT_VOICE_ID };
  }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const k = JSON.parse(raw) as Partial<Keys>;
      return {
        groq: k.groq ?? "",
        elevenlabs: k.elevenlabs ?? "",
        voiceId: k.voiceId || DEFAULT_VOICE_ID,
      };
    }
  } catch {
    /* ignore malformed storage */
  }
  return { groq: "", elevenlabs: "", voiceId: DEFAULT_VOICE_ID };
}

export function saveKeys(keys: Keys): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
}

export function clearKeys(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}

export function hasKeys(keys: Keys): boolean {
  // Only Groq is required (STT + LLM). ElevenLabs is optional — without it Tenri
  // speaks with the free browser voice.
  return Boolean(keys.groq);
}
