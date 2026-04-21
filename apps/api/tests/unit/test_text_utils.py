from app.utils.text import (
    build_topic_insights,
    chunk_text,
    clean_transcript_text,
    extract_candidate_topics,
    is_probably_transcript_text,
    looks_like_youtube_page_config,
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


def test_extract_candidate_topics_ignores_transcript_filler_words() -> None:
    counter = extract_candidate_topics(
        "the and game you but was games yeah think what game unity developer",
        limit=5,
    )

    assert "the" not in counter
    assert "and" not in counter
    assert "you" not in counter
    assert counter["game"] == 3
    assert "games" not in counter
    assert counter["unity"] == 1


def test_detects_youtube_page_config_as_not_transcript() -> None:
    page_config = (
        'WEB_PLAYER_CONTEXT_CONFIG_ID_KEVLAR_WATCH serializedExperimentFlags="'
        "html5_enable_sabr\\u003dtrue\\u0026web_player_autonav_use_server_provided_state\\u003dtrue"
        "\\u0026player_bootstrap_method\\u003dtrue"
        '" innertubeApiKey="AIzaSy..." window.ytcfg.set({})'
    )

    assert looks_like_youtube_page_config(page_config)
    assert not is_probably_transcript_text(page_config)


def test_accepts_natural_transcript_text() -> None:
    transcript = (
        "Today we are going to build a small game prototype and explain each design "
        "choice as we go through the submission. The first thing to notice is the pacing."
    )

    assert is_probably_transcript_text(transcript)
