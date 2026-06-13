// Free, keyless TTS using the browser's built-in Web Speech API
// (window.speechSynthesis). Works offline on Chrome/Edge/Safari + Android, no
// account needed. Lower quality than ElevenLabs but zero friction — used as the
// default voice and the fallback when ElevenLabs is absent or fails.

export function browserTtsAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  const target = lang.toLowerCase();
  return (
    voices.find((v) => v.lang?.toLowerCase() === target) ||
    voices.find((v) => v.lang?.toLowerCase().startsWith(target.slice(0, 2))) ||
    null
  );
}

/** Speak `text` and resolve when playback finishes (or on error/timeout). */
export function speakBrowser(text: string, lang = "id-ID"): Promise<void> {
  const clean = (text || "").trim();
  return new Promise((resolve) => {
    if (!clean || !browserTtsAvailable()) {
      resolve();
      return;
    }
    const synth = window.speechSynthesis;

    const utter = () => {
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = lang;
      const v = pickVoice(lang);
      if (v) u.voice = v;
      u.rate = 1.05;
      let settled = false;
      const done = () => {
        if (settled) return;
        settled = true;
        resolve();
      };
      u.onend = done;
      u.onerror = done;
      // Safety: never hang the turn if the engine stalls.
      setTimeout(done, Math.min(20000, 1500 + clean.length * 90));
      synth.cancel();
      synth.speak(u);
    };

    // Voices may load asynchronously on first use.
    if (synth.getVoices().length === 0) {
      const onVoices = () => {
        synth.removeEventListener("voiceschanged", onVoices);
        utter();
      };
      synth.addEventListener("voiceschanged", onVoices);
      // Fallback if voiceschanged never fires.
      setTimeout(() => {
        synth.removeEventListener("voiceschanged", onVoices);
        utter();
      }, 500);
    } else {
      utter();
    }
  });
}
