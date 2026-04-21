from app.utils.text import (
    build_topic_insights,
    chunk_text,
    clean_transcript_text,
    extract_candidate_topics,
)


def test_clean_transcript_text_normalizes_spacing() -> None:
    cleaned = clean_transcript_text("Hello   world\n[Music] this is a test")
    assert cleaned == "Hello world this is a test"


def test_chunk_text_splits_into_multiple_chunks() -> None:
    text = " ".join(f"word{i}" for i in range(450))
    chunks = chunk_text(text, target_words=200)
    assert len(chunks) == 3


def test_extract_candidate_topics_returns_ranked_topics() -> None:
    counter = extract_candidate_topics("python python ai ai ai tutorial developer", limit=5)
    primary, secondary = build_topic_insights(counter)
    assert primary[0][0] == "ai"
    assert secondary == []
