// Push-to-talk recorder using MediaRecorder. Webm/opus is accepted by Groq Whisper.

export class Recorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private stream: MediaStream | null = null;

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.chunks = [];
    const mime = pickMime();
    this.mediaRecorder = new MediaRecorder(
      this.stream,
      mime ? { mimeType: mime } : undefined,
    );
    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    };
    // Timeslice so data flushes periodically — more reliable for short clips
    // (avoids an empty/undecodable webm that Groq rejects with 400).
    this.mediaRecorder.start(100);
  }

  /** Stop and return the recorded audio. */
  stop(): Promise<Blob> {
    return new Promise((resolve) => {
      const mr = this.mediaRecorder;
      if (!mr) {
        resolve(new Blob());
        return;
      }
      mr.onstop = () => {
        const blob = new Blob(this.chunks, { type: mr.mimeType || "audio/webm" });
        this.cleanup();
        resolve(blob);
      };
      mr.stop();
    });
  }

  private cleanup(): void {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.mediaRecorder = null;
  }
}

function pickMime(): string | null {
  if (typeof MediaRecorder === "undefined") return null;
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const c of candidates) {
    if (MediaRecorder.isTypeSupported(c)) return c;
  }
  return null;
}
