# Panduan Lengkap: Setup & Penggunaan Tenri AI Companion

Tenri adalah AI companion berbasis suara untuk presentasi. Ia mendengarkan pembicaraan
presenter secara real-time, menjawab pertanyaan dari audiens, nimbrung dengan komentar
atau sanggahan berbasis dokumen yang Anda berikan, dan berbicara dengan suara alami
menggunakan Text-to-Speech.

---

## Daftar Isi

1. [Persyaratan Sistem](#1-persyaratan-sistem)
2. [Instalasi Python](#2-instalasi-python)
3. [Instalasi Visual Studio Code](#3-instalasi-visual-studio-code)
4. [Setup Project di VS Code](#4-setup-project-di-vs-code)
5. [Instalasi Library](#5-instalasi-library)
6. [Konfigurasi API Key](#6-konfigurasi-api-key)
7. [Konfigurasi File .env](#7-konfigurasi-file-env)
8. [Setup Mikrofon](#8-setup-mikrofon)
9. [Import Materi Presentasi (PPT / Word / PDF)](#9-import-materi-presentasi-ppt--word--pdf)
10. [Setup Slide dan Trigger](#10-setup-slide-dan-trigger)
11. [Cara Menjalankan Tenri](#11-cara-menjalankan-tenri)
12. [Cara Berbicara dengan Tenri](#12-cara-berbicara-dengan-tenri)
13. [Kelola Knowledge Base](#13-kelola-knowledge-base)
14. [Mode Live Presentasi](#14-mode-live-presentasi)
15. [Troubleshooting](#15-troubleshooting)
16. [Referensi Cepat Semua Setting .env](#16-referensi-cepat-semua-setting-env)

---

## 1. Persyaratan Sistem

| Komponen | Minimum |
|----------|---------|
| OS | Windows 10/11 (64-bit) |
| RAM | 4 GB (8 GB disarankan) |
| Python | 3.10 atau lebih baru (disarankan 3.13) |
| Koneksi Internet | Diperlukan untuk Groq API dan ElevenLabs |
| Mikrofon | Diperlukan untuk input suara |
| Speaker / Headphone | Diperlukan untuk output suara Tenri |

---

## 2. Instalasi Python

### Langkah 1 — Download Python

Buka browser, pergi ke: **https://python.org/downloads**

Klik **"Download Python 3.13.x"** (versi terbaru yang tersedia).

### Langkah 2 — Jalankan Installer

1. Buka file installer yang sudah didownload (contoh: `python-3.13.5-amd64.exe`)
2. **PENTING:** Centang kotak **"Add Python to PATH"** di bagian bawah sebelum klik Install
3. Klik **"Install Now"**
4. Tunggu hingga selesai, lalu klik **"Close"**

### Langkah 3 — Verifikasi

Buka **Command Prompt** (tekan `Win + R`, ketik `cmd`, Enter) lalu jalankan:

```
python --version
```

Hasilnya harus seperti: `Python 3.13.5`

Jika muncul error "python tidak dikenali", coba restart komputer lalu ulangi.

---

## 3. Instalasi Visual Studio Code

### Langkah 1 — Download VS Code

Buka: **https://code.visualstudio.com/download**

Pilih versi **Windows x64** dan download.

### Langkah 2 — Install

1. Jalankan installer yang didownload
2. Setujui license agreement
3. Centang semua opsi "Add to PATH" dan "Register Code as editor for..."
4. Klik **Install** dan tunggu selesai

### Langkah 3 — Install Extension Python

1. Buka VS Code
2. Klik ikon **Extensions** di sidebar kiri (atau tekan `Ctrl+Shift+X`)
3. Cari **"Python"** (oleh Microsoft) → klik **Install**
4. Cari **"Pylance"** (oleh Microsoft) → klik **Install** (untuk autocomplete lebih baik)

---

## 4. Setup Project di VS Code

### Langkah 1 — Buka Folder Project

1. Buka VS Code
2. Klik **File → Open Folder...**
3. Pilih folder `c:\ai-companion-terminal`
4. Klik **"Select Folder"**

### Langkah 2 — Buat Virtual Environment

Virtual environment memisahkan library project ini dari Python global di komputer Anda.

1. Buka terminal di VS Code: tekan `Ctrl+`` ` (backtick/tanda petik terbalik)
2. Jalankan perintah berikut:

```powershell
python -m venv .venv
```

Ini membuat folder `.venv` di dalam project.

### Langkah 3 — Aktifkan Virtual Environment

```powershell
.venv\Scripts\activate
```

Setelah berhasil, di awal baris terminal akan muncul tulisan `(.venv)`.

### Langkah 4 — Pilih Python Interpreter di VS Code

1. Tekan `Ctrl+Shift+P` untuk membuka Command Palette
2. Ketik: `Python: Select Interpreter`
3. Pilih opsi yang menunjukkan `.venv` (biasanya tertulis `.\.venv\Scripts\python.exe`)

---

## 5. Instalasi Library

Pastikan virtual environment sudah aktif (ada tulisan `(.venv)` di terminal), lalu jalankan:

```powershell
pip install -r requirements.txt
```

Proses ini mengunduh dan menginstal semua library yang dibutuhkan. Butuh waktu
3–10 menit tergantung kecepatan internet.

### Catatan Khusus: PyAudio di Windows

PyAudio memerlukan langkah tambahan di Windows. Jika instalasi di atas gagal
dengan error terkait PyAudio, gunakan cara ini:

```powershell
pip install pipwin
pipwin install pyaudio
```

Jika `pipwin` juga gagal, download file `.whl` PyAudio secara manual:

1. Buka: **https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio**
2. Download file sesuai versi Python Anda (contoh: `PyAudio-0.2.14-cp313-cp313-win_amd64.whl`)
3. Install dengan: `pip install PyAudio-0.2.14-cp313-cp313-win_amd64.whl`

### Verifikasi Instalasi

```powershell
python -m pytest tests/ -q
```

Jika berhasil, akan muncul: `376 passed` (atau sejumlah angka tanpa tulisan `FAILED`).

---

## 6. Konfigurasi API Key

Tenri membutuhkan dua API key: satu untuk otak AI (Groq) dan satu untuk suara (ElevenLabs).

### 6.1 Groq API Key (Otak AI + Speech-to-Text)

Groq digunakan untuk dua hal: memproses percakapan (LLM) dan mentranskrip suara
Anda menjadi teks (Whisper STT). **Gratis untuk penggunaan wajar.**

1. Buka: **https://console.groq.com/**
2. Daftar akun atau login
3. Klik **"API Keys"** di menu kiri
4. Klik **"Create API Key"**
5. Beri nama (contoh: "tenri-companion")
6. Salin API key yang muncul (format: `gsk_xxx...`)

### 6.2 ElevenLabs API Key (Suara Tenri)

ElevenLabs mengubah teks jawaban Tenri menjadi suara yang natural.

1. Buka: **https://elevenlabs.io/**
2. Daftar akun atau login
3. Klik foto profil di pojok kanan atas → **"Profile + API key"**
4. Salin **API Key** yang tertera

### 6.3 ElevenLabs Voice ID (ID Suara Tenri)

Voice ID menentukan karakter suara yang dipakai Tenri.

**Menggunakan suara bawaan:**

Di dashboard ElevenLabs, klik **"Voice Library"** dan pilih suara yang Anda suka.
Klik nama suara tersebut, lalu salin ID-nya dari URL halaman (format: `hpp4J3Vq...`).

**Menggunakan suara kustom (direkomendasikan untuk presentasi):**

1. Di ElevenLabs, klik **"Add Generative or Cloned Voice"**
2. Pilih **"Voice Design"** untuk membuat suara dari deskripsi, atau
   **"Instant Voice Cloning"** untuk kloning dari rekaman suara
3. Setelah dibuat, salin Voice ID dari halaman detail suara

---

## 7. Konfigurasi File .env

File `.env` adalah file konfigurasi utama yang menyimpan semua pengaturan Tenri,
termasuk API key dan pengaturan suara.

### Langkah 1 — Buka File .env

Di VS Code, klik file `.env` di sidebar kiri. Isinya sudah ada templatenya.

### Langkah 2 — Isi API Key

Ganti nilai yang kosong atau default dengan milik Anda:

```
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=isi_voice_id_di_sini
```

### Langkah 3 — Pengaturan Dasar

Bagian ini sudah dikonfigurasi dengan baik untuk penggunaan umum.
Anda cukup memastikan nilai-nilai ini sesuai kebutuhan:

```
# Bahasa utama
APP_LANGUAGE=id

# Aktifkan input suara dan output suara
VOICE_INPUT_ENABLED=true
VOICE_OUTPUT_ENABLED=true

# Mode input: false = auto-listen (wake word), true = tekan Enter dulu
PUSH_TO_TALK_ENABLED=false

# Wake words — kata yang diucapkan untuk memanggil Tenri
WAKE_WORDS=tenri,halo tenri,hai tenri,ok tenri,hey tenri
```

### Langkah 4 — Simpan File

Tekan `Ctrl+S` untuk menyimpan.

---

## 8. Setup Mikrofon

### Cek Index Mikrofon

Jalankan perintah ini di terminal VS Code untuk melihat daftar mikrofon:

```powershell
python -c "import speech_recognition as sr; [print(i, name) for i, name in enumerate(sr.Microphone.list_microphone_names())]"
```

Output contoh:
```
0 Microsoft Sound Mapper - Input
1 Realtek HD Audio Mic input
2 Headset Microphone (Logitech)
3 ...
```

Catat angka (index) di depan nama mikrofon yang ingin Anda gunakan.

### Set Index Mikrofon di .env

```
MIC_DEVICE_INDEX=2
```

Ganti `2` dengan index mikrofon Anda. Biarkan kosong (`MIC_DEVICE_INDEX=`) untuk
menggunakan mikrofon default sistem.

### Kalibrasi Energy Threshold

Jika Tenri terlalu sensitif (mendengar noise) atau kurang sensitif (tidak mendengar suara Anda):

```
SPEECH_ENERGY_THRESHOLD=500
```

- Turunkan nilai (contoh: 300) jika Tenri tidak mendengar suara Anda
- Naikkan nilai (contoh: 700) jika Tenri terlalu sering aktif karena noise

---

## 9. Import Materi Presentasi (PPT / Word / PDF)

Tenri menjawab pertanyaan berdasarkan dokumen yang Anda berikan. Anda perlu
mengimpor materi terlebih dahulu agar Tenri tahu apa yang akan dibahas.

### Format yang Didukung

| Format | Ekstensi |
|--------|----------|
| PowerPoint | `.pptx` |
| Word | `.docx` |
| PDF | `.pdf` |
| Teks | `.txt`, `.md` |

### Cara Import via Menu Utama

1. Jalankan aplikasi:
   ```powershell
   python main.py
   ```

2. Pilih **[2] Import Materi**

3. Masukkan path file dokumen Anda. Contoh:
   ```
   C:\Users\Anda\Documents\Presentasi-AI.pptx
   ```

4. Masukkan judul untuk dokumen ini (contoh: `Presentasi AI`)

5. Sistem akan memproses dokumen: mengekstrak teks, memecah menjadi potongan,
   dan menyimpan index ke `app/knowledge/indexes/`

6. Setelah selesai, dokumen terdaftar di `app/knowledge/sources.json` dengan
   status `active` dan siap digunakan Tenri

### Cara Import via Script Langsung

Untuk import cepat tanpa menu interaktif:

```powershell
python scripts/import_document.py
```

### Cara Import Manual (Drag & Drop ke Inbox)

Anda juga bisa menaruh file langsung ke folder:

```
app/knowledge/inbox/
```

Lalu jalankan import dari menu utama. Sistem akan otomatis mendeteksi file
baru di folder inbox.

### Memverifikasi Import Berhasil

Buka file `app/knowledge/sources.json` dan pastikan dokumen Anda terdaftar
dengan `"status": "active"`:

```json
{
  "id": "presentasi-ai",
  "title": "Presentasi AI",
  "type": "presentation",
  "status": "active",
  "versions": [
    {
      "version": "v1",
      "path": "presentations/Presentasi-AI.pptx",
      "status": "active"
    }
  ]
}
```

---

## 10. Setup Slide dan Trigger

Ini adalah bagian opsional tapi sangat disarankan agar Tenri bisa nimbrung
secara otomatis di momen yang tepat selama presentasi.

### 10.1 File slides.json — Metadata Slide

File ini ada di: `app/presentation/slides.json`

Setiap slide didefinisikan seperti ini:

```json
[
  {
    "id": 1,
    "title": "PENGENALAN AI",
    "subtitle": "Apa itu Kecerdasan Buatan?",
    "topics": ["AI", "kecerdasan buatan", "machine learning"],
    "presenter_notes": "Slide ini memperkenalkan konsep dasar AI kepada mahasiswa.",
    "tenri_role": "Beri komentar tentang relevansi AI dalam kehidupan sehari-hari.",
    "expected_tenri_mode": "comment",
    "triggers": ["pengenalan AI", "kecerdasan buatan", "apa itu AI"]
  },
  {
    "id": 2,
    "title": "CARA KERJA AI",
    "subtitle": "Dari Data ke Keputusan",
    "topics": ["data", "algoritma", "neural network"],
    "presenter_notes": "Penjelasan teknis cara AI belajar dari data.",
    "tenri_role": "Koreksi jika ada penyederhanaan berlebih.",
    "expected_tenri_mode": "gentle_objection",
    "triggers": ["cara kerja", "neural network", "data training"]
  }
]
```

**Kolom penting:**

| Kolom | Keterangan |
|-------|-----------|
| `id` | Nomor urut slide (integer) |
| `title` | Judul slide sesuai PPT |
| `topics` | Kata kunci utama slide ini |
| `presenter_notes` | Catatan untuk Tenri tentang konten slide |
| `tenri_role` | Instruksi apa yang Tenri lakukan di slide ini |
| `expected_tenri_mode` | Mode respons: `comment`, `gentle_objection`, `question`, `fact` |
| `triggers` | Kata yang jika diucapkan presenter akan mengaktifkan slide ini |

### 10.2 File triggers.json — Kapan Tenri Nimbrung Otomatis

File ini ada di: `app/presentation/triggers.json`

Trigger menentukan kapan Tenri berbicara **tanpa dipanggil**:

```json
[
  {
    "id": "t001",
    "patterns": ["kecerdasan buatan", "AI", "pengenalan teknologi"],
    "topic": "Pengenalan AI",
    "mode": "comment",
    "slide_ids": [1],
    "cooldown_seconds": 120,
    "suggested_response_intent": "Beri komentar singkat tentang relevansi AI. Maksimal 2 kalimat."
  },
  {
    "id": "t002",
    "patterns": ["AI menggantikan manusia", "robot lebih pintar"],
    "topic": "Mitos tentang AI",
    "mode": "gentle_objection",
    "slide_ids": [2],
    "cooldown_seconds": 90,
    "suggested_response_intent": "Luruskan mitos ini dengan fakta dari knowledge base."
  }
]
```

**Kolom penting:**

| Kolom | Keterangan |
|-------|-----------|
| `id` | ID unik trigger (string, contoh: `t001`) |
| `patterns` | Kata/frasa yang jika terdeteksi akan memicu Tenri |
| `mode` | Cara Tenri merespons (lihat tabel di bawah) |
| `slide_ids` | Slide mana yang terkait trigger ini |
| `cooldown_seconds` | Jeda minimal antar trigger yang sama (dalam detik) |
| `suggested_response_intent` | Panduan untuk Tenri saat membuat respons |

**Mode yang tersedia:**

| Mode | Kapan Digunakan |
|------|----------------|
| `comment` | Tambahkan komentar yang relevan |
| `gentle_objection` | Sanggah dengan sopan jika ada yang kurang tepat |
| `question` | Ajukan pertanyaan yang memancing diskusi |
| `fact` | Sampaikan fakta dari dokumen |
| `debate` | Tantang klaim dengan data dari knowledge base |

### 10.3 Navigasi Slide dengan Suara

Selama presentasi, Anda bisa pindah slide hanya dengan bicara:

| Ucapan | Aksi |
|--------|------|
| "lanjut slide" / "next" | Maju ke slide berikutnya |
| "mundur" / "kembali" | Kembali ke slide sebelumnya |
| "slide tiga" | Langsung ke slide nomor 3 |
| "status" | Tampilkan slide aktif saat ini |
| "list" | Tampilkan daftar semua slide |

---

## 11. Cara Menjalankan Tenri

### Langkah 1 — Aktifkan Virtual Environment

Buka terminal di VS Code (`Ctrl+`` `) dan jalankan:

```powershell
.venv\Scripts\activate
```

Pastikan ada tulisan `(.venv)` di awal baris terminal.

### Langkah 2 — Jalankan Aplikasi

```powershell
python main.py
```

### Langkah 3 — Pilih dari Menu

```
╔══════════════════════════════════╗
║   TENRI AI COMPANION TERMINAL    ║
╠══════════════════════════════════╣
║  [1] Jalankan Tenri              ║
║  [2] Import Materi               ║
║  [3] Rehearsal Simulasi          ║
║  [4] Kelola Knowledge Base       ║
║  [5] Keluar                      ║
╚══════════════════════════════════╝
```

Ketik `1` lalu tekan **Enter** untuk menjalankan Tenri.

### Langkah 4 — Tunggu Inisialisasi

Tenri akan memuat semua komponen. Proses ini membutuhkan beberapa detik:

```
Knowledge base loaded: 45 chunks.
ElevenLabs service ready (direct REST).
Groq Whisper STT initialized (model: whisper-large-v3-turbo).
BackgroundListener started — continuous capture aktif.
Pre-warming TTS cache...

Sistem aktif. Gunakan Ctrl+C untuk keluar dengan aman.
```

Setelah muncul **"Sistem aktif"**, Tenri siap digunakan.

### Menghentikan Tenri

Tekan **`Ctrl+C`** untuk menghentikan Tenri dengan aman. Sistem akan membersihkan
file temporary dan merilis hardware secara otomatis.

---

## 12. Cara Berbicara dengan Tenri

### Mode Auto-Listen (Default)

Dengan pengaturan default (`PUSH_TO_TALK_ENABLED=false`), Tenri mendengarkan
secara terus-menerus. Untuk memanggil Tenri, ucapkan salah satu **wake word**:

- **"Tenri"** — paling singkat
- **"Halo Tenri"** — lebih formal
- **"Hai Tenri"** / **"Hey Tenri"** — kasual
- **"Oke Tenri"** — sambil bilang oke

Contoh penggunaan lengkap:

```
Anda:  "Tenri, apa itu machine learning?"
Tenri: "Machine learning adalah sistem yang belajar dari data untuk menemukan
        pola tanpa diprogram secara eksplisit. Saya punya beberapa contoh
        dari slide yang kita bahas sekarang."
```

### Mode Push-to-Talk

Jika Anda mengatur `PUSH_TO_TALK_ENABLED=true` di `.env`:

1. Tekan **Enter** di terminal
2. Bicara
3. Diam sejenak (sekitar 0.5 detik) — Tenri akan mulai memproses

### Conversation Window

Setelah Tenri menjawab, Anda punya waktu **30 detik** untuk bertanya lagi
**tanpa perlu menyebut wake word**. Ini berguna untuk diskusi berlanjut:

```
Anda:  "Tenri, apa perbedaan AI dengan machine learning?"
Tenri: "..."
Anda:  "Terus, deep learning itu masuk kategori mana?"  ← tidak perlu sebut "Tenri"
Tenri: "..."
```

Setelah 30 detik diam, Tenri kembali ke mode standby dan Anda perlu
menyebut wake word lagi.

### Menutup Percakapan

Ucapkan salah satu frasa penutup untuk memberi tahu Tenri bahwa percakapan selesai:

- "Terima kasih"
- "Oke makasih"
- "Sudah cukup"
- "Cukup"

Tenri akan menjawab singkat lalu kembali ke mode monitoring.

---

## 13. Kelola Knowledge Base

### Lihat Semua Sumber

```powershell
python scripts/manage_knowledge.py list
```

### Tambah Dokumen Baru

```powershell
python scripts/manage_knowledge.py add --type presentation --title "Nama Dokumen" --file "C:\path\ke\file.pptx"
```

Tipe yang tersedia: `presentation`, `paper`, `book`, `project_note`, `archive`

### Ganti Versi Dokumen (Update)

Jika Anda punya versi baru dari presentasi yang sudah ada:

```powershell
python scripts/manage_knowledge.py replace --id id-dokumen --file "C:\path\ke\file_baru.pptx"
```

Versi lama akan diarsipkan secara otomatis.

### Nonaktifkan Dokumen

```powershell
python scripts/manage_knowledge.py disable --id id-dokumen
```

Dokumen tidak dihapus, hanya tidak dipakai Tenri sampai diaktifkan kembali.

### Aktifkan Kembali

```powershell
python scripts/manage_knowledge.py enable --id id-dokumen
```

---

## 14. Mode Live Presentasi

Untuk presentasi langsung di hadapan audiens, aktifkan **LIVE_RESPONSE_MODE**
agar Tenri memberikan respons lebih singkat dan cepat.

Edit file `.env`:

```
LIVE_RESPONSE_MODE=true
```

Dengan mode ini:
- Tenri hanya menjawab maksimal **1 kalimat**
- Proses generasi lebih cepat (~60% lebih cepat)
- Tidak ada jawaban panjang yang mengganggu alur presentasi

Kembali ke `false` saat rehearsal atau diskusi santai agar jawaban lebih lengkap.

---

## 15. Troubleshooting

### Tenri Tidak Mendengar Suara Saya

1. Cek MIC_DEVICE_INDEX — pastikan index sesuai mikrofon yang terpasang
2. Turunkan SPEECH_ENERGY_THRESHOLD (dari 500 menjadi 300)
3. Pastikan mikrofon tidak di-mute di Windows Sound Settings
4. Coba jalankan: `python -c "import speech_recognition as sr; r = sr.Recognizer(); m = sr.Microphone(); print('Mic OK')"` — jika error, PyAudio belum terinstal

### Suara Tenri Bergema / Didengar Ulang Sebagai Input

Sistem sudah memiliki perlindungan otomatis dari echo. Jika masih terjadi:

1. Gunakan **headset** agar speaker tidak masuk ke mikrofon
2. Kurangi volume speaker
3. Jika masih bermasalah, naikkan nilai `_POST_UNMUTE_BUFFER` di
   `app/services/background_listener.py` (dari 2.2 menjadi 3.0)

### Error "Rate Limit" dari Groq

Groq free tier memiliki batas token harian. Jika muncul pesan rate limit:
- Tunggu beberapa menit lalu coba lagi
- Atau upgrade ke Groq paid tier di console.groq.com

### ElevenLabs Tidak Menghasilkan Suara

1. Pastikan ELEVENLABS_API_KEY dan ELEVENLABS_VOICE_ID sudah benar di `.env`
2. Cek saldo karakter ElevenLabs di dashboard (free tier punya batas bulanan)
3. Aktifkan fallback TTS gratis dengan mengubah di `.env`:
   ```
   LOCAL_TTS_ENABLED=true
   LOCAL_TTS_VOICE=id-ID-GadisNeural
   ```
   Lalu install: `pip install edge-tts`

### Respons Tenri Lambat

1. Pastikan `GROQ_STREAMING=true` di `.env` (sudah default)
2. Aktifkan `LIVE_RESPONSE_MODE=true` untuk respons 1 kalimat yang lebih cepat
3. Turunkan `LLM_MAX_TOKENS` dari 250 ke 150

### Import Dokumen Gagal

1. Pastikan file tidak sedang dibuka oleh aplikasi lain (tutup PowerPoint dulu)
2. Pastikan path file tidak mengandung karakter khusus
3. Cek apakah library terinstal: `pip install pdfplumber python-docx python-pptx`

### Whisper Mentranskripsi Hal yang Salah

1. Bicara lebih jelas dan tidak terlalu cepat
2. Kurangi noise latar belakang
3. Pastikan `SPEECH_STT_ENGINE=groq` di `.env` (Groq Whisper lebih akurat dari Google)
4. Cek log di `app/data/logs/` untuk melihat apa yang ditangkap mikrofon

### Tests Gagal

Jalankan ulang dari virtual environment yang aktif:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## 16. Referensi Cepat Semua Setting .env

```
# ─── API Keys ─────────────────────────────────────────────────────────────
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile    # Model LLM Groq
GROQ_STT_MODEL=whisper-large-v3-turbo # Model STT Groq
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=   # Wajib: ID suara dari dashboard ElevenLabs
ELEVENLABS_MODEL=eleven_turbo_v2_5    # Model TTS (paling cepat)

# ─── Fitur Utama ───────────────────────────────────────────────────────────
VOICE_INPUT_ENABLED=true    # true = gunakan mikrofon
VOICE_OUTPUT_ENABLED=true   # true = Tenri berbicara
PUSH_TO_TALK_ENABLED=false  # false = auto-listen; true = tekan Enter dulu
WAKE_WORDS=tenri,halo tenri,hai tenri,ok tenri,hey tenri

# ─── Mode Respons ─────────────────────────────────────────────────────────
GROQ_STREAMING=true         # true = respons lebih cepat (streaming)
LIVE_RESPONSE_MODE=false    # true = 1 kalimat saja (untuk demo live)
LLM_MAX_TOKENS=250          # Panjang maksimal respons

# ─── Mikrofon ─────────────────────────────────────────────────────────────
MIC_DEVICE_INDEX=           # Index mikrofon (kosong = default sistem)
SPEECH_ENERGY_THRESHOLD=500 # Sensitivitas mikrofon (300-700)
SPEECH_DYNAMIC_ENERGY=false # true = threshold auto-adjust
SPEECH_STT_ENGINE=groq      # groq = Whisper (lebih akurat), google = Google STT
SPEECH_PAUSE_THRESHOLD=0.55 # Detik diam sebelum rekaman berhenti
SPEECH_TIMEOUT=7.0          # Maksimal waktu tunggu suara (detik)
SPEECH_PHRASE_TIME_LIMIT=8.0 # Maksimal durasi rekaman per kalimat

# ─── TTS Fallback (offline, gratis) ──────────────────────────────────────
LOCAL_TTS_ENABLED=false          # true = pakai edge-tts (butuh: pip install edge-tts)
LOCAL_TTS_VOICE=id-ID-GadisNeural # Suara: GadisNeural (wanita) atau ArdiNeural (pria)

# ─── Percakapan ───────────────────────────────────────────────────────────
CONVERSATION_WINDOW=30      # Detik follow-up tanpa wake word
MEMORY_MAX_EXCHANGES=10     # Jumlah percakapan yang diingat

# ─── Bahasa ───────────────────────────────────────────────────────────────
APP_LANGUAGE=id             # id = Indonesia, en = English, bilingual = keduanya

# ─── Fitur Opsional ───────────────────────────────────────────────────────
VISION_ENABLED=false        # true = deteksi wajah via kamera (butuh webcam)
VAD_ENABLED=true            # true = continuous listening (direkomendasikan)
LOCAL_INTENT_CLASSIFIER=true # true = klasifikasi intent offline
```

---

## Struktur Folder Singkat

```
ai-companion-terminal/
├── main.py                         ← Titik masuk utama, jalankan ini
├── .env                            ← Konfigurasi dan API key (JANGAN dibagikan)
├── requirements.txt                ← Daftar library Python
│
├── app/
│   ├── knowledge/
│   │   ├── sources.json            ← Registry dokumen yang aktif
│   │   ├── inbox/                  ← Taruh file baru di sini untuk diimport
│   │   ├── indexes/                ← Cache index dokumen (otomatis)
│   │   └── presentations/          ← Dokumen yang sudah diimport tersimpan di sini
│   │
│   ├── presentation/
│   │   ├── slides.json             ← Definisi metadata setiap slide
│   │   └── triggers.json           ← Trigger kapan Tenri nimbrung otomatis
│   │
│   └── prompts/
│       ├── character_prompt.txt    ← Kepribadian dan latar belakang Tenri
│       ├── system_rules.txt        ← Aturan-aturan yang harus diikuti Tenri
│       └── examples_tenri_dialogue.txt ← Contoh dialog untuk referensi gaya bicara
│
└── scripts/
    ├── import_document.py          ← Import dokumen ke knowledge base
    └── manage_knowledge.py         ← Kelola sumber pengetahuan
```

---

*Dokumentasi ini dibuat untuk Tenri AI Companion Terminal.*
*Untuk pertanyaan teknis, lihat file `TENRI_ENGINEERING.md` di folder project.*
