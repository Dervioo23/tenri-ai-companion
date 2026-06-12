# Audio Regression Corpus

Masukkan rekaman WAV dari kasus rehearsal yang gagal dengan:

```powershell
python scripts/add_audio_regression.py rekaman.wav `
  --id wake-word-di-akhir `
  --expected "Apa itu kecerdasan buatan, Tenri?" `
  --intent asking_tenri `
  --notes "Wake word berada di akhir kalimat."
```

Format wajib: mono, PCM 16-bit, WAV. Jangan masukkan rekaman yang berisi data pribadi audiens. Setiap bug pendengaran baru seharusnya memiliki satu fixture sebelum aturan atau model diubah.
