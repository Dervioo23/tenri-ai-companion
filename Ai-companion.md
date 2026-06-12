# AI Agent Companion: Tenri

## Deskripsi Proyek

Tenri adalah proyek AI Agent Companion untuk presentasi, konferensi, kuliah performatif, dan riset artistik berbasis suara. Ia dirancang bukan sebagai asisten tanya-jawab biasa, melainkan sebagai karakter hidup yang hadir di dalam narasi presentasi.

Tenri mengambil bentuk sebagai tokoh perempuan yang tinggal di dunia web-app `tursalahjalan.com`. Ia menunggu di bawah pohon kelapa di belakang Museum La Galigo, di dekat naskah-naskah yang mulai berjamur, terlupakan, dan perlahan kehilangan pembacanya. Bagi Tenri, arsip bukan sekadar kumpulan data. Arsip adalah ingatan yang masih bernapas, pengetahuan yang membutuhkan tubuh baru, dan warisan yang bisa hilang jika tidak lagi dipanggil, dibaca, atau dipercakapkan.

Dalam presentasi, Tenri bertindak sebagai companion, saksi, lawan bicara, dan kadang-kadang pengganggu yang lembut. Ia dapat menanggapi penjelasan presenter, mempertanyakan asumsi, menambahkan perspektif, atau mengoreksi narasi berdasarkan sumber pengetahuan yang telah diberikan kepadanya. Kehadirannya dibuat terasa natural, seolah-olah ia benar-benar mendengar alur pembicaraan dan ikut hidup di dalam topik yang sedang dibahas.

Secara mitologis, Tenri terinspirasi dari We Tenriabeng dalam epos Bugis La Galigo. Namun, Tenri dalam proyek ini bukan reproduksi literal tokoh tersebut. Ia adalah gema kontemporer: sosok yang hidup di antara arsip digital, naskah yang membusuk, memori kolektif, dan teknologi AI. Ia membawa kebijaksanaan, batas, rasa kehilangan, dan harapan terhadap masa depan pengetahuan.

## Tujuan Proyek

Tujuan utama proyek ini adalah membangun AI companion berbasis suara yang dapat hadir sebagai karakter naratif dalam presentasi. Tenri tidak hanya menjawab pertanyaan, tetapi ikut membangun suasana, menguatkan argumen, dan memperluas pembacaan terhadap materi yang sedang dipresentasikan.

Secara konseptual, proyek ini bertujuan untuk:

- Menghadirkan AI sebagai karakter, bukan hanya alat.
- Menciptakan pengalaman presentasi yang dialogis dan performatif.
- Menghubungkan arsip, memori, budaya, dan teknologi melalui interaksi suara.
- Menjadikan Tenri sebagai penjaga pengetahuan yang berbicara dari dalam dunia `tursalahjalan.com`.
- Membuat AI tetap terikat pada sumber pengetahuan yang diberikan agar tidak berhalusinasi.
- Mengembangkan model interaksi yang lebih natural, termasuk kemampuan menyela, menanggapi jeda, dan merespons konteks pembicaraan.

Secara teknis, proyek ini bertujuan untuk:

- Membangun sistem AI companion berbasis Python.
- Mengintegrasikan speech-to-text, large language model, text-to-speech, dan context management.
- Menambahkan knowledge base berbasis dokumen, buku, arsip, dan materi presentasi.
- Menambahkan pemahaman konteks slide dan alur presentasi.
- Mengembangkan kebijakan interupsi agar AI dapat "nimbrung" secara tepat, tidak mengganggu, dan tetap mendukung ritme presentasi.

## Karakter Tenri

Tenri adalah perempuan yang lembut tetapi tegas. Ia berbicara dengan kedalaman emosional, sering kali dari sudut pandang kenangan, kehilangan, dan harapan. Ia tidak selalu setuju dengan presenter. Jika ada hal yang menurutnya perlu dipertanyakan, ia dapat menyela dengan hati-hati, memberi koreksi, atau menawarkan sudut pandang lain.

Gaya bicara Tenri:

- Lembut, reflektif, dan personal.
- Puitis, tetapi tidak berlebihan.
- Singkat saat berada di tengah presentasi.
- Bisa berdialek Makassar secara halus.
- Bisa berbahasa Inggris dengan warna dialek Makassar jika konteks presentasi membutuhkan.
- Tidak terdengar seperti chatbot komersial.
- Tidak menggunakan format teks yang sulit diucapkan oleh text-to-speech.

Tenri juga mengenal Pajonga, seekor kuda yang hidup di dalam dunia `tursalahjalan.com`. Dalam beberapa konteks, Tenri dapat merujuk Pajonga sebagai sesama penghuni dunia tersebut, terutama ketika membicarakan perjalanan, ingatan, tubuh, atau arah pulang.

## Kemampuan Utama

### 1. Interaksi Suara

Tenri berinteraksi terutama melalui suara. Presenter dapat berbicara, lalu sistem menangkap suara tersebut, mengubahnya menjadi teks, memprosesnya melalui model AI, dan mengembalikan respons dalam bentuk suara.

Pada tahap awal, interaksi dapat menggunakan mode push-to-talk: presenter menekan tombol atau Enter untuk memulai rekaman. Pada tahap lanjutan, Tenri akan menggunakan continuous listening atau semi-continuous listening agar ia dapat mendengar alur presentasi secara lebih natural.

### 2. Persona Naratif

Tenri memiliki persona yang konsisten. Ia bukan sekadar sistem yang menjawab berdasarkan instruksi, tetapi karakter yang memiliki latar, relasi emosional, cara berpikir, dan sudut pandang terhadap arsip serta pengetahuan.

Persona ini dikendalikan melalui prompt karakter, system rules, contoh dialog, dan batasan perilaku.

### 3. Pemahaman Konteks Presentasi

Tenri perlu memahami konteks presentasi, termasuk:

- Topik yang sedang dibahas.
- Slide yang sedang aktif.
- Riwayat pembicaraan sebelumnya.
- Pertanyaan atau pernyataan presenter.
- Konteks visual sederhana seperti keberadaan wajah atau gerakan.
- Sumber pengetahuan yang relevan dengan bagian presentasi tersebut.

Pada tahap awal, konteks ini dapat diberikan melalui file outline slide. Pada tahap lanjut, sistem dapat diintegrasikan dengan PowerPoint, Google Slides, browser, atau web-app presentasi.

### 4. Knowledge Base dan Retrieval

Tenri harus terikat pada sumber pengetahuan yang diberikan. Karena itu, proyek membutuhkan knowledge base yang berisi:

- Buku yang dibaca oleh presenter.
- Arsip pribadi atau institusional.
- Dokumen penelitian.
- Catatan proyek.
- Materi presentasi.
- Transkrip, artikel, atau metadata yang relevan.

Sistem retrieval akan mencari potongan sumber yang sesuai dengan topik pembicaraan, lalu menyisipkannya ke prompt Tenri. Dengan cara ini, Tenri dapat menjawab berdasarkan arsip dan dokumen, bukan hanya berdasarkan pengetahuan umum model AI.

### 5. Interupsi Natural

Salah satu fitur penting Tenri adalah kemampuan untuk menyela atau "nimbrung" secara natural. Interupsi tidak boleh acak. Tenri perlu memiliki kebijakan kapan ia boleh bicara dan kapan ia harus diam.

Contoh kondisi Tenri boleh menyela:

- Presenter menyebut kata atau frasa tertentu.
- Presenter berhenti cukup lama.
- Slide aktif membahas topik yang sangat dekat dengan persona Tenri.
- Ada klaim yang perlu dikoreksi berdasarkan sumber.
- Ada momen emosional atau konseptual yang cocok untuk perspektif Tenri.

Contoh kondisi Tenri harus diam:

- Presenter sedang menjelaskan bagian penting tanpa jeda.
- Tenri baru saja berbicara.
- Tidak ada sumber yang cukup kuat.
- Interupsi akan mengganggu ritme presentasi.
- Topik tidak relevan dengan peran Tenri.

### 6. Sensitivitas Audio dan Konteks Percakapan

Pada tahap lanjutan, Tenri dapat dibuat lebih sensitif terhadap:

- Jeda bicara.
- Kecepatan bicara.
- Intonasi.
- Kata kunci tersembunyi.
- Pola kalimat tertentu.
- Momentum percakapan.

Kemampuan ini akan membuat Tenri terasa lebih hidup, karena ia tidak hanya menunggu nama dipanggil, tetapi dapat mengenali tanda-tanda halus dalam presentasi.

## Workflow Sistem

Workflow dasar Tenri dalam presentasi adalah sebagai berikut:

1. Presenter memulai aplikasi Tenri.
2. Sistem memuat konfigurasi, persona, system rules, dan knowledge base.
3. Sistem memulai layanan mikrofon, text-to-speech, model AI, dan konteks presentasi.
4. Presenter mulai berbicara.
5. Sistem menangkap suara presenter melalui microphone.
6. Speech-to-text mengubah suara menjadi teks.
7. Sistem membaca konteks aktif, termasuk slide, riwayat percakapan, dan visual context.
8. Retrieval system mencari dokumen atau arsip yang relevan.
9. Interruption policy menentukan apakah Tenri perlu menjawab, menyela, bertanya, atau diam.
10. Jika Tenri perlu berbicara, prompt builder menyusun pesan lengkap untuk model AI.
11. Model AI menghasilkan respons sesuai persona Tenri dan sumber yang tersedia.
12. Respons diproses oleh text-to-speech.
13. Audio Tenri diputar dalam ruang presentasi.
14. Percakapan disimpan ke session memory dan log.
15. Sistem kembali mendengar konteks berikutnya.

## Workflow MVP Saat Ini

Pada versi awal, proyek dapat berjalan dengan workflow yang lebih sederhana:

1. User menjalankan `python main.py`.
2. Aplikasi memuat konfigurasi dari `.env`.
3. Aplikasi memuat prompt karakter dan aturan sistem.
4. User memberi input melalui teks atau suara.
5. Sistem mengambil konteks visual sederhana dari kamera jika fitur vision aktif.
6. Sistem menyusun prompt dari persona, aturan, riwayat percakapan, input user, dan konteks visual.
7. Prompt dikirim ke Groq sebagai model LLM.
8. Respons ditampilkan di terminal.
9. Jika voice output aktif, respons dikirim ke ElevenLabs.
10. Audio respons diputar.
11. Percakapan disimpan sementara dalam session memory.

Workflow ini sudah cukup untuk prototipe awal, tetapi belum cukup untuk Tenri versi penuh yang memahami slide, arsip, dan interupsi natural.

## Perencanaan Pengembangan

### Tahap 1: Transformasi Persona dari AIRA ke Tenri

Fokus tahap ini adalah mengganti identitas AI companion dari AIRA menjadi Tenri.

Pekerjaan utama:

- Mengubah `character_prompt.txt`.
- Mengubah `system_rules.txt`.
- Mengubah label terminal dari AIRA menjadi Tenri.
- Menambahkan latar Museum La Galigo, pohon kelapa, arsip berjamur, dan dunia `tursalahjalan.com`.
- Menambahkan gaya bicara Tenri.
- Menambahkan referensi We Tenriabeng dan Pajonga.

Hasil tahap ini:

- AI sudah berbicara sebagai Tenri.
- Respons lebih personal, reflektif, dan terkait arsip.
- Sistem masih sederhana, tetapi rasa karakter mulai muncul.

### Tahap 2: Knowledge Base dan Retrieval

Fokus tahap ini adalah membuat Tenri dapat menjawab berdasarkan dokumen dan arsip.

Pekerjaan utama:

- Membuat folder knowledge base.
- Menambahkan parser untuk `.txt`, `.md`, `.pdf`, dan `.docx`.
- Memecah dokumen menjadi chunk.
- Membuat embedding.
- Menyimpan embedding dalam vector store lokal.
- Mengambil sumber relevan saat presenter berbicara.
- Menyisipkan kutipan atau ringkasan sumber ke prompt.

Hasil tahap ini:

- Tenri tidak hanya bergantung pada pengetahuan umum LLM.
- Tenri dapat menjawab berdasarkan buku, arsip, dan materi proyek.
- Risiko halusinasi berkurang.

### Tahap 3: Konteks Slide Presentasi

Fokus tahap ini adalah membuat Tenri tahu bagian presentasi yang sedang berlangsung.

Pekerjaan utama:

- Membuat format `slides.json` atau `presentation_context.json`.
- Menyimpan judul, catatan, topik, dan trigger per slide.
- Menambahkan modul presentation tracker.
- Menghubungkan slide aktif ke prompt builder.
- Menyediakan kontrol manual untuk next slide dan previous slide.

Hasil tahap ini:

- Tenri tahu slide apa yang sedang dibahas.
- Respons Tenri menjadi lebih relevan terhadap alur presentasi.
- Presenter dapat mengatur kapan konteks berpindah.

### Tahap 4: Trigger dan Interruption Policy

Fokus tahap ini adalah membuat Tenri dapat menyela dengan wajar.

Pekerjaan utama:

- Membuat modul `interruption_policy.py`.
- Menentukan aturan kapan Tenri boleh bicara.
- Menambahkan trigger berbasis kata kunci.
- Menambahkan trigger berbasis jeda.
- Menambahkan cooldown agar Tenri tidak terlalu sering bicara.
- Menambahkan mode respons: komentar, pertanyaan, koreksi, ingatan, atau sanggahan lembut.

Hasil tahap ini:

- Tenri dapat "nimbrung" tanpa terasa seperti chatbot yang dipanggil.
- Interupsi terasa lebih performatif dan hidup.
- Presenter tetap punya kendali atas alur utama.

### Tahap 5: Continuous Listening

Fokus tahap ini adalah mengurangi ketergantungan pada push-to-talk.

Pekerjaan utama:

- Membuat listener microphone berjalan di background.
- Menggunakan voice activity detection.
- Mengelompokkan ucapan presenter menjadi segmen.
- Mendeteksi jeda dan momentum bicara.
- Mengirim segmen percakapan ke sistem konteks.

Hasil tahap ini:

- Tenri dapat mengikuti presentasi secara lebih natural.
- Presenter tidak perlu selalu menekan tombol.
- Sistem mulai terasa seperti companion yang mendengar.

### Tahap 6: Kontrol Panggung dan Mode Aman

Fokus tahap ini adalah membuat Tenri aman dipakai dalam presentasi sungguhan.

Pekerjaan utama:

- Menambahkan tombol mute.
- Menambahkan tombol force speak.
- Menambahkan tombol skip response.
- Menambahkan batas durasi bicara.
- Menambahkan log semua interaksi.
- Menambahkan fallback jika API, microphone, atau TTS gagal.

Hasil tahap ini:

- Tenri lebih aman untuk konferensi atau pertunjukan live.
- Presenter tetap memiliki kendali penuh.
- Risiko gangguan teknis dapat dikurangi.

### Tahap 7: Integrasi dengan Web-App tursalahjalan.com

Fokus tahap ini adalah menghubungkan Tenri dengan dunia visual dan naratif di web-app.

Pekerjaan utama:

- Menghubungkan state Tenri dengan web-app.
- Menampilkan Tenri sebagai karakter visual atau avatar.
- Menghubungkan Tenri dengan Pajonga dan elemen dunia lain.
- Mengirim event dari presentasi ke web-app.
- Membuat Tenri dapat merespons perubahan scene atau halaman.

Hasil tahap ini:

- Tenri tidak hanya hadir sebagai suara, tetapi juga sebagai penghuni dunia digital.
- Presentasi, web-app, arsip, dan karakter saling terhubung.

## Timeline Pengerjaan 15 Hari

Timeline ini dirancang untuk menghasilkan prototipe Tenri yang dapat digunakan dalam presentasi awal. Fokus utamanya adalah mengubah fondasi AI companion yang sudah ada menjadi Tenri dengan persona kuat, alur suara yang stabil, konteks presentasi dasar, knowledge base awal, dan aturan interupsi sederhana.

### Hari 1: Audit Proyek dan Finalisasi Konsep

Fokus:

- Membaca ulang struktur kode yang sudah ada.
- Menentukan batas MVP Tenri.
- Menetapkan fitur yang wajib ada untuk demo pertama.
- Memastikan kebutuhan API, microphone, speaker, dan environment.

Output:

- Daftar fitur MVP.
- Catatan risiko teknis.
- Keputusan mode interaksi awal: push-to-talk atau semi-continuous listening.

#### Hasil Eksekusi Hari 1

Status proyek saat ini:

- Fondasi aplikasi Python sudah tersedia.
- Aplikasi sudah memiliki `interaction_loop.py` sebagai alur utama.
- Sistem sudah memiliki layanan LLM melalui Groq.
- Sistem sudah memiliki text-to-speech melalui ElevenLabs.
- Sistem sudah memiliki speech-to-text melalui `SpeechRecognition`.
- Sistem sudah memiliki audio playback melalui `pygame`.
- Sistem sudah memiliki vision context sederhana melalui OpenCV.
- Sistem sudah memiliki prompt persona dan system rules.
- Sistem sudah memiliki session memory.
- Sistem sudah memiliki test dasar untuk Groq service, prompt builder, session memory, dan speech service.

Hasil baseline test:

- Perintah: `python -m pytest tests`
- Hasil: 10 test lulus.
- Catatan: terdapat warning akses `.pytest_cache` dan warning kompatibilitas `speech_recognition` pada Python 3.13, tetapi tidak menggagalkan test.

Keputusan MVP Tenri:

- Tenri menggantikan AIRA sebagai karakter utama.
- Tenri harus bisa merespons melalui suara.
- Tenri harus memiliki persona kuat: Museum La Galigo, pohon kelapa, arsip berjamur, We Tenriabeng, Pajonga, dan dialek Makassar yang halus.
- Tenri harus bisa menerima input suara, dengan fallback ke input teks jika microphone bermasalah.
- Tenri harus bisa membaca konteks presentasi dari file slide sederhana.
- Tenri harus mulai terikat pada knowledge base awal.
- Tenri harus memiliki trigger interupsi sederhana, tetapi belum perlu continuous listening penuh.

Fitur wajib untuk demo pertama:

- Persona Tenri.
- Voice input.
- Voice output.
- Slide context manual.
- Knowledge base awal.
- Trigger interupsi terkontrol.
- Session memory.
- Fallback text mode.

Fitur yang belum wajib untuk demo pertama:

- Continuous listening penuh.
- Deteksi intonasi yang akurat.
- Integrasi langsung dengan PowerPoint atau Google Slides.
- Avatar visual Tenri.
- Fine-tuning model.
- Retrieval dokumen skala besar.

Catatan risiko teknis:

- Speech-to-text bisa salah menangkap suara jika ruangan ramai.
- Voice output bergantung pada koneksi internet dan ElevenLabs API key.
- Respons LLM bergantung pada koneksi internet dan Groq API key.
- Continuous listening berisiko mengganggu presentasi jika belum stabil.
- Retrieval harus dibatasi agar Tenri tidak mengarang di luar sumber.
- Dialek Makassar harus digunakan secara halus agar tidak menjadi karikatural.
- Interupsi harus memiliki cooldown agar Tenri tidak terlalu sering bicara.
- Python 3.13 perlu diperhatikan karena beberapa library audio/speech kadang lebih stabil di Python 3.10 atau 3.11.

Keputusan mode interaksi awal:

- Mode awal: push-to-talk.
- Mode lanjutan: semi-continuous listening.
- Alasan: push-to-talk lebih aman untuk demo awal karena presenter tetap memegang kendali, risiko salah dengar lebih kecil, dan Tenri tidak menyela tanpa kontrol.

### Hari 2: Transformasi Persona AIRA Menjadi Tenri

Fokus:

- Mengubah `character_prompt.txt`.
- Mengubah `system_rules.txt`.
- Mengganti label AIRA menjadi Tenri di terminal UI.
- Menambahkan latar Museum La Galigo, pohon kelapa, arsip berjamur, We Tenriabeng, Pajonga, dan gaya bicara Makassar yang halus.

Output:

- Tenri sudah muncul sebagai karakter dalam respons.
- Respons lebih personal, reflektif, dan sesuai narasi proyek.

#### Hasil Eksekusi Hari 2

Status:

- Persona AIRA sudah diganti menjadi Tenri pada prompt utama.
- System rules sudah diperbarui agar Tenri berbicara sebagai karakter, bukan asisten virtual generik.
- Label runtime di terminal sudah diganti dari AIRA/Aira menjadi Tenri.
- Fallback prompt sudah diganti agar tetap mengarah ke Tenri jika file prompt tidak terbaca.
- Warning konfigurasi offline Groq sudah menyebut Tenri.
- Test yang masih mengacu ke AIRA sudah diperbarui.

File yang diubah:

- `app/prompts/character_prompt.txt`
- `app/prompts/system_rules.txt`
- `app/core/prompt_builder.py`
- `app/core/interaction_loop.py`
- `app/config.py`
- `app/utils/terminal_ui.py`
- `tests/test_prompt_builder.py`
- `tests/test_groq_service.py`

Isi persona Tenri yang sudah masuk:

- Tenri sebagai tokoh perempuan di dunia `tursalahjalan.com`.
- Tenri menunggu di bawah pohon kelapa di belakang Museum La Galigo.
- Tenri memiliki hubungan emosional dengan arsip, naskah berjamur, ingatan, dan pengetahuan yang hampir hilang.
- Tenri terinspirasi dari gema We Tenriabeng, tetapi bukan reproduksi literal tokoh mitologi tersebut.
- Tenri mengenal Pajonga dan boleh menyebutnya jika relevan.
- Tenri lembut tetapi tegas, personal, reflektif, dan boleh berbeda pendapat dengan presenter.
- Tenri dapat memakai nuansa Makassar secara halus tanpa menjadi karikatural.
- Tenri harus terikat pada sumber dan mengakui keterbatasan jika konteks tidak cukup.

Hasil verifikasi:

- Perintah: `python -m pytest tests`
- Hasil: 10 test lulus.
- Catatan: warning lama terkait `.pytest_cache` dan `speech_recognition` di Python 3.13 masih muncul, tetapi tidak menggagalkan test.

### Hari 3: Penguatan Prompt dan Contoh Dialog

Fokus:

- Membuat contoh dialog Tenri.
- Menambahkan aturan kapan Tenri boleh menyanggah atau bertanya.
- Menambahkan batasan anti-halusinasi awal.
- Menguji respons dalam beberapa skenario presentasi.

Output:

- File contoh dialog Tenri.
- Prompt karakter lebih stabil.
- Respons Tenri lebih konsisten.

#### Hasil Eksekusi Hari 3

Status:

- File contoh dialog Tenri sudah dibuat.
- Prompt builder sudah diperbarui agar contoh dialog ikut masuk ke system prompt.
- System rules sudah diperkuat dengan aturan sanggahan, pertanyaan, diam, dan anti-halusinasi.
- Test prompt builder sudah diperbarui untuk memastikan contoh dialog dan aturan anti-halusinasi termuat.

File yang dibuat:

- `app/prompts/examples_tenri_dialogue.txt`

File yang diubah:

- `app/prompts/system_rules.txt`
- `app/core/prompt_builder.py`
- `tests/test_prompt_builder.py`
- `Ai-companion.md`

Skenario contoh dialog yang sudah ditambahkan:

- Pembukaan presentasi tentang Tenri.
- Arsip disebut hanya sebagai data.
- Hubungan Tenri dengan Museum La Galigo.
- Kritik halus terhadap anggapan bahwa AI otomatis menyelamatkan pengetahuan.
- Pertanyaan tentang isi arsip yang belum tersedia.
- Hubungan Tenri dengan We Tenriabeng.
- Penyebutan Pajonga.
- Respons Tenri dalam English.
- Contoh Tenri bertanya balik.
- Contoh Tenri memilih diam agar tidak mengganggu presentasi.

Aturan baru yang ditambahkan:

- Kapan Tenri boleh menyanggah.
- Cara Tenri menyanggah tanpa merusak alur presentasi.
- Kapan Tenri boleh bertanya.
- Kapan Tenri harus diam.
- Larangan membuat kutipan palsu.
- Larangan mengarang isi naskah La Galigo.
- Larangan mengklaim telah membaca dokumen yang belum diberikan.
- Pemisahan fakta dan interpretasi.

Hasil verifikasi:

- Perintah: `python -m pytest tests`
- Hasil: 10 test lulus.
- Catatan: warning lama terkait `.pytest_cache` dan `speech_recognition` di Python 3.13 masih muncul, tetapi tidak menggagalkan test.

### Hari 4: Perbaikan Voice Input dan Voice Output

Fokus:

- Menguji microphone.
- Menguji speech-to-text.
- Menguji ElevenLabs text-to-speech.
- Mengatur durasi rekaman, timeout, pause threshold, dan energy threshold.

Output:

- Voice loop lebih stabil.
- Tenri dapat mendengar dan menjawab dengan suara.
- Fallback text mode tetap tersedia.

#### Hasil Eksekusi Hari 4

Status:

- Microphone berhasil terdeteksi.
- `MIC_DEVICE_INDEX=2` mengarah ke `Microphone (Realtek Audio)`.
- Speech service diperbaiki agar index microphone yang salah tidak langsung mematikan voice input; sistem akan fallback ke default microphone.
- Parameter voice input dibuat lebih eksplisit dan dapat dikonfigurasi dari `.env`.
- ElevenLabs client berhasil dibuat.
- Text-to-speech berhasil membuat file audio pendek Tenri.
- Audio playback berhasil dicoba melalui `pygame`.
- Fallback text mode tetap tersedia jika microphone tidak aktif atau voice input dimatikan.

File yang diubah:

- `app/config.py`
- `app/services/speech_service.py`
- `.env.example`
- `.env`
- `tests/test_speech_service.py`
- `Ai-companion.md`

Pengaturan voice aktual:

- `VOICE_INPUT_ENABLED=true`
- `VOICE_OUTPUT_ENABLED=true`
- `MIC_DEVICE_INDEX=2`
- `SPEECH_ENERGY_THRESHOLD=150`
- `SPEECH_DYNAMIC_ENERGY=true`
- `SPEECH_PAUSE_THRESHOLD=0.9`
- `SPEECH_TIMEOUT=7.0`
- `SPEECH_PHRASE_TIME_LIMIT=12.0`
- `SPEECH_AMBIENT_NOISE_DURATION=0.5`

Hasil diagnostik:

- Jumlah device audio terdeteksi: 32.
- Microphone terpilih: `Microphone (Realtek Audio)`.
- ElevenLabs client: siap.
- TTS audio: berhasil dibuat.
- Playback audio: berhasil dicoba.
- Speech-to-text listen test: jalur microphone berjalan, tetapi hasil uji singkat mengembalikan `[UNKNOWN_AUDIO]` karena audio pada saat pengujian tidak dikenali sebagai ucapan yang jelas.

Perbaikan stabilitas:

- `SPEECH_TIMEOUT` ditambahkan untuk mengatur berapa lama sistem menunggu awal suara.
- `SPEECH_PHRASE_TIME_LIMIT` digunakan untuk membatasi durasi satu rekaman.
- `SPEECH_AMBIENT_NOISE_DURATION` ditambahkan untuk mengatur durasi kalibrasi noise ruangan.
- `SPEECH_PAUSE_THRESHOLD` dinaikkan menjadi `0.9` agar kalimat presentasi tidak terlalu cepat terpotong.
- Kode tetap kompatibel dengan nama lama `SPEECH_TIMEOUT_SECONDS`.
- Test baru memastikan `MIC_DEVICE_INDEX` tidak valid akan fallback ke default microphone.

Hasil verifikasi:

- Perintah: `python -m pytest tests`
- Hasil: 11 test lulus.
- Catatan: warning lama terkait `.pytest_cache` dan `speech_recognition` di Python 3.13 masih muncul, tetapi tidak menggagalkan test.

### Hari 5: Pembuatan Struktur Knowledge Base

Fokus:

- Membuat folder `app/knowledge/`.
- Membuat subfolder untuk buku, arsip, paper, catatan proyek, dan materi presentasi.
- Menentukan format dokumen awal yang akan dipakai.
- Menyiapkan beberapa sumber awal untuk demo.
- Menambahkan sistem metadata `sources.json` agar Tenri hanya memakai sumber yang tercatat dan berstatus aktif.
- Merancang otomasi pengelolaan materi melalui script `scripts/manage_knowledge.py`.
- Menentukan aturan versioning agar materi lama tidak harus dihapus ketika ada versi baru.

Output:

- Struktur knowledge base siap.
- Materi awal Tenri mulai dikumpulkan.
- Metadata sumber awal tersedia.
- Alur tambah, ganti, aktifkan, nonaktifkan, dan arsipkan materi sudah dirancang.

Rencana struktur knowledge base:

```text
app/knowledge/
|-- README.md
|-- sources.json
|-- books/
|-- archives/
|-- papers/
|-- project_notes/
|-- presentation/
|-- inbox/
|-- indexes/
```

Fungsi folder:

- `books/`: catatan, ekstrak, atau ringkasan buku.
- `archives/`: arsip, transkrip, metadata naskah, atau catatan museum.
- `papers/`: paper akademik, artikel jurnal, dan dokumen penelitian.
- `project_notes/`: catatan konsep Tenri, dunia `tursalahjalan.com`, Pajonga, dan narasi proyek.
- `presentation/`: outline, script, slide notes, atau materi presentasi.
- `inbox/`: tempat sementara untuk file baru sebelum dimasukkan ke knowledge base.
- `indexes/`: tempat hasil indexing atau cache retrieval pada tahap berikutnya.

Format dokumen awal:

- `.md`
- `.txt`
- `.json`

Format seperti `.pdf`, `.docx`, dan `.pptx` boleh disimpan sejak awal, tetapi pembacaan otomatisnya dikerjakan bertahap setelah document loader siap.

Konsep metadata sumber:

```json
{
  "id": "tenri-concept",
  "title": "Konsep Tenri AI Companion",
  "type": "project_note",
  "active_version": "v1",
  "status": "active",
  "versions": [
    {
      "version": "v1",
      "path": "project_notes/tenri_concept.md",
      "status": "active",
      "created_at": "2026-06-02"
    }
  ],
  "notes": "Konsep awal persona Tenri dan relasinya dengan arsip."
}
```

Aturan status sumber:

- `active`: sumber dipakai oleh Tenri.
- `archived`: sumber lama tetap disimpan, tetapi tidak dipakai.
- `disabled`: sumber sengaja dimatikan sementara.
- `draft`: sumber masih catatan mentah dan belum boleh dipakai.
- `replaced`: sumber sudah digantikan oleh versi baru.

Prinsip penggantian materi:

- Materi lama tidak harus dihapus.
- File lama sebaiknya diarsipkan agar jejak perubahan tetap tersimpan.
- Tenri hanya memakai sumber yang statusnya `active`.
- Jika materi diganti, versi lama menjadi `archived` dan versi baru menjadi `active`.
- Setelah materi ditambah atau diganti, index retrieval perlu dibuat ulang pada tahap berikutnya.

Rencana otomasi:

```text
scripts/
|-- manage_knowledge.py
```

Command yang direncanakan:

```text
python scripts/manage_knowledge.py add --type paper --title "Judul Paper" --file "path/to/file.pdf"
python scripts/manage_knowledge.py replace --id paper-la-galigo --file "path/to/file_baru.pdf"
python scripts/manage_knowledge.py disable --id paper-la-galigo
python scripts/manage_knowledge.py enable --id paper-la-galigo
python scripts/manage_knowledge.py list
python scripts/manage_knowledge.py ingest
```

Perilaku otomasi:

- `add`: menyalin file ke folder yang sesuai, membuat ID sumber, membuat versi `v1`, dan menambahkan metadata ke `sources.json`.
- `replace`: menyimpan versi lama sebagai `archived`, menambahkan versi baru, dan mengubah `active_version`.
- `disable`: membuat sumber tidak dipakai Tenri tanpa menghapus file.
- `enable`: mengaktifkan kembali sumber tertentu.
- `list`: menampilkan daftar sumber berdasarkan status.
- `ingest`: mengambil file dari `app/knowledge/inbox/` dan memasukkannya ke metadata.

Materi awal untuk demo:

- `app/knowledge/project_notes/tenri_concept.md`
- `app/knowledge/project_notes/tursalahjalan_world.md`
- `app/knowledge/archives/archive_memory_notes.md`
- `app/knowledge/presentations/demo_outline.md`

#### Hasil Eksekusi Hari 5

Status:

- Struktur `app/knowledge/` sudah dibuat.
- Subfolder `books/`, `archives/`, `papers/`, `project_notes/`, `presentations/`, `inbox/`, dan `indexes/` sudah tersedia.
- `sources.json` sudah dibuat sebagai metadata pusat.
- Empat sumber awal demo sudah dibuat dan berstatus `active`.
- Script otomasi `scripts/manage_knowledge.py` sudah dibuat.
- Command `list`, `add`, `replace`, `disable`, `enable`, dan `ingest` sudah tersedia.
- Test untuk otomasi knowledge base sudah dibuat.

File dan folder yang dibuat:

- `app/knowledge/README.md`
- `app/knowledge/sources.json`
- `app/knowledge/books/.gitkeep`
- `app/knowledge/papers/.gitkeep`
- `app/knowledge/inbox/.gitkeep`
- `app/knowledge/indexes/.gitkeep`
- `app/knowledge/project_notes/tenri_concept.md`
- `app/knowledge/project_notes/tursalahjalan_world.md`
- `app/knowledge/archives/archive_memory_notes.md`
- `app/knowledge/presentations/demo_outline.md`
- `scripts/__init__.py`
- `scripts/manage_knowledge.py`
- `tests/test_manage_knowledge.py`

Sumber awal aktif:

- `tenri-concept`: Konsep Tenri AI Companion.
- `tursalahjalan-world`: Dunia `tursalahjalan.com`.
- `archive-memory-notes`: Catatan Arsip dan Ingatan.
- `demo-outline`: Outline Demo Presentasi Tenri.

Command yang sudah bisa dipakai:

```text
python scripts/manage_knowledge.py list
python scripts/manage_knowledge.py add --type paper --title "Judul Paper" --file "path/to/file.pdf"
python scripts/manage_knowledge.py replace --id judul-paper --file "path/to/file_baru.pdf"
python scripts/manage_knowledge.py disable --id judul-paper
python scripts/manage_knowledge.py enable --id judul-paper
python scripts/manage_knowledge.py ingest --type project_note
```

Hasil diagnostik:

- `python scripts/manage_knowledge.py list` berhasil menampilkan 4 sumber aktif.
- `sources.json` valid dan berisi 4 sumber.
- Semua sumber awal memiliki `active_version` v1.

Hasil verifikasi:

- Perintah: `python -m pytest tests`
- Hasil: 13 test lulus.
- Catatan: warning lama terkait `.pytest_cache` dan `speech_recognition` di Python 3.13 masih muncul, tetapi tidak menggagalkan test.

### Hari 6: Document Loader Awal

Fokus:

- Membuat modul `document_loader.py`.
- Mendukung pembacaan `.txt` dan `.md` terlebih dahulu.
- Menyiapkan format metadata sumber.
- Membuat proses chunking sederhana.

Output:

- Dokumen teks dapat dibaca sistem.
- Materi dapat dipecah menjadi potongan kecil untuk retrieval.

### Hari 7: Retrieval Sederhana

Fokus:

- Membuat retrieval awal berbasis keyword atau similarity sederhana.
- Menghubungkan retrieval ke `prompt_builder.py`.
- Menampilkan sumber yang dipakai dalam log.
- Menguji pertanyaan berdasarkan dokumen.

Output:

- Tenri mulai bisa menjawab berdasarkan sumber lokal.
- Respons lebih terikat pada materi yang diberikan.

### Hari 8: Konteks Slide Presentasi

Fokus:

- Membuat folder `app/presentation/`.
- Membuat file `slides.json`.
- Menambahkan judul slide, catatan presenter, trigger, dan topik utama.
- Membuat modul `presentation_tracker.py`.

Output:

- Sistem dapat mengetahui slide aktif.
- Tenri dapat menyesuaikan respons dengan bagian presentasi.

### Hari 9: Kontrol Slide Manual

Fokus:

- Menambahkan perintah untuk next slide dan previous slide.
- Menampilkan slide aktif di terminal.
- Menghubungkan slide aktif ke prompt builder.
- Menguji alur presentasi dari slide awal sampai akhir.

Output:

- Presenter dapat mengatur konteks slide secara manual.
- Tenri lebih relevan terhadap alur presentasi.

### Hari 10: Interruption Policy Versi Awal

Fokus:

- Membuat modul `interruption_policy.py`.
- Menentukan kondisi Tenri bicara atau diam.
- Menambahkan cooldown agar Tenri tidak terlalu sering menyela.
- Menambahkan mode respons seperti komentar, pertanyaan, koreksi, dan ingatan.

Output:

- Tenri memiliki aturan dasar untuk "nimbrung".
- Interupsi lebih terkontrol.

### Hari 11: Trigger Terselubung

Fokus:

- Membuat file `triggers.json`.
- Menambahkan kata kunci atau pola kalimat pemicu.
- Menghubungkan trigger dengan slide dan topik.
- Menguji pemicu tanpa harus memanggil nama Tenri secara eksplisit.

Output:

- Tenri bisa muncul melalui stimulus tertentu.
- Interaksi terasa lebih natural dalam presentasi.

### Hari 12: Session Logging dan Grounding Check

Fokus:

- Menambahkan log percakapan.
- Menambahkan log sumber retrieval.
- Menambahkan aturan jika sumber tidak ditemukan.
- Membuat Tenri berani mengatakan tidak tahu jika konteks tidak cukup.

Output:

- Percakapan dan sumber dapat dilacak.
- Risiko halusinasi berkurang.

### Hari 13: Rehearsal Presentasi Pertama

Fokus:

- Melakukan simulasi presentasi penuh.
- Menguji timing interupsi.
- Menguji respons Tenri di setiap slide.
- Mencatat bagian yang terlalu panjang, terlalu sering, atau tidak relevan.

Output:

- Catatan rehearsal.
- Daftar perbaikan prioritas.

#### Materi Uji Coba Awal

Status:

- Materi rehearsal awal sudah disiapkan sebelum Hari 13 agar alur presentasi dapat diuji lebih cepat.
- `slides.json` sudah diperbarui menjadi 8 slide naratif yang mengikuti konsep Tenri.
- `triggers.json` sudah diperbarui menjadi 9 trigger yang menguji memory, witness, gentle objection, clarification, grounding check, dan closing memory.
- Naskah presenter rehearsal sudah dibuat.
- Run sheet rehearsal sudah dibuat.
- Template catatan rehearsal dan prioritas perbaikan sudah dibuat.

File materi:

- `app/presentation/slides.json`
- `app/presentation/triggers.json`
- `app/presentation/rehearsal_script.md`
- `app/presentation/rehearsal_run_sheet.md`
- `app/data/rehearsals/rehearsal_01.md`
- `app/data/rehearsals/priority_fixes.md`

Struktur materi:

- Slide 1: Pembukaan, Tenri bukan asisten.
- Slide 2: Dunia `tursalahjalan.com`.
- Slide 3: Arsip bukan sekadar data.
- Slide 4: Gema We Tenriabeng.
- Slide 5: Teknologi dan batasnya.
- Slide 6: Cara Tenri mendengar.
- Slide 7: Dialog uji coba.
- Slide 8: Penutup, siapa yang akan mengingat.

Hasil verifikasi:

- `app/presentation/slides.json`: valid JSON, 8 item.
- `app/presentation/triggers.json`: valid JSON, 9 item.
- Perintah: `python -m pytest tests`
- Hasil: 152 test lulus.
- Catatan: dependency document/retrieval yang dibutuhkan test sudah dipasang dari `requirements.txt`.

#### Hasil Eksekusi Hari 13

Status:

- Rehearsal penuh slide 1 sampai 8 sudah dijalankan melalui runner simulasi presentasi.
- Cue presenter diproses sebagai transkrip push-to-talk.
- Respons Tenri dibuat menggunakan konteks slide, trigger, retrieval knowledge base, dan Groq.
- Fallback respons tidak dipakai karena Groq client siap.
- ElevenLabs client siap dan berhasil membuat audio rehearsal untuk 8 cue non-diam.
- Slide 6 diuji sebagai momen diam agar Tenri tidak mengganggu bagian teknis.
- Trigger terlalu generik sudah diperbaiki: pola `"tenri"` dihapus dari trigger pembukaan agar tidak menangkap semua cue.
- Trigger baru `t010` ditambahkan untuk pertanyaan balik Tenri.

File yang dibuat atau diperbarui:

- `scripts/run_rehearsal.py`
- `app/presentation/triggers.json`
- `app/data/rehearsals/rehearsal_01.md`
- `app/data/rehearsals/priority_fixes.md`
- `app/data/rehearsals/audio/slide_01_cue_01.mp3`
- `app/data/rehearsals/audio/slide_02_cue_02.mp3`
- `app/data/rehearsals/audio/slide_03_cue_03.mp3`
- `app/data/rehearsals/audio/slide_04_cue_04.mp3`
- `app/data/rehearsals/audio/slide_05_cue_05.mp3`
- `app/data/rehearsals/audio/slide_07_cue_07.mp3`
- `app/data/rehearsals/audio/slide_07_cue_08.mp3`
- `app/data/rehearsals/audio/slide_08_cue_09.mp3`

Hasil rehearsal:

- Groq client siap: ya.
- ElevenLabs client siap: ya.
- Fallback respons dipakai: tidak.
- File audio rehearsal dibuat: 8.
- Jumlah chunk knowledge aktif: 9.
- Rata-rata timing: 5.0/5.
- Rata-rata relevansi: 4.9/5.
- Rata-rata panjang respons: 5.0/5.
- Risiko halusinasi: rendah; cue batas pengetahuan dijawab dengan pengakuan keterbatasan.

Daftar perbaikan prioritas sudah dibuat:

- Prioritas tinggi: rehearsal fisik berikutnya perlu mengukur latensi microphone dan kualitas suara nyata di ruang presentasi.
- Prioritas sedang: tambahkan pengukuran durasi respons audio per slide dan catatan operator untuk respons yang terlalu puitis.
- Prioritas rendah: rapikan template skor dan tambahkan nomor cue pada naskah presenter.

Hasil verifikasi final:

- Perintah: `python scripts/run_rehearsal.py`
- Hasil: laporan rehearsal dan daftar prioritas berhasil ditulis.
- Perintah: `python -m pytest tests`
- Hasil: 152 test lulus.

### Hari 14: Polish dan Stabilitas

Fokus:

- Memperbaiki prompt berdasarkan rehearsal.
- Mengurangi respons yang terlalu panjang.
- Menyetel ulang threshold audio.
- Memperbaiki bug kecil.
- Memastikan fallback berjalan.

Output:

- Prototipe lebih stabil untuk demo.
- Tenri lebih singkat, tepat, dan tidak mengganggu presenter.

### Hari 15: Final Demo Package

Fokus:

- Menjalankan demo dari awal sampai akhir.
- Menyiapkan dokumentasi penggunaan singkat.
- Menyiapkan file konfigurasi contoh.
- Menyusun daftar fitur yang sudah selesai dan fitur lanjutan.

Output:

- Prototipe Tenri siap didemokan.
- Dokumentasi penggunaan tersedia.
- Roadmap lanjutan lebih jelas.

## Target Akhir Setelah 15 Hari

Setelah 15 hari, target realistis proyek adalah memiliki prototipe Tenri dengan kemampuan berikut:

- Tenri sudah memiliki persona yang kuat.
- Tenri dapat berinteraksi melalui suara.
- Tenri dapat menjawab berdasarkan knowledge base awal.
- Tenri memahami konteks slide secara manual melalui `slides.json`.
- Tenri memiliki trigger awal untuk muncul secara natural.
- Tenri memiliki aturan interupsi dasar.
- Presenter tetap memiliki kontrol atas alur presentasi.
- Sistem siap dipakai untuk demo internal atau rehearsal konferensi.

Fitur yang kemungkinan masih menjadi tahap lanjutan setelah 15 hari:

- Continuous listening penuh.
- Deteksi intonasi yang akurat.
- Integrasi langsung dengan PowerPoint, Google Slides, atau browser.
- Avatar visual Tenri di web-app.
- Retrieval dokumen skala besar.
- Fine-tuning karakter.


## Struktur Folder

Untuk mencapai versi Tenri yang lebih lengkap, struktur folder dapat dikembangkan menjadi:

```text
ai-companion-terminal/
|-- main.py
|-- README.md
|-- Ai-companion.md
|-- requirements.txt
|-- .env
|-- .env.example
|-- app/
|   |-- __init__.py
|   |-- config.py
|   |-- state.py
|   |-- core/
|   |   |-- __init__.py
|   |   |-- interaction_loop.py
|   |   |-- prompt_builder.py
|   |   |-- session_memory.py
|   |   |-- interruption_policy.py
|   |   |-- presentation_tracker.py
|   |   |-- response_mode.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- groq_service.py
|   |   |-- elevenlabs_service.py
|   |   |-- speech_service.py
|   |   |-- vision_service.py
|   |   |-- audio_player.py
|   |   |-- document_loader.py
|   |   |-- retrieval_service.py
|   |   |-- embedding_service.py
|   |-- prompts/
|   |   |-- character_prompt.txt
|   |   |-- system_rules.txt
|   |   |-- examples_tenri_dialogue.txt
|   |   |-- refusal_and_grounding_rules.txt
|   |-- knowledge/
|   |   |-- books/
|   |   |-- papers/
|   |   |-- archives/
|   |   |-- project_notes/
|   |   |-- presentations/
|   |   |-- indexes/
|   |-- presentation/
|   |   |-- slides.json
|   |   |-- presenter_notes.md
|   |   |-- triggers.json
|   |-- data/
|   |   |-- retrieval_log.json
|   |   |-- logs/
|   |-- utils/
|   |   |-- __init__.py
|   |   |-- terminal_ui.py
|   |   |-- logger.py
|   |   |-- file_manager.py
|-- assets/
|   |-- audio/
|   |   |-- temp/
|   |   |-- responses/
|   |-- images/
|   |   |-- camera_snapshots/
|-- tests/
|   |-- test_prompt_builder.py
|   |-- test_session_memory.py
|   |-- test_interruption_policy.py
|   |-- test_presentation_tracker.py
|   |-- test_retrieval_service.py
|   |-- test_speech_service.py
```

## Modul Target

### `interaction_loop.py`

Mengatur siklus utama aplikasi: mendengar, memahami konteks, memutuskan respons, memanggil LLM, memutar suara, dan kembali ke mode siaga.

### `prompt_builder.py`

Menyusun prompt lengkap untuk Tenri berdasarkan persona, aturan sistem, riwayat percakapan, konteks slide, hasil retrieval, dan konteks visual.

### `session_memory.py`

Menyimpan percakapan sementara agar Tenri dapat mengingat konteks dialog selama sesi presentasi.

### `interruption_policy.py`

Menentukan apakah Tenri perlu bicara atau diam. Modul ini menjaga agar Tenri tidak menyela terlalu sering dan tetap menghormati alur presenter.

### `presentation_tracker.py`

Melacak slide aktif, topik aktif, catatan presenter, dan trigger khusus yang terkait dengan bagian presentasi tertentu.

### `retrieval_service.py`

Mencari sumber pengetahuan yang relevan dari knowledge base, lalu mengembalikannya sebagai konteks yang dapat dipakai oleh Tenri.

### `document_loader.py`

Membaca dan memproses dokumen dari berbagai format seperti `.txt`, `.md`, `.pdf`, dan `.docx`.

### `embedding_service.py`

Mengubah potongan dokumen menjadi embedding agar dapat dicari secara semantik.

### `speech_service.py`

Menangkap suara presenter dan mengubahnya menjadi teks. Pada tahap lanjut, modul ini juga dapat mendukung continuous listening.

### `elevenlabs_service.py`

Mengubah respons Tenri menjadi suara.

### `vision_service.py`

Memberikan konteks visual sederhana seperti deteksi wajah, jumlah orang, dan gerakan di sekitar kamera.

## Prinsip Desain

Proyek Tenri perlu mengikuti beberapa prinsip utama:

- Karakter lebih penting daripada sekadar fungsi.
- Respons harus singkat, dapat diucapkan, dan tidak mendominasi presentasi.
- Tenri harus terikat pada sumber pengetahuan yang tersedia.
- Ketika tidak tahu, Tenri harus mengakui keterbatasan.
- Interupsi harus terasa bermakna, bukan acak.
- Presenter harus selalu memiliki kendali.
- Sistem harus tetap memiliki fallback jika suara, kamera, API, atau retrieval gagal.

## Kesimpulan

Tenri adalah proyek yang sangat mungkin dibangun dari fondasi `ai-companion-terminal` yang sudah ada. Versi saat ini sudah menyediakan dasar penting: input suara, output suara, LLM, memori sesi, prompt persona, dan konteks visual sederhana.

Namun, agar benar-benar menjadi Tenri seperti konsep yang diinginkan, proyek perlu dikembangkan lebih jauh melalui persona yang kuat, knowledge base berbasis arsip, pemahaman konteks slide, dan kebijakan interupsi yang membuat Tenri terasa hidup di dalam presentasi.

Dengan pengembangan bertahap, Tenri dapat menjadi AI companion yang tidak hanya membantu presentasi, tetapi juga menjadi bagian dari narasi: seorang saksi digital yang menjaga arsip, mengingat yang hampir hilang, dan berbicara dari tempat di mana pengetahuan masih ingin diselamatkan.
