# Rencana Implementasi — Tenri Web (Lintas Platform, BYOK)

Dokumen ini adalah rencana mengubah Tenri dari aplikasi terminal Python single-user
menjadi **web app lintas platform** (Windows, Android, MacBook — apa pun yang punya
browser) yang **bisa dipakai banyak orang**, dengan model **BYOK (Bring Your Own Key)**:
tiap pengguna memakai API key Groq & ElevenLabs miliknya sendiri.

> Keputusan inti yang sudah disepakati:
> 1. **Web app**, bukan port Python ke Vercel (Vercel tak bisa menjalankan loop audio persisten).
> 2. **BYOK Cara A** — API key **tetap di browser**, tidak pernah menyentuh server kita.
> 3. **Frontend** di Vercel, **backend "otak"** di host always-on (Render/Railway).
> 4. **Otak Tenri yang sudah ada dipakai ulang** (RAG, intent, grounding, prompt) — bukan ditulis ulang.
> 5. Opsional: **demo-key terbatas** milik kita untuk awam mencoba instan.

---

## 1. Arsitektur

```
┌─ FRONTEND — Next.js @ Vercel ─────────────┐        ┌─ BACKEND "OTAK" — FastAPI @ Render/Railway ─┐
│ • Tangkap mic (getUserMedia/MediaRecorder)│        │ • Intent classifier (hybrid addressee)      │
│ • VAD di browser (@ricky0123/vad-web)     │ HTTPS  │ • Retrieval BM25 + knowledge base           │
│ • Putar audio (Web Audio API)             │◄──────►│ • Query rewriter                            │
│ • UI: chat, slide, tombol bicara          │  /route│ • Answer grounding (verifier)               │
│ • SIMPAN API KEY (sessionStorage/memori)  │ /verify│ • Prompt builder + slide/trigger state      │
│ • Orkestrasi giliran percakapan           │        │ • TANPA API KEY, TANPA audio, stateless     │
└───────────────┬───────────────────────────┘        └─────────────────────────────────────────────┘
                │ (pakai API KEY pengguna, langsung)
                ▼
        ┌─ PROVIDERS ───────────────────────────────┐
        │ Groq  : Whisper STT + LLM (llama/kimi)     │
        │ ElevenLabs : TTS (WebSocket streaming)     │
        └────────────────────────────────────────────┘
```

**Prinsip pembagian:**
- **Backend = fungsi murni atas teks + basis pengetahuan.** Tak butuh key, tak menyentuh audio, tak menyimpan rahasia. Stateless (riwayat dikirim per request).
- **Browser = audio + panggilan provider berkunci.** STT, LLM, TTS, VAD, playback — semua di sisi klien dengan key pengguna.
- **API key pengguna tidak pernah lewat server kita** (selama CORS provider mengizinkan; lihat Risiko R1).

---

## 2. Alur data satu giliran (BYOK Cara A)

```
1. Pengguna tekan tombol & bicara
   └─ Browser rekam audio (16 kHz mono PCM/webm)

2. Browser ─► Groq Whisper (key pengguna)            → transkrip            [STT di browser]

3. Browser ─► POST /route (backend)
      body: { transcript, slide_id, history[], in_conversation, quiet_mode }
      ◄─ resp: { action, prompt_messages[], context_str, slide_update, new_conv_state }
      (backend: intent → slide command → query rewrite → retrieval → prompt)

4. Jika action == "answer":
   Browser ─► Groq LLM (key pengguna, streaming)     → teks jawaban (token demi token)

5. (Opsional, fase 2+) Browser ─► POST /verify { response, context_str }
      ◄─ { final_text, overridden }                  → grounding check

6. Browser ─► ElevenLabs WS (key pengguna)           → PCM → Web Audio playback

7. Browser update riwayat + state percakapan (conversation window, quiet_mode) lokal
```

Catatan: **riwayat & state percakapan disimpan di klien** dan dikirim tiap giliran, sehingga
backend tetap stateless dan mudah diskalakan. Hybrid addressee model (buka dengan nama →
tanggapi debat; tutup dengan "terima kasih") berjalan persis seperti versi terminal —
flag `in_conversation`/`quiet_mode` dihitung di klien dari timestamp & dikirim ke `/route`.

---

## 3. Reuse — apa yang dipakai ulang dari kode sekarang

Inti "otak" Tenri sudah berupa Python murni dan **pindah langsung** ke FastAPI:

| Modul sekarang | Nasib di web |
|---|---|
| `app/services/intent_classifier.py` | ✅ Dipakai ulang apa adanya (hybrid addressee) |
| `app/services/retrieval.py` (BM25) | ✅ Dipakai ulang |
| `app/services/answer_verifier.py` | ✅ Dipakai ulang (grounding coverage) |
| `app/core/prompt_builder.py` | ✅ Dipakai ulang |
| `app/services/query_rewriter.py` | ✅ Dipakai ulang |
| `app/services/document_loader.py`, slides/triggers JSON | ✅ Dipakai ulang (basis pengetahuan) |
| `app/services/presentation_tracker.py`, `trigger_service.py` | ✅ Dipakai ulang (logika slide) |
| `app/config.py` | ◑ Dipangkas: buang audio/device, sisakan parameter otak |
| `vad_listener.py`, `silero_vad.py` | ↪ Konsep pindah ke **browser** (`@ricky0123/vad-web` = Silero WASM) |
| `streaming_tts.py` (ElevenLabs WS) | ↪ Pola sama, dipanggil dari **browser** |
| `speech_service.py` (STT), `audio_player.py` | ↪ Diganti Web Audio + Groq STT browser |
| `interaction_loop.py` | ↪ Dipecah: logika murni → endpoint backend; orkestrasi → klien |

**Artinya kerja keras sesi-sesi lalu (VAD, grounding, hybrid addressee, closing, depth-on-demand)
tidak terbuang — semuanya tetap relevan.**

---

## 4. Stack teknologi

**Frontend (Vercel)**
- Next.js (App Router) + TypeScript + Tailwind
- `@ricky0123/vad-web` — Silero VAD di browser (WASM) untuk mode dengar-terus (fase 3)
- Web Audio API / `MediaRecorder` — capture & playback
- State: React + `sessionStorage` (khusus API key)

**Backend (Render / Railway / Fly.io — always-on)**
- FastAPI (Python) — membungkus otak Tenri yang sudah ada
- Endpoint REST: `/route`, `/verify`, `/health`, (`/slides` untuk metadata presentasi)
- Stateless; CORS dibatasi ke domain Vercel kita
- Tanpa rahasia provider (BYOK)

**Providers (dipanggil dari browser, key pengguna)**
- Groq: `POST /openai/v1/audio/transcriptions` (Whisper), `POST /openai/v1/chat/completions` (LLM, stream)
- ElevenLabs: `wss://api.elevenlabs.io/v1/text-to-speech/{voice}/stream-input`

---

## 5. Keamanan BYOK (wajib, jangan dilewati)

1. **Key disimpan di `sessionStorage` atau memori React saja** — **bukan** `localStorage`
   (hilang saat tab ditutup; mengurangi risiko pencurian).
2. **Key TIDAK PERNAH** dikirim/disimpan/di-log di backend atau database kita.
3. **HTTPS wajib** (otomatis di Vercel & Render).
4. **Mitigasi XSS**: jangan render HTML mentah, sanitasi input, CSP ketat — karena key ada di browser,
   celah XSS = key bisa dicuri.
5. **Validasi key** dengan 1 panggilan tes murah saat dimasukkan; tampilkan status jelas bila salah/limit.
6. **Backend CORS** dibatasi hanya ke origin frontend kita.
7. **Rate-limit ringan di backend** (per IP) — bukan untuk biaya API (itu nol), tapi melindungi server RAG dari spam.
8. Jelaskan ke pengguna dengan transparan: *"API key Anda disimpan hanya di browser Anda dan tidak pernah dikirim ke server kami."*

---

## 6. Tahapan implementasi

Setiap fase punya hasil yang bisa dipakai/diuji sendiri. Estimasi = perkiraan kerja fokus.

### Fase 0 — Ekstraksi backend "otak" (≈ 3–5 hari)
- Buat service FastAPI; impor modul otak yang ada (intent, retrieval, verifier, prompt, rewriter).
- Endpoint `/route` (terima transkrip+state → balas aksi+prompt+konteks) dan `/verify`.
- Muat basis pengetahuan (slides/triggers/sources) saat startup.
- **Verifikasi dini CORS provider** (lihat R1) dengan skrip kecil dari browser.
- Deploy ke Render. Uji dengan `curl`/REST client.
- **DoD:** `/route` mengembalikan keputusan & prompt yang benar untuk input contoh; teruji unit.

### Fase 1 — MVP push-to-talk + BYOK (≈ 5–7 hari)
- Next.js: halaman dengan **form input API key** (Groq + ElevenLabs) → simpan di sessionStorage + validasi.
- Tombol "Tahan untuk bicara" → rekam → Groq Whisper (browser) → transkrip.
- Kirim ke `/route` → jika `answer`, panggil Groq LLM (browser, non-stream dulu) → ElevenLabs TTS (browser) → putar.
- Tampilkan transkrip + jawaban + slide aktif.
- Deploy frontend ke Vercel.
- **DoD:** satu orang dengan key sendiri bisa: buka situs → masukkan key → tanya → dengar jawaban Tenri berpijak materi. Lintas Windows/Android/Mac browser.

### Fase 2 — Streaming (≈ 3–5 hari)
- LLM streaming (token) → potong per kalimat → TTS streaming WebSocket → putar saat tiba (first-voice ~cepat).
- `/verify` grounding per kalimat sebelum TTS (port logika `_stream_and_speak`).
- **DoD:** suara pertama terasa cepat; jawaban panjang mengalir, bukan menunggu utuh.

### Fase 3 — Mode dengar-terus + hybrid addressee (≈ 5–7 hari)
- Integrasi `@ricky0123/vad-web` (Silero WASM) → endpointing di browser, tanpa tombol.
- Wake word "Tenri" buka jendela percakapan; tanggapi pertanyaan+debat; "terima kasih" menutup.
- Anti-echo: mute saat Tenri bicara (atau anjuran headset, sama seperti versi terminal).
- **DoD:** alur penuh **buka → tanya/debat → tutup → diam → buka lagi** jalan di browser.

### Fase 4 — Multi-user, demo-key, polish (≈ 5–7 hari)
- Mode **demo-key** terbatas (rate-limit + cap harian) untuk coba instan tanpa key sendiri.
- Sesi per-pengguna terisolasi (riwayat di klien; backend stateless sudah aman).
- (Opsional) unggah presentasi sendiri (.pptx) → indeks per sesi.
- UI rapi, status koneksi, indikator state (LISTENING/THINKING/SPEAKING), aksesibilitas.
- **DoD:** orang awam bisa coba via demo-key; power user pasang key sendiri untuk unlimited.

**Total realistis Fase 0–3: ~3–4 minggu kerja fokus untuk produk yang benar-benar bisa dipakai.**

---

## 7. Multi-user & sesi
- Backend **stateless**: tak menyimpan sesi → mudah skalakan horizontal.
- Riwayat percakapan + state jendela (conversation window, quiet_mode) **disimpan di klien**, dikirim tiap `/route`.
- Untuk MVP: **satu presentasi bersama** (materi yang sudah diimpor). Unggah per-pengguna = peningkatan Fase 4.
- Singleton `state_manager`/`bg_listener` versi terminal **tidak dipakai** di web (digantikan state per-tab di browser).

---

## 8. Biaya & model demo-key hybrid
- **BYOK = biaya API kita $0.** Tiap pengguna bayar Groq/ElevenLabs sendiri.
- **Biaya kita hanya hosting**: Vercel (frontend, ada free tier) + backend kecil di Render/Railway (~$0–7/bulan tier murah).
- **Demo-key (opsional)**: key milik kita dengan **rate-limit ketat + cap harian** agar biaya terkendali; untuk menurunkan friksi awam. Power user → key sendiri (unlimited).

---

## 9. Struktur repo yang diusulkan

```
tenri/
├─ backend/                  # FastAPI "otak" (deploy ke Render/Railway)
│  ├─ app/                   # impor ulang modul otak: intent, retrieval, verifier, prompt, rewriter
│  ├─ api/                   # endpoint: route.py, verify.py, health.py
│  ├─ knowledge/             # slides.json, triggers.json, sources.json, presentations/
│  └─ requirements.txt
├─ frontend/                 # Next.js (deploy ke Vercel)
│  ├─ app/                   # halaman, komponen UI
│  ├─ lib/                   # klien Groq/ElevenLabs (pakai key pengguna), VAD, audio, orkestrasi giliran
│  └─ package.json
└─ IMPLEMENTATION_PLAN_WEB.md (dokumen ini)
```

> Versi terminal yang ada sekarang **tetap dipertahankan** sebagai referensi/“otak sumber”;
> backend mengimpor logikanya. Tidak perlu menghapus apa pun.

---

## 10. Risiko & mitigasi

| ID | Risiko | Mitigasi |
|---|---|---|
| **R1** | Provider (Groq/ElevenLabs) memblokir panggilan langsung dari browser (CORS) → Cara A gagal | **Verifikasi di Fase 0.** Bila diblokir: pakai **thin proxy stateless** di backend yang meneruskan request memakai key dari header pengguna — **tak menyimpan/men-log key** (tetap BYOK, hanya transit terenkripsi). |
| **R2** | Celah XSS membocorkan key di browser | CSP ketat, tanpa `dangerouslySetInnerHTML`, sanitasi, sessionStorage bukan localStorage |
| **R3** | Awam tak punya API key → adopsi rendah | Mode **demo-key** terbatas untuk coba instan |
| **R4** | Echo speaker→mic di mode dengar-terus | Anjuran headset (seperti versi terminal) + mute saat TTS; AEC browser sebagai opsi lanjutan |
| **R5** | Latency bertambah (browser→backend→provider) | Streaming (Fase 2); backend ringan & dekat region; retrieval BM25 hanya milidetik |
| **R6** | Penyalahgunaan server RAG | Rate-limit per IP di backend |

---

## 11. Langkah pertama bila disetujui
1. Buat folder `backend/` + FastAPI, salin modul otak, endpoint `/route` + `/verify`, uji lokal.
2. Skrip kecil verifikasi CORS Groq & ElevenLabs dari browser (tentukan Cara A vs thin-proxy).
3. Deploy backend ke Render; lanjut Fase 1 (frontend MVP push-to-talk + BYOK).

*Disusun sebagai titik mulai; tiap fase boleh disesuaikan setelah belajar dari fase sebelumnya.*
