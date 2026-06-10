"""Lightweight BOW centroid classifier for intent classification.

Consulted only when the rule-based IntentClassifier returns AMBIENT — can upgrade
ambiguous short sentences to EXPLAINING if the pattern matches.

Design rationale
----------------
SBERT (the spec's preferred approach) requires sentence-transformers (~500 MB) which
is incompatible with Python 3.13.  This numpy-only BOW centroid approach achieves
<5 ms inference with no extra dependencies and covers the main gap: explanation
utterances shorter than the 15-word rule-based threshold.

How it works
------------
1. At init, tokenize all training examples and build per-category centroid vectors.
2. At predict(), compute cosine similarity of the input TF vector to each centroid.
3. Return (label, confidence) — confidence is the winning centroid's cosine score.
"""

import re
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("AICompanion.LocalIntentClassifier")

_PUNCT_RE = re.compile(r"[^\w\s]")

# Minimum cosine similarity for the local classifier to declare confidence.
# BOW vectors for short sentences are sparse, so 0.15 is intentionally lenient.
_MIN_CONFIDENCE = 0.15

# Training corpus — 10-15 examples per category covering Indonesian presenter speech.
# These examples intentionally target the *gap* cases: sentences short enough that
# the 15-word rule-based EXPLAINING threshold misses them.
_TRAINING_CORPUS: dict[str, list[str]] = {
    "asking_tenri": [
        "Tenri jelaskan bagian ini lebih detail",
        "Tenri apa maksud dari data ini",
        "hei Tenri bagaimana cara kerjanya",
        "Tenri ceritakan tentang naskah La Galigo",
        "bisa jelaskan lebih Tenri",
        "Tenri apakah informasi ini akurat",
        "apa pendapat kamu Tenri",
        "Tenri siapa itu Sawerigading",
        "tolong bantu jelaskan Tenri",
        "Tenri tambahkan konteks tentang ini",
        "Tenri kasih tahu saya",
        "hei Tenri ada info tentang ini",
    ],
    "asking_audience": [
        "teman-teman perhatikan slide ini baik-baik",
        "siapa yang pernah dengar La Galigo",
        "apakah kalian tahu tentang lontara",
        "ada yang bisa menjawab pertanyaan ini",
        "gimana menurut teman-teman semua",
        "coba kalian pikirkan sejenak",
        "ada pertanyaan dari teman-teman",
        "apakah kalian setuju dengan pernyataan ini",
        "raise your hand if you know",
        "apakah ada yang mau berbagi pengalaman",
        "siapa di sini yang pernah ke museum",
        "apakah kalian pernah melihat naskah lontara asli",
    ],
    "explaining": [
        # Short explanation utterances (≤ 14 words) — the exact gap in rules
        "jadi proses digitalisasi ini membutuhkan waktu yang lama",
        "maksudnya adalah data yang kita miliki perlu diverifikasi dulu",
        "artinya naskah lontara harus dipindai dengan sangat hati-hati",
        "dalam konteks ini pelestarian digital sangat penting sekali",
        "nah jadi intinya adalah metadata yang lengkap dan terstruktur",
        "kita tahu bahwa naskah ini sangat rapuh dan tua",
        "secara umum ada dua metode utama yang digunakan",
        "kalau kita lihat data ini hasilnya cukup mengejutkan",
        "berdasarkan penelitian tersebut hasilnya sangat signifikan dan jelas",
        "pada slide ini saya menjelaskan tahap pertama prosesnya",
        "langkah awalnya adalah mengidentifikasi dokumen yang sudah rusak",
        "di sini kita bisa melihat perbedaan yang nyata",
        "hari ini topiknya tentang pelestarian warisan budaya kita",
        "nah begini cara kerjanya secara teknis dan praktis",
        "ada dua faktor utama yang perlu kita perhatikan",
        "yang perlu dipahami adalah proses ini berlangsung bertahap",
        "contohnya seperti yang terlihat pada gambar di slide ini",
        "perlu diingat bahwa setiap naskah memiliki kondisi yang berbeda",
    ],
    "ambient": [
        # Short, ambiguous, non-explanatory utterances
        "hmm ya begitu saja",
        "ya betul sekali memang",
        "oh oke saya paham",
        "arsip hanya sekadar data biasa",
        "ini menarik juga sih",
        "saya rasa sudah cukup untuk ini",
        "kita lihat dulu hasilnya nanti",
        "mungkin ada yang terlewat di sini",
        "eh tunggu sebentar ya",
        "satu momen saya cek dulu",
        "oke baik baik terima kasih",
        "ya ya paham mengerti sudah",
        "hmm menarik juga ya memang",
        "data ini cukup jelas sebenarnya",
        "ini perlu dicek lebih lanjut",
        "sebentar saya cari dulu",
        "baik lanjut saja",
        "oke oke sudah mengerti",
    ],
}


def _tokenize(text: str) -> list[str]:
    cleaned = _PUNCT_RE.sub(" ", text.lower())
    return [t for t in cleaned.split() if len(t) > 2]


class LocalIntentClassifier:
    """BOW centroid intent classifier — fast fallback for the rule-based system.

    Inference time: < 5 ms on the built-in corpus.
    Dependencies: numpy only (no sentence-transformers / scikit-learn).

    Predicts one of: asking_tenri, asking_audience, explaining, ambient.
    CLOSING_TENRI is excluded — it is handled reliably by the rule-based system.

    Typical use: consult only when rule-based system returns AMBIENT.
    """

    def __init__(self, corpus: Optional[dict[str, list[str]]] = None) -> None:
        self._vocab: dict[str, int] = {}
        self._centroids: dict[str, np.ndarray] = {}
        self._build(_TRAINING_CORPUS if corpus is None else corpus)
        logger.debug(
            "LocalIntentClassifier ready: vocab=%d, categories=%s",
            len(self._vocab),
            list(self._centroids.keys()),
        )

    def _build(self, corpus: dict[str, list[str]]) -> None:
        """Tokenize corpus, build shared vocabulary, compute per-category centroids."""
        per_category: dict[str, list[list[str]]] = {}
        all_tokens: list[str] = []

        for label, examples in corpus.items():
            tokenized = [_tokenize(ex) for ex in examples]
            per_category[label] = tokenized
            all_tokens.extend(tok for tokens in tokenized for tok in tokens)

        if not all_tokens:
            return

        self._vocab = {tok: i for i, tok in enumerate(sorted(set(all_tokens)))}
        V = len(self._vocab)

        for label, tokenized_examples in per_category.items():
            valid = [t for t in tokenized_examples if t]
            if not valid:
                continue
            matrix = np.zeros((len(valid), V), dtype=np.float32)
            for row_idx, tokens in enumerate(valid):
                for tok in tokens:
                    if tok in self._vocab:
                        matrix[row_idx, self._vocab[tok]] += 1.0
            self._centroids[label] = matrix.mean(axis=0)

    def predict(self, text: str) -> tuple[str, float]:
        """Return (predicted_label, cosine_similarity_to_winning_centroid).

        Returns ("ambient", 0.0) when vocabulary has no overlap with training corpus
        or when text is empty.
        """
        if not self._vocab or not self._centroids:
            return "ambient", 0.0

        tokens = _tokenize(text)
        if not tokens:
            return "ambient", 0.0

        vec = np.zeros(len(self._vocab), dtype=np.float32)
        for tok in tokens:
            if tok in self._vocab:
                vec[self._vocab[tok]] += 1.0

        vec_norm = np.linalg.norm(vec)
        if vec_norm == 0.0:
            return "ambient", 0.0

        vec_normalized = vec / vec_norm

        best_label = "ambient"
        best_sim = 0.0

        for label, centroid in self._centroids.items():
            centroid_norm = np.linalg.norm(centroid)
            if centroid_norm == 0.0:
                continue
            sim = float(np.dot(vec_normalized, centroid / centroid_norm))
            if sim > best_sim:
                best_sim = sim
                best_label = label

        return best_label, best_sim

    @property
    def min_confidence(self) -> float:
        return _MIN_CONFIDENCE
