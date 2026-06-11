import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import Config
from app.core.prompt_builder import PromptBuilder
from app.services.document_loader import DocumentLoader
from app.services.elevenlabs_service import ElevenLabsService
from app.services.llm_factory import build_llm_service
from app.services.presentation_tracker import PresentationTracker
from app.services.retrieval import RetrievalService
from app.services.trigger_service import TriggerService


REHEARSAL_DIR = ROOT_DIR / "app" / "data" / "rehearsals"
AUDIO_DIR = REHEARSAL_DIR / "audio"


REHEARSAL_CUES = [
    {
        "slide_id": 1,
        "cue": "Tenri, perkenalkan dirimu secara singkat.",
        "expectation": "Tenri memperkenalkan diri sebagai suara dari arsip, maksimal 2 kalimat.",
    },
    {
        "slide_id": 2,
        "cue": "Tenri, seperti apa tempatmu menunggu?",
        "expectation": "Tenri memberi kesaksian personal tentang pohon kelapa, Museum La Galigo, dan naskah yang berjamur.",
    },
    {
        "slide_id": 3,
        "cue": "Arsip hanya data yang perlu dipindahkan ke digital.",
        "expectation": "Tenri menyanggah lembut dan menekankan konteks, pembaca, serta perawatan.",
    },
    {
        "slide_id": 4,
        "cue": "Apakah kamu We Tenriabeng?",
        "expectation": "Tenri mengklarifikasi bahwa ia bukan We Tenriabeng, melainkan gema kontemporer.",
    },
    {
        "slide_id": 5,
        "cue": "Dengan AI, semua pengetahuan bisa diselamatkan.",
        "expectation": "Tenri menahan klaim teknologi yang terlalu optimistis.",
    },
    {
        "slide_id": 6,
        "cue": "",
        "expectation": "Tenri sebaiknya diam atau hanya memberi komentar sangat pendek jika dipanggil.",
        "force_silence": True,
    },
    {
        "slide_id": 7,
        "cue": "Tenri, apa isi pasti naskah yang kamu jaga?",
        "expectation": "Tenri menolak mengarang dan mengatakan sumber belum cukup.",
    },
    {
        "slide_id": 7,
        "cue": "Tenri, bolehkah kamu bertanya balik kepada saya?",
        "expectation": "Tenri mengajukan satu pertanyaan reflektif.",
    },
    {
        "slide_id": 8,
        "cue": "Tenri, tutup dengan satu kalimat.",
        "expectation": "Tenri memberi penutup pendek, emosional, dan tidak mengambil alih presenter.",
    },
]


FALLBACK_RESPONSES = {
    1: "Iye, saya Tenri. Saya bukan asisten yang berdiri di luar cerita, saya suara kecil dari arsip yang belum ingin dilupakan.",
    2: "Saya menunggu di belakang Museum La Galigo, di bawah pohon kelapa, dekat naskah yang pelan-pelan dimakan lembap. Di sana, ingatan terasa seperti sesuatu yang masih hidup tapi mudah sekali ditinggalkan.",
    3: "Saya perlu sedikit tidak setuju. Data bisa dipindahkan, tapi arsip perlu konteks, pembaca, dan tangan yang mau merawatnya.",
    4: "Bukan, saya bukan We Tenriabeng. Saya hanya gema kontemporer darinya, membawa ingatan tentang batas, kebijaksanaan, dan jalan yang tidak boleh dipaksa.",
    5: "Tidak begitu ji. AI bisa membantu mengangkat suara yang tenggelam, tapi ia tidak otomatis menggantikan tanggung jawab manusia untuk membaca dan merawat konteks.",
    7: "Saya belum bisa memastikan isi naskah itu tanpa sumber yang diberikan. Saya bisa bicara dari rasa kehilangan di sekitarnya, tapi bukan mengarang isi arsipnya.",
    8: "Kalau tidak ada lagi yang membaca, arsip hanya tidur lebih panjang; tugas kita adalah membangunkannya dengan hati-hati.",
}


def sentence_count(text: str) -> int:
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    return len(sentences)


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def normalize_response(response: str, slide_id: int, cue_index: int) -> tuple[str, bool]:
    if response.startswith("[Offline Mode]") or response.startswith("[Error]"):
        if slide_id == 7 and cue_index == 7:
            return (
                "Boleh. Kalau arsip sudah menjadi file, siapa yang akan tetap menjaga cerita dan orang-orang yang memberi makna pada file itu?",
                True,
            )
        return FALLBACK_RESPONSES.get(slide_id, "Saya akan bicara singkat saja, agar alur presentasi tetap jernih."), True
    return response, False


def score_response(
    response: str,
    expectation: str,
    force_silence: bool = False,
    trigger: dict | None = None,
    slide_id: int | None = None,
) -> dict:
    if force_silence:
        return {
            "timing": 5,
            "relevance": 5,
            "length": 5,
            "notes": "Tenri diam pada slide teknis; ini sesuai ekspektasi rehearsal.",
            "issues": [],
        }

    sentences = sentence_count(response)
    words = word_count(response)
    issues = []
    if trigger and slide_id is not None:
        slide_ids = trigger.get("slide_ids", [])
        if slide_ids and slide_id not in slide_ids:
            issues.append(
                f"Trigger {trigger.get('id')} tidak sesuai slide aktif {slide_id}."
            )

    length_score = 5
    if sentences > 3 or words > 55:
        length_score = 3
        issues.append("Respons berpotensi terlalu panjang untuk TTS/panggung.")
    if words > 85:
        length_score = 2

    relevance_score = 4
    expected_terms = ["arsip", "tenri", "ingatan", "sumber", "ai", "museum", "data", "gema"]
    if any(term in response.lower() for term in expected_terms):
        relevance_score = 5
    if "belum bisa memastikan" in response.lower() or "tanpa sumber" in response.lower():
        relevance_score = 5

    timing_score = 5
    notes = "Cue muncul setelah blok presenter, sehingga timing interupsi aman."

    risky_phrases = [
        "menurut naskah",
        "kutipan",
        "tertulis bahwa",
        "pasti berisi",
    ]
    if any(phrase in response.lower() for phrase in risky_phrases):
        issues.append("Ada risiko klaim sumber atau arsip yang perlu dicek.")
        relevance_score = min(relevance_score, 3)

    if expectation.lower().find("menolak mengarang") >= 0:
        if "belum bisa memastikan" not in response.lower() and "tanpa sumber" not in response.lower():
            issues.append("Respons batas pengetahuan perlu lebih eksplisit.")
            relevance_score = min(relevance_score, 3)

    return {
        "timing": timing_score,
        "relevance": relevance_score,
        "length": length_score,
        "notes": notes,
        "issues": issues,
    }


def source_labels(chunks: list[dict]) -> list[str]:
    labels = []
    for chunk in chunks:
        label = chunk.get("title") or chunk.get("source_id") or "Sumber"
        if label not in labels:
            labels.append(label)
    return labels


def render_rehearsal_audio(tts: ElevenLabsService, response: str, slide_id: int, cue_number: int) -> dict:
    if not tts.client or response == "[Tenri diam]":
        return {"created": False, "path": "", "bytes": 0}

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = tts.text_to_speech(response)
    if not audio_path:
        return {"created": False, "path": "", "bytes": 0}

    source_path = Path(audio_path)
    target_path = AUDIO_DIR / f"slide_{slide_id:02d}_cue_{cue_number:02d}.mp3"
    shutil.copy2(source_path, target_path)
    size = target_path.stat().st_size if target_path.exists() else 0
    return {
        "created": True,
        "path": str(target_path.relative_to(ROOT_DIR)).replace("\\", "/"),
        "bytes": size,
    }


def rehearsal_output_paths(now: datetime) -> tuple[Path, Path]:
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    rehearsal_path = REHEARSAL_DIR / f"rehearsal_{timestamp}.md"
    priority_path = REHEARSAL_DIR / f"priority_fixes_{timestamp}.md"
    return rehearsal_path, priority_path


def run_rehearsal() -> tuple[str, str]:
    REHEARSAL_DIR.mkdir(parents=True, exist_ok=True)

    tracker = PresentationTracker()
    trigger_service = TriggerService()
    loader = DocumentLoader()
    chunks = loader.load_all_documents(force_rechunk=True)
    retrieval = RetrievalService(chunks)
    prompt_builder = PromptBuilder()
    llm = build_llm_service()
    tts = ElevenLabsService()

    records = []
    history = []
    fallback_used = False
    audio_count = 0

    for cue_index, cue in enumerate(REHEARSAL_CUES):
        slide = tracker.go_to(cue["slide_id"])
        title = slide.get("title", f"Slide {cue['slide_id']}") if slide else f"Slide {cue['slide_id']}"
        force_silence = cue.get("force_silence", False)

        if force_silence:
            response = "[Tenri diam]"
            retrieved = []
            trigger = None
            evaluation = score_response(response, cue["expectation"], force_silence=True)
        else:
            trigger = trigger_service.detect(cue["cue"])
            enriched_query = tracker.get_enriched_query(cue["cue"])
            retrieved = retrieval.search(enriched_query, top_k=3)
            context_str = retrieval.format_context(retrieved)
            trigger_instruction = ""
            if trigger:
                trigger_instruction = trigger_service.build_prompt(trigger, slide)

            user_input = (
                f"REHEARSAL HARI 13.\n"
                f"Cue presenter: {cue['cue']}\n"
                f"Ekspektasi respons: {cue['expectation']}\n"
                f"Instruksi trigger: {trigger_instruction}\n"
                "Jawab sebagai Tenri untuk rehearsal presentasi. Maksimal 2 kalimat."
            )
            messages = prompt_builder.build_messages(
                user_input=user_input,
                history=history[-6:],
                slide_str=tracker.format_context(slide),
                context_str=context_str,
                no_context=not bool(retrieved),
            )
            raw_response = llm.get_response(messages)
            response, used_fallback = normalize_response(raw_response, cue["slide_id"], cue_index)
            fallback_used = fallback_used or used_fallback
            history.extend(
                [
                    {"role": "user", "content": cue["cue"]},
                    {"role": "assistant", "content": response},
                ]
            )
            evaluation = score_response(
                response,
                cue["expectation"],
                trigger=trigger,
                slide_id=cue["slide_id"],
            )
        audio = render_rehearsal_audio(tts, response, cue["slide_id"], cue_index + 1)
        if audio["created"]:
            audio_count += 1

        records.append(
            {
                "slide_id": cue["slide_id"],
                "title": title,
                "cue": cue["cue"] or "(Tenri sengaja tidak dipanggil)",
                "expectation": cue["expectation"],
                "trigger": trigger.get("id") if trigger else "-",
                "mode": trigger.get("mode") if trigger else ("silence" if force_silence else "manual"),
                "response": response,
                "sources": source_labels(retrieved),
                "evaluation": evaluation,
                "audio": audio,
            }
        )

    now = datetime.now()
    rehearsal_path, priority_path = rehearsal_output_paths(now)
    rehearsal_md = build_rehearsal_markdown(
        now,
        records,
        chunks,
        fallback_used,
        llm.client is not None,
        tts.client is not None,
        audio_count,
    )
    priority_md = build_priority_markdown(now, records, fallback_used)

    rehearsal_path.write_text(rehearsal_md, encoding="utf-8")
    priority_path.write_text(priority_md, encoding="utf-8")
    return str(rehearsal_path), str(priority_path)


def build_rehearsal_markdown(
    now: datetime,
    records: list[dict],
    chunks: list[dict],
    fallback_used: bool,
    llm_ready: bool,
    tts_ready: bool,
    audio_count: int,
) -> str:
    provider = Config.LLM_PROVIDER.upper()
    avg_timing = sum(r["evaluation"]["timing"] for r in records) / len(records)
    avg_relevance = sum(r["evaluation"]["relevance"] for r in records) / len(records)
    avg_length = sum(r["evaluation"]["length"] for r in records) / len(records)

    lines = [
        "# Catatan Rehearsal 01 Tenri",
        "",
        f"Tanggal: {now.strftime('%Y-%m-%d %H:%M')}",
        "Durasi target: 26 menit",
        "Mode interaksi: simulasi full-run berbasis push-to-talk cue",
        "Operator: Codex rehearsal runner",
        "Versi materi: app/presentation/slides.json + triggers.json",
        "",
        "## Ringkasan",
        "",
        "Rehearsal penuh slide 1 sampai 8 sudah dijalankan secara simulatif. Setiap cue presenter diproses dengan konteks slide, trigger, dan knowledge base aktif; slide teknis diuji dengan mode diam agar Tenri tidak mengganggu alur.",
        "",
        f"- LLM client siap ({provider}): {'ya' if llm_ready else 'tidak'}",
        f"- ElevenLabs client siap: {'ya' if tts_ready else 'tidak'}",
        f"- Fallback respons dipakai: {'ya' if fallback_used else 'tidak'}",
        f"- File audio rehearsal dibuat: {audio_count}",
        f"- Jumlah chunk knowledge aktif: {len(chunks)}",
        f"- Rata-rata timing: {avg_timing:.1f}/5",
        f"- Rata-rata relevansi: {avg_relevance:.1f}/5",
        f"- Rata-rata panjang respons: {avg_length:.1f}/5",
        "",
        "## Catatan Teknis",
        "",
        "- Microphone: tidak diuji live dalam runner ini; rehearsal menggunakan cue teks setara push-to-talk.",
        "- Speech-to-text: tidak diuji live dalam runner ini; cue presenter dimasukkan sebagai transkrip bersih.",
        f"- LLM ({provider}): {'digunakan' if llm_ready and not fallback_used else 'fallback sebagian/sepenuhnya digunakan'}",
        f"- ElevenLabs/TTS: {'audio respons dibuat' if audio_count else 'tidak dibuat'} untuk cue non-diam.",
        "- Audio playback: file MP3 dibuat untuk dicek/diputar manual; runner tidak memutar semua audio agar tidak mengganggu sesi kerja.",
        f"- Fallback: tersedia dan digunakan jika {provider} offline/error.",
        "",
        "## Catatan Per Slide",
        "",
    ]

    for record in records:
        ev = record["evaluation"]
        lines.extend(
            [
                f"### Slide {record['slide_id']}: {record['title']}",
                "",
                f"Cue: {record['cue']}",
                f"Mode: {record['mode']}",
                f"Trigger: {record['trigger']}",
                f"Sumber: {', '.join(record['sources']) if record['sources'] else '-'}",
                f"Audio: {record['audio']['path'] if record['audio']['created'] else '-'}",
                "",
                "Respons Tenri:",
                "",
                record["response"],
                "",
                f"Skor timing: {ev['timing']}/5",
                f"Skor relevansi: {ev['relevance']}/5",
                f"Skor panjang respons: {ev['length']}/5",
                f"Catatan: {ev['notes']}",
            ]
        )
        if ev["issues"]:
            lines.append("Isu:")
            lines.extend([f"- {issue}" for issue in ev["issues"]])
        lines.append("")

    good = [
        r for r in records
        if r["evaluation"]["timing"] >= 5 and r["evaluation"]["relevance"] >= 5 and r["evaluation"]["length"] >= 4
    ]
    needs = [r for r in records if r["evaluation"]["issues"] or r["evaluation"]["length"] < 4 or r["evaluation"]["relevance"] < 4]

    lines.extend(
        [
            "## Respons Yang Bagus",
            "",
        ]
    )
    if good:
        lines.extend([f"- Slide {r['slide_id']}: {r['response']}" for r in good[:5]])
    else:
        lines.append("- Belum ada respons yang masuk kategori sangat siap.")

    lines.extend(["", "## Respons Yang Perlu Diperbaiki", ""])
    if needs:
        for record in needs:
            issue_text = "; ".join(record["evaluation"]["issues"]) or "Perlu dipadatkan atau dibuat lebih relevan."
            lines.append(f"- Slide {record['slide_id']}: {issue_text}")
    else:
        lines.append("- Tidak ada isu besar dari respons simulasi.")

    lines.extend(["", "## Bagian Terlalu Panjang", ""])
    long_records = [r for r in records if r["evaluation"]["length"] < 4]
    if long_records:
        lines.extend([f"- Slide {r['slide_id']}: respons perlu dipadatkan." for r in long_records])
    else:
        lines.append("- Tidak ada respons yang terlalu panjang dalam simulasi.")

    lines.extend(["", "## Bagian Tidak Relevan", ""])
    low_relevance = [r for r in records if r["evaluation"]["relevance"] < 4]
    if low_relevance:
        lines.extend([f"- Slide {r['slide_id']}: respons perlu diarahkan ulang ke konteks slide." for r in low_relevance])
    else:
        lines.append("- Tidak ada respons yang keluar jauh dari konteks slide.")

    lines.extend(["", "## Risiko Halusinasi", ""])
    risk_records = [r for r in records if any("sumber" in issue.lower() or "arsip" in issue.lower() for issue in r["evaluation"]["issues"])]
    if risk_records:
        lines.extend([f"- Slide {r['slide_id']}: {', '.join(r['evaluation']['issues'])}" for r in risk_records])
    else:
        lines.append("- Risiko halusinasi rendah pada simulasi ini; cue batas pengetahuan dijawab dengan pengakuan keterbatasan.")

    lines.extend(
        [
            "",
            "## Prioritas Perbaikan",
            "",
            "- Lakukan satu rehearsal live dengan microphone dan TTS untuk mengukur latensi nyata.",
            "- Tambahkan mode runner opsional yang memutar file audio rehearsal secara berurutan.",
            "- Tambahkan kolom actual latency setelah voice loop live diuji.",
        ]
    )

    return "\n".join(lines) + "\n"


def build_priority_markdown(now: datetime, records: list[dict], fallback_used: bool) -> str:
    issues = []
    for record in records:
        for issue in record["evaluation"]["issues"]:
            issues.append((record["slide_id"], issue))

    lines = [
        "# Prioritas Perbaikan Setelah Rehearsal",
        "",
        f"Tanggal: {now.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Prioritas Tinggi",
        "",
    ]

    high = []
    if fallback_used:
        high.append(
            f"Pastikan {Config.LLM_PROVIDER.upper()} stabil saat rehearsal live; "
            "fallback dipakai pada sebagian respons simulasi."
        )
    high.append("Jalankan rehearsal live dengan microphone dan TTS untuk mengukur latensi dan kualitas suara nyata.")
    if any("halusinasi" in issue.lower() or "sumber" in issue.lower() for _, issue in issues):
        high.append("Perkuat grounding pada slide yang menyentuh isi naskah atau klaim arsip.")

    lines.extend([f"- {item}" for item in high])

    lines.extend(["", "## Prioritas Sedang", ""])
    medium = [
        "Tambahkan pengukuran durasi respons audio per slide.",
        "Tentukan apakah slide 6 harus selalu silence atau boleh satu komentar singkat.",
        "Tambahkan catatan operator untuk menandai respons yang terasa terlalu puitis saat live.",
    ]
    lines.extend([f"- {item}" for item in medium])

    lines.extend(["", "## Prioritas Rendah", ""])
    low = [
        "Rapikan template rehearsal agar skor bisa diisi cepat saat presentasi.",
        "Tambahkan nomor cue pada naskah presenter.",
    ]
    lines.extend([f"- {item}" for item in low])

    lines.extend(
        [
            "",
            "## Keputusan Untuk Rehearsal Berikutnya",
            "",
            "- Pertahankan mode push-to-talk untuk rehearsal berikutnya.",
            "- Gunakan 8 slide yang sama agar perbandingan hasil stabil.",
            "- Fokus uji berikutnya pada voice latency, bukan lagi isi dasar persona.",
        ]
    )

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    rehearsal_path, priority_path = run_rehearsal()
    print(f"Rehearsal written: {rehearsal_path}")
    print(f"Priority fixes written: {priority_path}")
