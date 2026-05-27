"""Embedding utility tests."""

import math

from api.utils.embeddings import cosine_similarity, generate_embedding


def test_embedding_has_correct_dimension():
    vec = generate_embedding("خرسانة مسلحة", dim=512)
    assert len(vec) == 512


def test_embedding_is_deterministic():
    a = generate_embedding("دهان بلاستيكي", dim=256)
    b = generate_embedding("دهان بلاستيكي", dim=256)
    assert a == b


def test_embedding_is_unit_norm():
    vec = generate_embedding("حديد تسليح قطر 12 مم", dim=512)
    norm = math.sqrt(sum(v * v for v in vec))
    assert norm == 0 or abs(norm - 1.0) < 1e-6


def test_cosine_similarity_basic():
    a = generate_embedding("خرسانة مسلحة 30 ميجا", dim=512)
    b = generate_embedding("خرسانة مسلحة 30 ميجا", dim=512)
    c = generate_embedding("دهان بلاستيكي درجة أولى", dim=512)

    assert cosine_similarity(a, b) > 0.99
    assert cosine_similarity(a, c) < 0.5


def test_similar_phrases_score_higher():
    base = generate_embedding("خرسانة مسلحة بمقاومة 30 ميجا", dim=512)
    similar = generate_embedding("خرسانة مسلحة 30 ميجا", dim=512)
    different = generate_embedding("مكيف سبليت 24000 وحدة", dim=512)

    assert cosine_similarity(base, similar) > cosine_similarity(base, different)


def test_empty_text_returns_zero_vector():
    vec = generate_embedding("", dim=128)
    assert vec == [0.0] * 128
