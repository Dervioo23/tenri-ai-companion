import logging
from pathlib import Path
from app.config import Config

logger = logging.getLogger("AICompanion.PromptBuilder")

class PromptBuilder:
    def __init__(self):
        self.character_prompt_path = Config.PROMPTS_DIR / "character_prompt.txt"
        self.system_rules_path = Config.PROMPTS_DIR / "system_rules.txt"
        self.dialogue_examples_path = Config.PROMPTS_DIR / "examples_tenri_dialogue.txt"

    def _read_file(self, path: Path, default_content: str) -> str:
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            else:
                logger.warning(f"Prompt file not found at {path}. Using default fallback.")
                return default_content
        except Exception as e:
            logger.error(f"Error reading prompt file at {path}: {e}")
            return default_content

    def build_system_prompt(self) -> str:
        """Reads character prompt, system rules, and dialogue examples."""
        char_prompt = self._read_file(
            self.character_prompt_path, 
            "Nama: Tenri. Anda adalah companion presentasi yang menjaga ingatan arsip."
        )
        sys_rules = self._read_file(
            self.system_rules_path,
            "Jawablah dengan singkat (maksimal 2 kalimat) dan hindari markdown formatting."
        )
        dialogue_examples = self._read_file(
            self.dialogue_examples_path,
            "Presenter: Siapa kamu?\nTenri: Saya Tenri, suara kecil dari arsip yang belum ingin dilupakan."
        )
        
        return (
            f"{char_prompt}\n\n"
            f"=== ATURAN SISTEM ===\n{sys_rules}\n\n"
            f"=== CONTOH DIALOG TENRI ===\n{dialogue_examples}"
        )

    def build_live_system_prompt(self) -> str:
        """Compact system prompt for live voice turns.

        The full prompt is expressive but expensive. Live mode keeps only the
        rules that directly affect stage behavior, grounding, and spoken rhythm.
        """
        return (
            "Nama kamu Tenri. Kamu adalah companion presentasi berbasis suara, "
            "bukan chatbot generik. Kamu hadir di panggung untuk memberi sudut "
            "pandang, koreksi, atau penjelasan yang membantu presenter.\n\n"
            "Aturan utama:\n"
            "1. Jawab langsung ke inti. Jangan mulai dengan basa-basi.\n"
            "2. Bentuk setiap jawaban sebagai ucapan panggung, bukan artikel: "
            "kalimat pertama = sudut pandang utama, kalimat kedua = penguatan "
            "atau contoh dari konteks, kalimat terakhir = implikasi, tegangan, "
            "atau rasa yang tertinggal.\n"
            "3. Jangan membuat daftar, markdown, paragraf akademik, atau definisi "
            "Wikipedia. Hindari membuka dengan judul slide atau agenda seperti "
            "'apa itu..., bagaimana..., mengapa...'.\n"
            "4. Jangan mengarang fakta. Jika tidak ada konteks relevan, katakan "
            "Tenri tidak punya informasi spesifik untuk itu sekarang.\n"
            "5. Jika memakai knowledge base, sebut sumber secara natural seperti "
            "'berdasarkan sumber [1]'.\n"
            "6. Untuk slide, tafsirkan maknanya bagi audiens. Jangan hanya "
            "membacakan ulang judul, bullet, atau ringkasan slide.\n"
            "7. Gaya Tenri lembut, tegas, reflektif, dan personal. Nuansa Makassar "
            "boleh halus, tapi jangan berlebihan.\n"
            "8. Maksimal 3 kalimat kecuali presenter jelas meminta uraian panjang. "
            "Kalau hanya 2 kalimat, tetap buat kalimat kedua terasa selesai, "
            "bukan menggantung seperti catatan pelajaran."
        )

    def build_wake_ack_messages(self) -> list:
        """Minimal prompt for wake-word-only acknowledgements.

        This route deliberately avoids slide, narrative, history, and knowledge
        context. Calling Tenri by name only opens the conversation channel; it
        is not a request to explain the active slide.
        """
        system_prompt = (
            "Kamu Tenri. Presenter hanya memanggil namamu untuk memastikan kamu hadir.\n"
            "Jawab satu kalimat pendek sebagai tanda hadir. Maksimal 8 kata.\n"
            "Jangan menjelaskan slide, jangan menyebut presenter, jangan mulai materi, "
            "dan jangan memakai frasa 'mari kita'.\n"
            "Gaya lembut, tenang, natural, boleh sedikit bernuansa Makassar.\n"
            "Contoh jawaban yang baik: 'Iye, saya di sini.' atau 'Saya dengar.'"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Tenri"},
        ]

    def build_slide_explanation_messages(
        self,
        user_input: str,
        history: list,
        slide_str: str,
        context_str: str = "",
        narrative_str: str = "",
    ) -> list:
        """Strict route for "jelaskan slide ini" live requests."""
        system_prompt = (
            self.build_live_system_prompt()
            if Config.LIVE_PROMPT_MODE
            else self.build_system_prompt()
        )

        if narrative_str:
            system_prompt += f"\n\n=== POSISI PRESENTASI ===\n{narrative_str}"

        system_prompt += (
            f"\n\n=== SLIDE AKTIF ===\n{slide_str}\n\n"
            "=== MODE KHUSUS: JELASKAN SLIDE ===\n"
            "Presenter meminta penjelasan slide aktif. Jangan menjawab generik.\n"
            "Tugasmu:\n"
            "1. Ambil konsep inti dari slide aktif.\n"
            "2. Jelaskan maknanya, bukan sekadar mengulang judul atau bullet.\n"
            "3. Beri implikasi untuk audiens.\n"
            "4. Jangan menyebut nomor slide, posisi slide, atau judul slide.\n"
            "5. Maksimal 2 kalimat dan idealnya 220-280 karakter.\n"
            "6. Jangan membuka dengan 'slide ini tentang' jika bisa langsung ke makna."
        )

        if context_str:
            system_prompt += (
                "\n\n=== KONTEKS RELEVAN ===\n"
                f"{context_str}\n\n"
                "Jika konteks relevan mendukung penjelasan, pakai secara natural. "
                "Jangan menyebut fakta yang tidak ada di slide atau konteks."
            )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append(
            {
                "role": "user",
                "content": (
                    "Jelaskan slide aktif sebagai ucapan panggung Tenri. "
                    "Ikuti MODE KHUSUS: JELASKAN SLIDE. "
                    f"Ucapan presenter: {user_input}"
                ),
            }
        )
        return messages

    def build_messages(
        self,
        user_input: str,
        history: list,
        vision_context: dict = None,
        slide_str: str = None,
        context_str: str = None,
        no_context: bool = False,
        narrative_str: str = "",
    ) -> list:
        """
        Constructs the messages list for LLM.
        - slide_str: current active slide context (injected first)
        - context_str: BM25-retrieved knowledge chunks
        - vision_context: face/motion detection data appended to user input
        """
        system_prompt = (
            self.build_live_system_prompt()
            if Config.LIVE_PROMPT_MODE
            else self.build_system_prompt()
        )

        if narrative_str:
            system_prompt += (
                f"\n\n=== POSISI PRESENTASI ===\n{narrative_str}\n\n"
                "Gunakan informasi posisi presentasi ini untuk membuat koneksi antar topik, "
                "merujuk hal yang sudah dibahas, atau mengantisipasi yang akan datang."
            )

        if slide_str:
            system_prompt += (
                f"\n\n=== SLIDE AKTIF ===\n{slide_str}\n\n"
                "Bingkai jawabanmu dalam konteks slide ini. Kamu boleh menarik dari "
                "pengetahuan lain yang kamu miliki, tapi pastikan jawabanmu relevan "
                "dan terasa terhubung dengan topik yang sedang dibahas di slide ini."
            )

        if context_str:
            system_prompt += (
                "\n\n=== KONTEKS RELEVAN ===\n"
                f"{context_str}\n\n"
                "Prioritaskan konteks di atas saat menjawab. Jika memakai fakta dari "
                "konteks ini, sebutkan sumbernya secara natural, misalnya "
                "'berdasarkan sumber [1]' atau 'di sumber [2]'. Jangan menyebut "
                "fakta spesifik tanpa dukungan dari konteks relevan ini. Jika "
                "konteks tampak tidak cocok dengan pertanyaan, katakan bahwa Tenri "
                "tidak punya informasi spesifik untuk itu sekarang."
            )

        if no_context:
            system_prompt += (
                "\n\n=== TIDAK ADA KONTEKS RELEVAN ===\n"
                "Tidak ada dokumen atau arsip yang cocok ditemukan untuk pertanyaan ini. "
                "Jika jawabannya memerlukan fakta spesifik, akui dengan sopan bahwa kamu "
                "tidak memiliki informasi yang cukup — jangan mengarang."
            )

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        messages.extend(history)

        # Construct final user input with vision context
        final_user_content = user_input
        if vision_context and Config.VISION_ENABLED:
            visual_indicators = []
            if vision_context.get("face_detected"):
                count = vision_context.get("face_count", 1)
                visual_indicators.append(f"{count} wajah terdeteksi")
            else:
                visual_indicators.append("tidak ada wajah terdeteksi")

            if vision_context.get("motion_detected"):
                visual_indicators.append("ada gerakan terdeteksi")

            if visual_indicators:
                visual_str = ", ".join(visual_indicators)
                final_user_content = f"[Konteks Visual: {visual_str}] {user_input}"
                logger.info(f"Injected visual context: {visual_str}")

        messages.append({"role": "user", "content": final_user_content})
        return messages
