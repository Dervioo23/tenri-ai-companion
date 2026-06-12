# Roadmap Optimasi Tenri — Dari Tambal Sulam ke Arsitektur yang Benar

Dokumen ini menjawab satu pertanyaan: bagaimana mengoptimalkan pendengaran, respon, ucapan, waktu mendengar, dan waktu respon Tenri secara fundamental — bukan menambah tambalan baru.

## Status eksekusi per 12 Juni 2026

Status di bawah membedakan implementasi kode dari bukti runtime. Sebuah tahap tidak disebut selesai hanya karena file atau feature flag sudah tersedia.

| Tahap | Status | Bukti dan keputusan |
|---|---|---|
| 0. Metrik p50/p95 | Selesai di kode dan terukur | Metrik per turn tersimpan di session log dan `scripts/report_latency.py` membaca 14 turn. Baseline ujung-bicara ke suara pertama: p50 2,92 detik, p95 5,04 detik. Target 2,0 detik belum tercapai. |
| 1. Silero VAD | Implementasi selesai, validasi perangkat belum lulus | `VadListener`, model ONNX, health check startup, dan fallback energi tersedia. Pada perangkat ini Silero belum stabil sehingga `.env` tetap memakai fallback `BackgroundListener`. Tahap ini belum boleh dinyatakan 100 persen. |
| 2. TTS WebSocket | Implementasi aktif, smoke test lulus | Streaming PCM, `auto_mode`, koneksi langsung tanpa proxy otomatis Windows, circuit breaker, fallback REST/local, dan metrik playback sudah tersedia. Smoke test WebSocket berhasil memainkan audio. Validasi p50/p95 baru harus dilakukan setelah rehearsal baru. |
| 3. Koneksi persisten dan paralelisasi | Bagian relevan selesai | Klien Groq LLM dan Whisper sudah persisten; ElevenLabs REST kini memakai `requests.Session`. Retrieval BM25 tidak diparalelkan karena p95 aktual hanya 0,01 detik, sehingga kompleksitas tambahan tidak punya manfaat terukur. |
| 4. Pipeline event-driven | Milestone 4A selesai, migrasi parsial | Capture sudah dipisahkan menjadi `CaptureStage`; event bus bertipe, trace JSONL tanpa transkrip, dan korpus audio regresi sudah aktif. Router, Brain, TTS, dan Player masih berjalan di `InteractionLoop`, sehingga Tahap 4 belum 100 persen dan barge-in belum diaktifkan. |
| 5. STT lokal | Belum dimulai | Evaluasi `faster-whisper` menunggu korpus audio rehearsal agar keputusan akurasi dan latensi berbasis data. |

Keputusan operasional saat ini: jalankan rehearsal baru dengan `ELEVENLABS_STREAMING=true`, kumpulkan sedikitnya 20 turn, lalu bandingkan p50/p95 baru. Milestone 4A sengaja hanya membangun batas komponen dan observability tanpa mengubah concurrency audio. Migrasi berikutnya adalah memindahkan Router dan Brain keluar dari `InteractionLoop`; barge-in menunggu jalur playback yang dapat dibatalkan dan strategi echo yang terbukti.

## Diagnosis jujur: kenapa kode Anda penuh tambalan

Lihat pola di codebase Anda sendiri: `_HALLUCINATION_PHRASES` (daftar hitam frasa), `_DOMAIN_GLOSSARY` (kamus salah-dengar), `_strip_echo` (pencocokan token gema), `_remove_repetition_loops`, `_AMBIGUOUS_HALLUCINATION_PHRASES`, filter RMS, filter durasi, filter no_speech_prob, filter suku-kata-pendek, filter karakter-tunggal. Itu sembilan lapis penyaring yang semuanya mengobati gejala dari **empat akar masalah yang sama**:

1. **Tidak ada VAD sungguhan.** Gerbang energi (`energy_threshold`) tidak bisa membedakan suara manusia dari suara apa pun yang keras. Maka noise lolos ke Whisper, Whisper berhalusinasi, dan Anda menulis daftar hitam baru tiap kali demo menemukan halusinasi baru. Daftar itu tidak akan pernah selesai.
2. **Audio half-duplex tanpa echo cancellation.** Mic dimatikan saat Tenri bicara (mute gate + buffer 2,2 detik + `_strip_echo`). Konsekuensinya: Tenri tuli selama dia bicara, presenter tidak bisa memotong, dan sisa gema tetap bocor lewat celah waktu callback.
3. **STT batch, bukan streaming.** Rekam dulu sampai selesai → upload → tunggu. Waktu mendengar = durasi bicara + 1,1 detik jeda (`pause_threshold`) + upload + transkripsi. Semua itu serial.
4. **TTS request-response, bukan streaming.** Tiap kalimat = satu request REST → tunggu MP3 utuh → baru bunyi. ElevenLabs punya WebSocket streaming yang mengeluarkan audio chunk pertama dalam ~200–400 ms; Anda tidak memakainya.

Selama empat hal ini tidak disentuh, setiap optimasi lain hanyalah memindahkan milidetik di pinggiran.

---

## Prinsip arah ke depan

**Setiap heuristik harus berubah menjadi data + pengukuran, bukan konstanta di kode.** Daftar halusinasi, glossary, threshold — semuanya seharusnya hidup di file konfigurasi/korpus yang diuji regresi terhadap rekaman audio nyata, bukan ditulis tangan di dalam `.py` setiap kali ada kejadian. Anda sudah punya fondasinya: `session_logger` menulis JSONL per sesi, dan logging latency per tahap sudah ada. Yang kurang adalah menjadikannya siklus: rekam → ukur → uji → ubah.

---

## TAHAP 0 — Ukur dulu (1 hari, prasyarat semuanya)

Anda tidak bisa mengoptimalkan apa yang tidak Anda lihat. Latency per tahap sudah dicatat di log, tapi tersebar. Buat satu hal: tulis **semua metrik per turn ke session JSONL** (wait, record, stt, retrieval, llm-first-token, tts-first-audio, playback) dan satu skrip kecil `scripts/report_latency.py` yang membaca semua sesi dan mencetak p50/p95 per tahap. Tetapkan anggaran: misal *ujung-bicara presenter → suara pertama Tenri ≤ 2,0 detik*. Setelah itu setiap perubahan di bawah bisa dibuktikan, bukan dirasa-rasa.

Hipotesis saya berdasarkan baca kode, urutan pemborosan terbesar Anda sekarang: (1) endpointing 1,1 s pause + ambient-adjust 0,8 s per turn di mode sequential, (2) TTS REST per kalimat ~0,8–1,5 s sebelum bunyi pertama, (3) upload+transkripsi Whisper ~1–2 s, (4) LLM first-token ~0,3–0,8 s (sudah bagus karena streaming). Validasi hipotesis ini dengan data Anda sendiri sebelum percaya saya.

## TAHAP 1 — Pendengaran: ganti gerbang energi dengan VAD sungguhan (dampak terbesar per usaha)

Pasang **Silero VAD** (model ONNX ~2 MB, jalan offline di CPU, <1 ms per frame 30 ms). Arsitekturnya: mic mengalir terus ke ring buffer → tiap frame 30 ms dicek Silero → ucapan dimulai saat probabilitas suara naik, diakhiri saat turun selama ~400–600 ms (hangover). Efek berantai:

- `pause_threshold` 1,1 s → efektif 0,4–0,6 s. **Hemat ±0,5–0,7 s tiap turn**, dan Tenri terasa "sigap".
- Noise, musik, dengung ruangan tidak pernah sampai ke Whisper → sebagian besar daftar halusinasi dan filter RMS/durasi bisa **dihapus**, bukan ditambah.
- `adjust_for_ambient_noise` per turn (0,8 s) tidak diperlukan lagi — VAD tidak bergantung threshold energi. Kalibrasi sekali di startup, selesai.

Ini menggantikan `BackgroundListener` berbasis `listen_in_background` (yang memakai endpointing energi bawaan SpeechRecognition) dengan loop capture sendiri via PyAudio. Sekitar 150–250 baris, dan menghapus lebih banyak baris tambalan daripada yang ditambahkannya.

## TAHAP 2 — Ucapan: TTS streaming WebSocket (dampak terasa paling "ajaib")

Ganti REST `text-to-speech` dengan **ElevenLabs WebSocket streaming** (`/v1/text-to-speech/{voice}/stream-input`): kirim token teks begitu keluar dari LLM, terima chunk audio PCM, putar lewat `sounddevice`/`pyaudio` stream (bukan pygame.mixer.music yang butuh file utuh). Hasilnya pipeline sejati: token LLM pertama → suara pertama dalam ~0,5 s total, dibanding sekarang yang menunggu satu kalimat penuh + satu file MP3 penuh. Arsitektur `_stream_and_speak` Anda yang sudah sentence-level membuatnya mudah dimigrasi — kontraknya sama, transportnya yang berubah.

Pertahankan cache SHA256 untuk frasa statis (itu desain yang benar), dan pertahankan SAPI/edge-tts sebagai fallback. Output format pindah ke `pcm_22050` agar tidak ada biaya decode MP3.

## TAHAP 3 — Waktu mendengar + respon: paralelkan yang sekarang serial

Setelah VAD ada, dua paralelisasi murah:

1. **Mulai upload STT saat VAD mendeteksi akhir ucapan**, jangan tunggu pipeline lain. Pakai satu `requests.Session`/klien Groq persisten supaya TLS handshake tidak dibayar tiap panggilan (sekarang setiap call berpotensi koneksi baru — periksa ini di Tahap 0).
2. **Jalankan retrieval BM25 dan pembangunan prompt secara overlap dengan TTS sapaan/aknowledgment** bila ada. BM25 Anda hanya beberapa milidetik, jadi fokusnya bukan retrieval — fokusnya jangan biarkan QueryRewriter + verifier + format berantai menunda first-token. Ukur dulu; kalau QueryRewriter menyumbang <10 ms, biarkan.

Untuk LLM sendiri Anda sudah benar (streaming + model live terpisah + prompt ringkas mode live). Sisa perbaikan di sisi LLM hanyalah disiplin: sistem prompt live jangan tumbuh, dan `max_tokens` tetap kecil.

## TAHAP 4 — Refactor arsitektur: dari loop sekuensial ke pipeline event-driven

Ini jawaban sesungguhnya untuk "bukan menambal, tapi memperbaiki untuk ke depan". `InteractionLoop.run()` Anda sekarang 450+ baris yang mencampur capture, routing, retrieval, LLM, TTS, playback, dan UI dalam satu while-loop. Setiap fitur baru menambah cabang if di tempat yang sama — itulah kenapa tambalan menumpuk di sana.

Bentuk targetnya: komponen independen yang terhubung lewat queue/event — `Mic → VAD → STT → Router(Intent) → Brain(RAG+LLM) → TTS → Player` — masing-masing punya antarmuka kecil, bisa diganti implementasinya (pola yang sudah Anda mulai di `llm_factory`, diperluas ke STT dan TTS), dan masing-masing melaporkan metriknya sendiri. Manfaat konkret yang tidak mungkin dicapai arsitektur sekarang:

- **Barge-in (presenter memotong Tenri).** Player tinggal di-stop ketika VAD mendeteksi suara presenter saat SPEAKING. Ini mustahil selama mic di-mute saat playback. Prasyaratnya echo cancellation: pakai modul AEC (speexdsp-python / WebRTC APM) dengan sinyal playback sebagai referensi — atau jalur pragmatis untuk panggung: presenter pakai headset/mic directional sehingga gema speaker tidak masuk mic, dan AEC tidak dibutuhkan sama sekali. Jujur: AEC software itu sulit; coba jalur hardware dulu.
- **Spekulasi.** Begitu transkrip parsial mengandung wake word, Brain bisa mulai retrieval sebelum ucapan selesai.
- **Testing per komponen dengan audio rekaman.** Kumpulkan rekaman WAV dari tiap rehearsal (kasus gagal: gema, noise, wake word di akhir). Jadikan korpus regresi: `pytest` memutar WAV ke pipeline STT+filter dan memastikan outputnya benar. Mulai sekarang, *setiap bug pendengaran baru wajib masuk korpus ini sebelum diperbaiki* — itulah mekanisme yang mengubah tambalan menjadi perbaikan permanen.

## TAHAP 5 — Kualitas pendengaran jangka panjang: pertimbangkan STT lokal

Groq Whisper bagus, tapi batch dan bergantung jaringan venue — risiko terbesar demo live Anda justru WiFi panggung. Evaluasi `faster-whisper` (CTranslate2) model `small`/`medium` lokal: di laptop ber-GPU bisa <1 s per ucapan, offline total, dan mendukung transkripsi incremental. Jadikan ia provider STT kedua di balik antarmuka yang sama (pola factory), lalu ukur akurasi+latency head-to-head dengan korpus audio Anda. Keputusan pakai data, bukan selera.

---

## Urutan eksekusi dan ekspektasi

| Tahap | Usaha | Hasil terukur yang diharapkan |
|---|---|---|
| 0. Metrik p50/p95 | 1 hari | Baseline; tahu musuh sebenarnya |
| 1. Silero VAD | 3–5 hari | −0,7–1,5 s waktu mendengar; hapus sebagian besar filter halusinasi |
| 2. TTS WebSocket | 3–5 hari | First-voice dari ~2–3 s → ~0,7–1,0 s |
| 3. Paralelisasi + koneksi persisten | 1–2 hari | −0,2–0,5 s |
| 4. Pipeline event-driven + korpus audio + barge-in | 2–4 minggu | Kemampuan baru, bukan cuma kecepatan; tambalan berhenti tumbuh |
| 5. STT lokal | 1 minggu evaluasi | Kekebalan terhadap jaringan venue |

Total realistis Tahap 0–3: sekitar dua minggu kerja fokus, dan itu sudah mengubah pengalaman dari "asisten yang menunggu giliran" menjadi "lawan bicara". Tahap 4 yang membuat proyek ini berumur panjang.

Satu peringatan terakhir, karena Anda minta dicermin: godaan terbesar Anda berdasarkan jejak kode adalah menambah fitur (JARVIS UI, rehearsal, trigger, verifier) sebelum fondasi audio beres. Fitur-fitur itu bagus, tapi penonton menilai Tenri dari dua hal saja: apakah dia mendengar dengan benar, dan seberapa cepat dia menjawab. Bereskan empat akar masalah di atas sebelum menulis fitur baru apa pun.
