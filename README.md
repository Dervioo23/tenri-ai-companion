# Tenri AI Companion

Tenri adalah companion presentasi berbasis suara yang dapat mendengar presenter, memahami posisi slide, mengambil fakta dari knowledge base, lalu merespons sebagai karakter hidup. Persona Tenri terinspirasi oleh We Tenriabeng dan dunia `tursalahjalan.com`, dengan perhatian khusus pada arsip, ingatan kolektif, dan warisan budaya.

## Kemampuan Utama

- Percakapan suara dengan speech-to-text, intent classification, conversation window, dan koreksi istilah domain.
- LLM melalui Groq sebagai provider utama, dengan Gemini sebagai provider opsional.
- ElevenLabs TTS melalui REST API langsung, plus fallback TTS lokal atau Edge TTS.
- Retrieval berbasis BM25 dari PDF, DOCX, PPTX, Markdown, dan teks.
- Kesadaran narasi presentasi: slide aktif, topik yang sudah dibahas, dan slide berikutnya.
- Navigasi slide melalui suara, ambient trigger, interruption policy, dan mode debat berbasis sumber.
- JarvisDisplay dan terminal UI untuk status listening, thinking, speaking, slide, serta metrik latensi.
- Menu interaktif untuk menjalankan Tenri, mengimpor materi, rehearsal, dan mengelola knowledge base.
- Session log terpusat di `app/data/logs/`.

## Persyaratan

- Python 3.10 atau lebih baru.
- Microphone dan speaker.
- API key Groq untuk konfigurasi default.
- API key ElevenLabs bila TTS ElevenLabs diaktifkan.
- Camera hanya diperlukan bila vision diaktifkan.

## Instalasi

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Dependensi Gemini dan Edge TTS sengaja tidak dipasang pada instalasi inti:

```powershell
pip install -r requirements-optional.txt
```

Jangan commit `.env` atau API key ke repository.

## Konfigurasi Provider

Provider default adalah Groq:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Untuk Gemini, instal dependensi opsional lalu ubah konfigurasi:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.5-flash
```

ElevenLabs dipanggil melalui REST API menggunakan `requests`; paket SDK `elevenlabs` tidak diperlukan.

## Menjalankan Aplikasi

```powershell
python main.py
```

Menu utama menyediakan:

1. Jalankan Tenri.
2. Import Materi.
3. Rehearsal Simulasi.
4. Kelola Knowledge Base.
5. Keluar.

## Knowledge Base

Materi aktif dicatat di `app/knowledge/sources.json`. Folder kanonik untuk materi presentasi adalah `app/knowledge/presentations/`; `inbox/` hanya area masuk sementara sebelum impor selesai.

```powershell
python scripts/import_document.py "C:\materi\presentasi.pptx"
python scripts/manage_knowledge.py list
python scripts/manage_knowledge.py disable --id sumber-id
python scripts/manage_knowledge.py enable --id sumber-id
```

Importer mendukung `.pptx`, `.docx`, dan `.pdf`. Loader runtime juga mendukung `.md` dan `.txt`. Index retrieval tersimpan di `app/knowledge/indexes/` dan dibangun ulang ketika cache tidak tersedia atau rusak.

## Struktur Proyek

```text
ai-companion-terminal/
|-- main.py
|-- requirements.txt
|-- requirements-optional.txt
|-- app/
|   |-- config.py
|   |-- core/                  # interaction loop, prompt, memory
|   |-- services/              # LLM, STT, TTS, retrieval, intent, vision
|   |-- prompts/               # persona, aturan, contoh dialog
|   |-- presentation/          # slides dan ambient triggers
|   |-- knowledge/             # sumber, presentasi, index retrieval
|   |-- ui/                    # JarvisDisplay
|   |-- utils/                 # terminal, logging, text processing
|   `-- data/
|       |-- logs/              # app.log dan session_*.jsonl
|       `-- rehearsals/
|-- scripts/                   # import, rehearsal, knowledge management
`-- tests/                     # regression dan unit tests
```

## Pengujian

```powershell
pytest -q
```

Untuk demo live, uji microphone, provider LLM, TTS, navigasi slide, dan materi aktif sebelum presentasi. Kelulusan unit test tidak membuktikan bahwa latensi jaringan dan perangkat audio di lokasi acara akan stabil.
