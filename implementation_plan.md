# AI Companion Terminal Prototype — Implementation Plan

Membangun prototipe karakter AI interaktif berbasis Python terminal yang dapat berinteraksi melalui suara, merespons dengan suara, dan menerima konteks visual dari kamera. Mengikuti tahapan pengembangan dari dokumen perencanaan proyek.

## User Review Required

> [!IMPORTANT]
> **API Keys diperlukan**: Anda perlu menyiapkan API key untuk **Groq** dan **ElevenLabs** sebelum tahap 1 dan 2 dapat dijalankan. Silakan siapkan dan masukkan ke file `.env`.

> [!IMPORTANT]
> **Persona Karakter AI**: Dokumen menyebutkan persona karakter perlu ditentukan (nama, gaya bicara, peran, bahasa). Saya akan membuat persona default yang dapat Anda ubah nanti. Default: karakter bernama **"AIRA"** (AI Research Assistant), bilingual ID/EN, gaya bicara singkat dan sadar konteks.

> [!WARNING]
> **ElevenLabs Voice ID**: Anda perlu memilih voice ID dari ElevenLabs dashboard. Saya akan menyiapkan placeholder di `.env.example`.

## Open Questions

> [!IMPORTANT]
> 1. **Bahasa utama karakter**: Apakah default menggunakan Bahasa Indonesia, English, atau bilingual?
> 2. **Speech Recognition engine**: Apakah boleh menggunakan `speech_recognition` library (gratis, menggunakan Google Speech API) atau lebih prefer model offline seperti Whisper?
> 3. **Audio playback**: Preferensi library? Saya akan menggunakan `pygame.mixer` karena cross-platform dan stabil.
> 4. **Groq Model**: Apakah ada preferensi model? Default: `llama-3.1-70b-versatile` atau `llama3-70b-8192`.

---

## Proposed Changes

Implementasi dibagi ke **5 tahap** sesuai dokumen perencanaan. Semua file dibuat dalam satu batch, dengan setiap tahap memvalidasi komponen tertentu.

---

### Tahap 0: Project Foundation — Struktur Folder, Config, Dependencies

#### [NEW] [main.py](file:///c:/ai-companion-terminal/main.py)
- Entry point aplikasi
- Import dan jalankan `interaction_loop` dari `app.core`
- Minimalis, hanya orchestration

#### [NEW] [requirements.txt](file:///c:/ai-companion-terminal/requirements.txt)
- Dependencies:
  - `groq` — Groq Python SDK
  - `elevenlabs` — ElevenLabs Python SDK
  - `SpeechRecognition` — Speech-to-text
  - `pyaudio` — Audio input recording
  - `pygame` — Audio playback
  - `opencv-python` — Computer vision
  - `python-dotenv` — Environment config
  - `colorama` — Terminal colors (Windows compatible)
  - `rich` — Rich terminal UI (status, panels, tables)

#### [NEW] [.env.example](file:///c:/ai-companion-terminal/.env.example)
- Template dengan semua variabel yang dibutuhkan:
  - `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`
  - `GROQ_MODEL`, `APP_LANGUAGE`, `VISION_ENABLED`

#### [NEW] [README.md](file:///c:/ai-companion-terminal/README.md)
- Dokumentasi instalasi, setup, cara menjalankan, dan struktur proyek

---

### Tahap 0: App Package & Config

#### [NEW] [app/\_\_init\_\_.py](file:///c:/ai-companion-terminal/app/__init__.py)
- Package marker

#### [NEW] [app/config.py](file:///c:/ai-companion-terminal/app/config.py)
- Load `.env` menggunakan `dotenv`
- Expose semua config sebagai class/dataclass: `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `GROQ_MODEL`, `VISION_ENABLED`, paths, dll.
- Validasi: raise error jika key kritis tidak tersedia

#### [NEW] [app/state.py](file:///c:/ai-companion-terminal/app/state.py)
- Enum/class untuk state aplikasi: `IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`
- Global state manager dengan method `set_state()`, `get_state()`

---

### Tahap 1: Text-Only AI (Core Interaction)

#### [NEW] [app/core/\_\_init\_\_.py](file:///c:/ai-companion-terminal/app/core/__init__.py)

#### [NEW] [app/core/interaction_loop.py](file:///c:/ai-companion-terminal/app/core/interaction_loop.py)
- Main loop: tampilkan status → terima input → proses AI → tampilkan respons → ulangi
- Tahap 1: input teks dari terminal (belum suara)
- Push-to-talk flow: user tekan Enter → ketik/bicara → proses
- Integrasi state management
- Graceful exit dengan Ctrl+C

#### [NEW] [app/core/prompt_builder.py](file:///c:/ai-companion-terminal/app/core/prompt_builder.py)
- Load persona dari `character_prompt.txt`
- Load system rules dari `system_rules.txt`
- Build prompt array: `[system_prompt, ...conversation_history, user_input]`
- Inject vision context jika tersedia (misalnya `[VISUAL CONTEXT: face detected]`)

#### [NEW] [app/core/session_memory.py](file:///c:/ai-companion-terminal/app/core/session_memory.py)
- Simpan conversation history dalam list of dicts `[{"role": "user", "content": "..."}, ...]`
- Limit history (default: 10 exchanges) agar tidak melebihi context window
- Method: `add_message()`, `get_history()`, `clear()`

#### [NEW] [app/services/\_\_init\_\_.py](file:///c:/ai-companion-terminal/app/services/__init__.py)

#### [NEW] [app/services/groq_service.py](file:///c:/ai-companion-terminal/app/services/groq_service.py)
- Initialize Groq client
- Method `get_response(messages: list) -> str`
- Error handling: timeout, rate limit, API error
- Logging response time

#### [NEW] [app/prompts/character_prompt.txt](file:///c:/ai-companion-terminal/app/prompts/character_prompt.txt)
- Default persona AIRA:
  - Nama: AIRA
  - Peran: AI Research Companion untuk lecture/presentasi
  - Gaya: singkat, reflektif, sadar konteks, tidak dominan
  - Bahasa: bilingual (ID/EN, sesuai user)

#### [NEW] [app/prompts/system_rules.txt](file:///c:/ai-companion-terminal/app/prompts/system_rules.txt)
- Aturan respons: maksimal 2-3 kalimat, jangan menyela, tunggu trigger
- Format output: plain text, tanpa markdown
- Batas topik: sesuai konteks presentasi

---

### Tahap 2: Voice Output (ElevenLabs TTS)

#### [NEW] [app/services/elevenlabs_service.py](file:///c:/ai-companion-terminal/app/services/elevenlabs_service.py)
- Initialize ElevenLabs client
- Method `text_to_speech(text: str) -> str` (returns audio file path)
- Save audio ke `assets/audio/responses/` atau `assets/audio/temp/`
- Error handling: API error, rate limit

#### [NEW] [app/services/audio_player.py](file:///c:/ai-companion-terminal/app/services/audio_player.py)
- Initialize pygame mixer
- Method `play_audio(file_path: str)` — blocking playback
- Method `stop()` — interrupt playback
- Cleanup temp files setelah playback

#### Update [app/core/interaction_loop.py](file:///c:/ai-companion-terminal/app/core/interaction_loop.py)
- Setelah mendapat respons teks dari Groq, kirim ke ElevenLabs
- Putar audio respons
- Update state: `THINKING` → `SPEAKING` → `IDLE`

---

### Tahap 3: Voice Input (Speech Recognition)

#### [NEW] [app/services/speech_service.py](file:///c:/ai-companion-terminal/app/services/speech_service.py)
- Initialize `speech_recognition.Recognizer`
- Method `listen() -> str` — record dari microphone, convert ke teks
- Push-to-talk mode: user tekan Enter → mulai record → selesai otomatis saat silence
- Error handling: no microphone, ambient noise, recognition failure
- Adjustable timeout dan energy threshold

#### Update [app/core/interaction_loop.py](file:///c:/ai-companion-terminal/app/core/interaction_loop.py)
- Ganti text input dengan voice input
- Flow: Enter → `LISTENING` → record → `THINKING` → AI → `SPEAKING` → play → `IDLE`
- Fallback ke text input jika microphone tidak tersedia

---

### Tahap 4: Computer Vision Trigger (OpenCV)

#### [NEW] [app/services/vision_service.py](file:///c:/ai-companion-terminal/app/services/vision_service.py)
- Initialize OpenCV VideoCapture
- Method `get_visual_context() -> dict` — return detected context
- Deteksi: `face_detected`, `face_count`, `motion_detected`, `no_presence`
- Run di background thread agar tidak blocking main loop
- Save snapshot ke `assets/images/camera_snapshots/` (opsional, untuk debugging)
- Configurable: `VISION_ENABLED` dari `.env`

#### Update [app/core/prompt_builder.py](file:///c:/ai-companion-terminal/app/core/prompt_builder.py)
- Inject visual context ke prompt jika vision enabled
- Format: `[VISUAL CONTEXT: 2 faces detected, motion active]`

#### Update [app/core/interaction_loop.py](file:///c:/ai-companion-terminal/app/core/interaction_loop.py)
- Start vision service di awal jika enabled
- Pass visual context ke prompt builder setiap interaction cycle

---

### Tahap 5: Refinement & Polish

#### [NEW] [app/utils/\_\_init\_\_.py](file:///c:/ai-companion-terminal/app/utils/__init__.py)

#### [NEW] [app/utils/logger.py](file:///c:/ai-companion-terminal/app/utils/logger.py)
- Setup Python logging dengan file handler + console handler
- Log ke `app/data/logs/` dengan timestamp
- Log levels: INFO untuk flow normal, WARNING untuk fallbacks, ERROR untuk exceptions

#### [NEW] [app/utils/file_manager.py](file:///c:/ai-companion-terminal/app/utils/file_manager.py)
- Ensure semua folder yang dibutuhkan ada saat startup
- Cleanup temp audio files
- Method `ensure_directories()`, `cleanup_temp()`

#### [NEW] [app/utils/terminal_ui.py](file:///c:/ai-companion-terminal/app/utils/terminal_ui.py)
- Menggunakan `rich` library untuk terminal UI yang lebih menarik
- Status display: `[IDLE]`, `[LISTENING]`, `[THINKING]`, `[SPEAKING]`
- Panel untuk conversation log
- Spinner/progress saat AI sedang memproses
- Welcome banner saat startup

#### [NEW] [tests/test_groq_service.py](file:///c:/ai-companion-terminal/tests/test_groq_service.py)
- Unit test: koneksi Groq, response format, error handling

#### [NEW] [tests/test_prompt_builder.py](file:///c:/ai-companion-terminal/tests/test_prompt_builder.py)
- Unit test: prompt construction, memory injection, vision context injection

#### [NEW] [tests/test_speech_service.py](file:///c:/ai-companion-terminal/tests/test_speech_service.py)
- Unit test: speech service initialization, mock recording

---

### Asset Directories

#### [NEW] Folder structure
```
assets/audio/responses/     — audio respons ElevenLabs
assets/audio/temp/          — file audio sementara
assets/images/camera_snapshots/ — frame kamera untuk debugging
app/data/logs/              — log files
```

---

## Verification Plan

### Automated Tests
1. **Tahap 1**: `python main.py` → ketik teks → verifikasi respons dari Groq muncul di terminal
2. **Tahap 2**: Verifikasi audio diputar setelah respons AI
3. **Tahap 3**: Verifikasi speech-to-text berfungsi, fallback ke text jika mic tidak ada
4. **Tahap 4**: Verifikasi vision context muncul di log dan mempengaruhi respons
5. **Unit tests**: `python -m pytest tests/`

### Manual Verification
- Jalankan `python main.py` dan lakukan percakapan 5-10 exchange
- Verifikasi state transitions di terminal UI (IDLE → LISTENING → THINKING → SPEAKING → IDLE)
- Verifikasi conversation history tetap kontekstual
- Test graceful exit dengan Ctrl+C
- Test error handling: matikan internet, gunakan API key salah

---

## Execution Order

Saya akan membangun semua tahap secara berurutan:

1. **Foundation**: Struktur folder, `requirements.txt`, `.env.example`, `README.md`, `config.py`, `state.py`
2. **Core Text-Only**: `groq_service.py`, `prompt_builder.py`, `session_memory.py`, `interaction_loop.py`, prompt files
3. **Voice Output**: `elevenlabs_service.py`, `audio_player.py`, update interaction loop
4. **Voice Input**: `speech_service.py`, update interaction loop
5. **Vision**: `vision_service.py`, update prompt builder & interaction loop
6. **Utils & Polish**: `logger.py`, `file_manager.py`, `terminal_ui.py`, tests
