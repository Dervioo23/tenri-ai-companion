import { routeTurn, verifyAnswer } from "./backend";
import { chat, transcribe } from "./groq";
import { speak } from "./elevenlabs";
import type { Keys, Message, RouteResponse } from "./types";

export const WINDOW_MS = 30_000;

export type UiState = "idle" | "listening" | "thinking" | "speaking";

export interface ConvState {
  conversationUntil: number; // epoch ms; > now means inside the window
  quietMode: boolean;
  slideIndex: number;
}

export function initConv(): ConvState {
  return { conversationUntil: 0, quietMode: false, slideIndex: 0 };
}

export function inConversation(s: ConvState): boolean {
  return Date.now() < s.conversationUntil;
}

/** Apply the conversation-state hints the backend returned. */
export function applyFlags(s: ConvState, r: RouteResponse): ConvState {
  let conversationUntil = s.conversationUntil;
  let quietMode = s.quietMode;
  if (r.extend_window) conversationUntil = Date.now() + WINDOW_MS;
  if (r.clear_window) conversationUntil = 0;
  if (r.set_quiet) quietMode = true;
  if (r.clear_quiet) quietMode = false;
  const slideIndex =
    typeof r.slide_index === "number" ? r.slide_index : s.slideIndex;
  return { conversationUntil, quietMode, slideIndex };
}

export interface TurnHandlers {
  onState: (s: UiState) => void;
  onUser: (text: string) => void;
  onTenri: (text: string, sources?: string[]) => void;
  onSlide?: (index: number, slideStr: string) => void;
  onInfo?: (msg: string) => void;
}

export interface TurnResult {
  conv: ConvState;
  history: Message[];
}

/**
 * Run one full turn: STT (browser) -> /route (backend) -> LLM (browser) ->
 * /verify (backend) -> TTS (browser). All provider calls use the user's keys.
 */
export async function runTurn(
  audio: Blob,
  keys: Keys,
  conv: ConvState,
  history: Message[],
  h: TurnHandlers,
): Promise<TurnResult> {
  h.onState("thinking");

  const transcript = await transcribe(audio, keys.groq);
  if (!transcript) {
    h.onState("idle");
    return { conv, history };
  }
  h.onUser(transcript);

  const resp = await routeTurn({
    transcript,
    slide_index: conv.slideIndex,
    history,
    in_conversation: inConversation(conv),
    quiet_mode: conv.quietMode,
  });
  const newConv = applyFlags(conv, resp);
  let newHistory = history;

  switch (resp.action) {
    case "answer": {
      let text = await chat(resp.messages ?? [], keys.groq, {
        model: resp.llm?.model ?? "llama-3.1-8b-instant",
        max_tokens: resp.llm?.max_tokens ?? 180,
      });
      try {
        if (resp.context_str) {
          const v = await verifyAnswer(text, resp.context_str);
          text = v.final_text;
        }
      } catch {
        /* grounding check is best-effort; never block the answer */
      }
      const cap = resp.llm?.max_chars ?? 0;
      if (cap > 0) text = trimToChars(text, cap);
      h.onTenri(text, resp.sources);
      h.onState("speaking");
      await speak(text, keys.elevenlabs, keys.voiceId);
      newHistory = [
        ...history,
        { role: "user", content: transcript },
        { role: "assistant", content: text },
      ];
      break;
    }
    case "wake_ack":
    case "close": {
      h.onTenri(resp.text);
      h.onState("speaking");
      await speak(resp.text, keys.elevenlabs, keys.voiceId);
      break;
    }
    case "navigate":
    case "slide_info": {
      h.onSlide?.(newConv.slideIndex, resp.slide_str);
      break;
    }
    case "slide_list": {
      h.onInfo?.(resp.slides.map((t, i) => `${i + 1}. ${t}`).join("\n"));
      break;
    }
    case "monitor":
    case "ignore":
    default:
      // Addressed to the audience / acknowledgment / noise — Tenri stays silent.
      break;
  }

  h.onState("idle");
  return { conv: newConv, history: newHistory };
}

function trimToChars(text: string, max: number): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastStop = Math.max(cut.lastIndexOf(". "), cut.lastIndexOf("! "), cut.lastIndexOf("? "));
  return (lastStop > max * 0.5 ? cut.slice(0, lastStop + 1) : cut).trim();
}
