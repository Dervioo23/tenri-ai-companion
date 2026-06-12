# Tenri Knowledge Base

Folder ini menyimpan sumber pengetahuan yang boleh dipakai Tenri. Sumber runtime harus tercatat di `sources.json`; hanya entri berstatus `active` yang dimuat.

## Struktur Kanonik

```text
app/knowledge/
|-- sources.json
|-- books/
|-- archives/
|-- papers/
|-- project_notes/
|-- presentations/    # satu-satunya folder materi presentasi permanen
|-- inbox/            # area sementara untuk file yang belum diimpor
`-- indexes/          # cache chunk retrieval
```

Jangan membuat folder `presentation/` tanpa huruf `s`. Semua PPTX dan outline presentasi permanen berada di `presentations/`.

## Status Sumber

- `active`: dimuat ke knowledge base.
- `disabled`: dimatikan sementara.
- `draft`: belum siap dipakai.
- `archived`: versi lama disimpan sebagai jejak.
- `replaced`: sudah digantikan versi baru.

## Alur Materi

Gunakan importer agar file disalin ke lokasi kanonik, metadata `sources.json` diperbarui, dan aset presentasi dapat dibuat secara konsisten:

```powershell
python scripts/import_document.py "C:\materi\presentasi.pptx"
python scripts/import_document.py "C:\materi\paper.pdf" --name "Judul Materi"
```

Kelola status sumber dengan:

```powershell
python scripts/manage_knowledge.py list
python scripts/manage_knowledge.py disable --id sumber-id
python scripts/manage_knowledge.py enable --id sumber-id
python scripts/manage_knowledge.py replace --id sumber-id --file "C:\materi\versi-baru.pdf"
```

Jangan menghapus versi lama hanya untuk mengganti materi. Gunakan `replace` bila riwayat versi masih dibutuhkan. Hapus entri hanya jika memang artefak basi dan file rujukannya sudah tidak ada.
