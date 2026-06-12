from app.utils.text_utils import (
    format_tenri_voice_response,
    humanize_tenri_response,
    trim_to_character_budget,
    trim_response,
)


class TestTrimResponse:
    def test_empty_string_returns_empty(self):
        assert trim_response("") == ""

    def test_single_sentence_unchanged(self):
        text = "La Galigo adalah epos besar."
        assert trim_response(text) == text

    def test_two_sentences_within_limit(self):
        text = "La Galigo adalah epos besar. Ia berasal dari Bugis."
        assert trim_response(text, max_sentences=3) == text

    def test_trims_to_max_sentences(self):
        text = "Kalimat satu. Kalimat dua. Kalimat tiga. Kalimat empat."
        result = trim_response(text, max_sentences=2)
        assert result == "Kalimat satu. Kalimat dua."

    def test_default_max_is_three(self):
        text = "Satu. Dua. Tiga. Empat. Lima."
        result = trim_response(text)
        assert result == "Satu. Dua. Tiga."

    def test_exclamation_mark_split(self):
        text = "Ini penting! Jangan lupa. Sungguh penting! Tambahan ekstra."
        result = trim_response(text, max_sentences=2)
        assert result == "Ini penting! Jangan lupa."

    def test_question_mark_split(self):
        text = "Apakah kamu tahu? Ini jawabannya. Sungguh? Betul sekali."
        result = trim_response(text, max_sentences=2)
        assert result == "Apakah kamu tahu? Ini jawabannya."

    def test_max_one_sentence(self):
        text = "Kalimat pertama. Kalimat kedua."
        assert trim_response(text, max_sentences=1) == "Kalimat pertama."

    def test_no_sentence_boundary_returns_full(self):
        text = "Ini adalah teks tanpa tanda titik di akhir"
        assert trim_response(text, max_sentences=1) == text

    def test_strips_leading_trailing_whitespace(self):
        text = "  La Galigo adalah epos besar. Ia dari Bugis.  "
        result = trim_response(text, max_sentences=1)
        assert result == "La Galigo adalah epos besar."

    def test_mid_sentence_period_not_split(self):
        # Abbreviation-style periods should NOT split (no trailing space)
        text = "Tenri v1.0.0 dirilis hari ini. Versi berikutnya akan lebih baik."
        result = trim_response(text, max_sentences=1)
        assert result == "Tenri v1.0.0 dirilis hari ini."

    def test_sentences_ending_in_numbers_respect_limit(self):
        text = "Ini kalimat 1. Ini kalimat 2. Ini kalimat 3."

        result = trim_response(text, max_sentences=2)

        assert result == "Ini kalimat 1. Ini kalimat 2."

    def test_year_at_sentence_end_is_a_boundary(self):
        text = "Arsip ini ditemukan pada tahun 2024. Penelitian berlanjut pada 2025."

        result = trim_response(text, max_sentences=1)

        assert result == "Arsip ini ditemukan pada tahun 2024."

    def test_decimal_is_not_a_sentence_boundary(self):
        text = "Nilainya naik menjadi 3.5 persen. Kenaikan itu perlu diperiksa."

        result = trim_response(text, max_sentences=1)

        assert result == "Nilainya naik menjadi 3.5 persen."

    def test_unicode_text(self):
        text = "Sawerigading adalah tokoh La Galigo. We Tenriabeng adalah saudarinya."
        result = trim_response(text, max_sentences=1)
        assert result == "Sawerigading adalah tokoh La Galigo."


class TestHumanizeTenriResponse:
    def test_removes_leading_ai_filler(self):
        text = "Tentu saja, arsip bukan cuma data."
        assert humanize_tenri_response(text) == "Arsip bukan cuma data."

    def test_removes_question_template(self):
        text = "Pertanyaan yang menarik. Ingatan tidak selesai hanya karena dipindahkan."
        assert humanize_tenri_response(text) == "Ingatan tidak selesai hanya karena dipindahkan."

    def test_rewrites_context_phrase(self):
        text = "Berdasarkan konteks yang diberikan, digitalisasi belum cukup."
        assert humanize_tenri_response(text) == "Dari konteks yang ada, digitalisasi belum cukup."

    def test_removes_sterile_conclusion_phrase(self):
        text = "Dapat disimpulkan bahwa arsip perlu dirawat."
        assert humanize_tenri_response(text) == "Arsip perlu dirawat."

    def test_keeps_offline_fallback_unchanged(self):
        text = "[Offline Mode] Maaf, koneksi ke Groq API tidak aktif."
        assert humanize_tenri_response(text) == text


class TestTrimToCharacterBudget:
    def test_keeps_text_under_budget(self):
        text = "Arsip bukan cuma data. Ia membawa konteks hidup."

        assert trim_to_character_budget(text, max_chars=80) == text

    def test_prefers_whole_sentences(self):
        text = (
            "AI membaca pola dari data. "
            "Audiens perlu tahu bahwa hasilnya tetap harus diperiksa. "
            "Jangan serahkan keputusan penting begitu saja."
        )

        result = trim_to_character_budget(text, max_chars=70)

        assert result == "AI membaca pola dari data."
        assert len(result) <= 70

    def test_cuts_long_first_sentence_at_word_boundary(self):
        text = (
            "Digitalisasi membantu arsip bertahan lebih lama tetapi tidak otomatis "
            "menjaga konteks sosial yang membuatnya bermakna bagi komunitas."
        )

        result = trim_to_character_budget(text, max_chars=82)

        assert len(result) <= 82
        assert result.endswith(".")
        assert "komunitas" not in result


class TestFormatTenriVoiceResponse:
    def test_removes_unicode_bullet_prefixes(self):
        text = "• Poin pertama penting. • Poin kedua juga."

        result = format_tenri_voice_response(text)

        assert "•" not in result
        assert result == "Poin pertama penting. Poin kedua juga."

    def test_removes_markdown_and_list_prefixes(self):
        text = "1. **AI bukan makhluk hidup.** 2. Ia membaca pola dari data."

        result = format_tenri_voice_response(text)

        assert "**" not in result
        assert not result.startswith("1.")
        assert result == "AI bukan makhluk hidup. Ia membaca pola dari data."

    def test_removes_sterile_closing_prefix(self):
        text = "AI membaca pola. Kesimpulannya, jangan perlakukan outputnya sebagai kebenaran mutlak."

        result = format_tenri_voice_response(text)

        assert result == "AI membaca pola. Jangan perlakukan outputnya sebagai kebenaran mutlak."

    def test_keeps_stage_arc_when_response_is_too_long(self):
        text = (
            "AI bukan benar-benar berpikir. "
            "Ia membaca pola dari data yang diberikan. "
            "Ia bisa membantu manusia bekerja lebih cepat. "
            "Tapi keputusan tetap perlu dijaga oleh manusia."
        )

        result = format_tenri_voice_response(text)

        assert result == (
            "AI bukan benar-benar berpikir. "
            "Ia membaca pola dari data yang diberikan. "
            "Tapi keputusan tetap perlu dijaga oleh manusia."
        )

    def test_deduplicates_repeated_sentences(self):
        text = "Arsip bukan cuma data. Arsip bukan cuma data. Ia butuh konteks."

        result = format_tenri_voice_response(text)

        assert result == "Arsip bukan cuma data. Ia butuh konteks."

    def test_respects_max_sentences(self):
        text = "Satu gagasan. Penguatan penting. Penutup terasa."

        result = format_tenri_voice_response(text, max_sentences=2)

        assert result == "Satu gagasan. Penguatan penting."

    def test_merges_list_like_sentence_fragments(self):
        text = (
            "Fungsi kognitif manusia seperti belajar. "
            "Mengenali pola, mengambil keputusan, dan memahami bahasa."
        )

        result = format_tenri_voice_response(text)

        assert result == (
            "Fungsi kognitif manusia seperti belajar, "
            "mengenali pola, mengambil keputusan, dan memahami bahasa."
        )

    def test_merges_adalah_sentence_fragment(self):
        text = (
            "Kecerdasan Buatan, atau Artificial Intelligence. "
            "Adalah kemampuan mesin meniru fungsi kognitif manusia."
        )

        result = format_tenri_voice_response(text)

        assert result == (
            "Kecerdasan Buatan, atau Artificial Intelligence, "
            "adalah kemampuan mesin meniru fungsi kognitif manusia."
        )

    def test_rewrites_slide_reader_opening(self):
        text = (
            "Slide ini membuka konsep dasar mengenal kecerdasan buatan. "
            "AI membaca pola dari data, bukan berpikir seperti manusia."
        )

        result = format_tenri_voice_response(text, max_sentences=2)

        assert result == (
            "Konsep dasarnya adalah mengenal kecerdasan buatan. "
            "AI membaca pola dari data, bukan berpikir seperti manusia."
        )

    def test_drops_slide_title_and_agenda_opening(self):
        text = (
            "Mengenal Kecerdasan Buatan. "
            "Apa itu AI, bagaimana ia bekerja, dan mengapa relevan bagi kita sehari-hari. "
            "AI bukan robot yang tiba-tiba punya perasaan. "
            "Ia membaca pola dari data dan membantu manusia melihat sesuatu yang terlalu besar."
        )

        result = format_tenri_voice_response(text, max_sentences=2)

        assert result == (
            "AI bukan robot yang tiba-tiba punya perasaan. "
            "Ia membaca pola dari data dan membantu manusia melihat sesuatu yang terlalu besar."
        )

    def test_keeps_real_opening_when_not_slide_reading(self):
        text = (
            "AI bukan sekadar teknologi baru. "
            "Ia mengubah cara manusia mempercayai keputusan yang lahir dari data."
        )

        result = format_tenri_voice_response(text, max_sentences=2)

        assert result == text

    def test_keeps_offline_fallback_unchanged(self):
        text = "[Offline Mode] Maaf, koneksi ke Gemini API tidak aktif."

        assert format_tenri_voice_response(text) == text
