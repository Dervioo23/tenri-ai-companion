# Tenri Knowledge Base

Folder ini menyimpan sumber pengetahuan eksternal untuk Tenri. Tenri tidak seharusnya membaca semua file secara bebas; sumber yang boleh dipakai harus tercatat di `sources.json` dan memiliki status `active`.

## Struktur

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

## Status Sumber

- `active`: sumber dipakai oleh Tenri.
- `archived`: sumber lama tetap disimpan, tetapi tidak dipakai.
- `disabled`: sumber dimatikan sementara.
- `draft`: sumber belum siap dipakai.
- `replaced`: sumber sudah digantikan oleh versi baru.

## Prinsip

- Jangan hapus materi lama jika masih berguna sebagai jejak kerja.
- Gunakan versi baru ketika materi berubah besar.
- Tenri hanya boleh memakai sumber yang tercatat dan aktif.
- Setelah menambah atau mengganti materi, index retrieval perlu dibuat ulang pada tahap berikutnya.

## Otomasi

Gunakan `scripts/manage_knowledge.py` untuk menambah, mengganti, mengaktifkan, menonaktifkan, dan melihat daftar sumber.

Contoh:

```text
python scripts/manage_knowledge.py list
python scripts/manage_knowledge.py add --type paper --title "Judul Paper" --file "path/to/file.pdf"
python scripts/manage_knowledge.py replace --id judul-paper --file "path/to/file_baru.pdf"
python scripts/manage_knowledge.py disable --id judul-paper
python scripts/manage_knowledge.py enable --id judul-paper
```
