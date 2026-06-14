# Pengujian Tenri di macOS

Dokumen ini memisahkan kompatibilitas software dari pengujian hardware. GitHub
Actions dapat membuktikan instalasi, import, model ONNX, Pygame, dan test suite.
Runner cloud tidak dapat membuktikan mikrofon, speaker, kamera, atau izin macOS.

## 1. Pengujian Otomatis

Workflow `.github/workflows/macos-compatibility.yml` menjalankan pengujian pada
Apple Silicon dan Intel macOS. Workflow dapat dijalankan manual dari tab
**Actions > macOS compatibility > Run workflow** setelah perubahan tersedia di
GitHub.

Workflow melakukan hal berikut:

1. Memasang Python 3.12 dan PortAudio.
2. Memasang dependensi inti dan opsional.
3. Menjalankan smoke test macOS tanpa API key.
4. Menjalankan seluruh test suite dengan `pytest`.

Status hijau membuktikan bahwa software dapat dipasang dan diuji di macOS.
Status tersebut belum membuktikan perangkat audio fisik bekerja.

## 2. Persiapan MacBook

Jalankan perintah berikut di Terminal:

```bash
xcode-select --install
brew install python@3.12 portaudio
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt -r requirements-optional.txt
cp .env.example .env
```

Isi API key di `.env`. Untuk pengujian awal gunakan konfigurasi aman berikut:

```dotenv
VOICE_INPUT_ENABLED=true
VOICE_OUTPUT_ENABLED=true
PUSH_TO_TALK_ENABLED=true
VISION_ENABLED=false
LOCAL_TTS_ENGINE=edge
SILERO_VAD_ENABLED=false
```

`LOCAL_TTS_ENGINE=sapi` tidak didukung di macOS. Gunakan ElevenLabs atau `edge`.

## 3. Smoke Test Lokal

```bash
source .venv/bin/activate
python scripts/check_macos_compatibility.py --require-macos
python -m pytest -q
```

Smoke test boleh memberikan peringatan apabila tidak ada mikrofon atau speaker,
tetapi tidak boleh menghasilkan baris `[FAIL]`.

## 4. Izin macOS

Buka **System Settings > Privacy & Security**, lalu berikan izin berikut kepada
Terminal atau aplikasi yang menjalankan Tenri:

- Microphone
- Camera, hanya jika `VISION_ENABLED=true`

Tutup dan buka kembali Terminal setelah mengubah izin.

## 5. Checklist Hardware

Jalankan `python main.py`, pilih **Jalankan Tenri**, lalu buktikan semua item:

- Jendela JarvisDisplay muncul dan dapat ditutup normal.
- Mikrofon menangkap satu pertanyaan push-to-talk dengan jelas.
- Groq Whisper atau Google STT menghasilkan transkripsi yang benar.
- Tenri memberikan jawaban berbasis knowledge base.
- Audio ElevenLabs atau Edge TTS terdengar melalui speaker.
- Audio Tenri tidak direkam kembali sebagai pertanyaan pengguna.
- Navigasi slide dan konteks slide aktif bekerja.
- Dengan `SILERO_VAD_ENABLED=true`, Silero dapat membuka dan menutup ucapan.
- Dengan `VISION_ENABLED=true`, kamera aktif setelah izin diberikan.
- `Ctrl+C` dan tombol tutup menghentikan proses tanpa menggantung.

Catat model MacBook, versi macOS, arsitektur (`uname -m`), perangkat audio, dan
hasil setiap item. Dukungan macOS baru layak disebut penuh setelah checklist ini
lulus pada sekurangnya satu MacBook Apple Silicon.
