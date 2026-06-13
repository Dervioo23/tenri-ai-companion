export type Role = "system" | "user" | "assistant";

export interface Message {
  role: Role;
  content: string;
}

export interface LlmParams {
  model: string;
  max_tokens: number;
  max_sentences: number;
  max_chars: number;
}

export interface RouteResponse {
  action:
    | "answer"
    | "navigate"
    | "slide_info"
    | "slide_list"
    | "wake_ack"
    | "close"
    | "monitor"
    | "ignore";
  reason: string;
  intent: string;
  messages: Message[] | null;
  llm: LlmParams | null;
  context_str: string;
  sources: string[];
  text: string;
  slide_index: number;
  slide_str: string;
  slides: string[];
  extend_window: boolean;
  clear_quiet: boolean;
  set_quiet: boolean;
  clear_window: boolean;
}

export interface RouteRequest {
  transcript: string;
  slide_index: number;
  history: Message[];
  in_conversation: boolean;
  quiet_mode: boolean;
}

export interface VerifyResponse {
  final_text: string;
  overridden: boolean;
}

export interface Keys {
  groq: string;
  elevenlabs: string;
  voiceId: string;
}
