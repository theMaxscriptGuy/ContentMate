import html
import re
from collections import Counter

STOPWORDS = {
    "able",
    "actually",
    "all",
    "almost",
    "already",
    "always",
    "am",
    "an",
    "and",
    "any",
    "anyone",
    "anything",
    "about",
    "after",
    "again",
    "also",
    "amp",
    "api",
    "are",
    "around",
    "because",
    "been",
    "before",
    "being",
    "bit",
    "both",
    "but",
    "can",
    "channel",
    "could",
    "content",
    "did",
    "didn",
    "does",
    "doing",
    "don",
    "enable",
    "enablejsapi",
    "even",
    "every",
    "false",
    "for",
    "from",
    "get",
    "got",
    "had",
    "has",
    "have",
    "having",
    "hey",
    "hi",
    "html",
    "html5",
    "http",
    "https",
    "ill",
    "i'll",
    "i'm",
    "im",
    "is",
    "isn",
    "it",
    "its",
    "into",
    "just",
    "know",
    "like",
    "lot",
    "made",
    "make",
    "maybe",
    "me",
    "more",
    "most",
    "much",
    "nice",
    "not",
    "now",
    "okay",
    "one",
    "only",
    "out",
    "player",
    "play",
    "playing",
    "right",
    "really",
    "see",
    "seen",
    "should",
    "so",
    "some",
    "something",
    "still",
    "stream",
    "streaming",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "they",
    "thing",
    "think",
    "this",
    "till",
    "today",
    "true",
    "u0026",
    "u003d",
    "uh",
    "um",
    "was",
    "we",
    "well",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "url",
    "video",
    "videos",
    "want",
    "way",
    "web",
    "with",
    "widget",
    "would",
    "yeah",
    "yes",
    "you",
    "youre",
    "you're",
    "your",
}

TOPIC_BUCKETS = {
    "ai": {"ai", "openai", "gpt", "agent", "automation", "prompt"},
    "business": {"business", "startup", "sales", "marketing", "finance", "revenue"},
    "education": {"learn", "tutorial", "guide", "course", "lesson", "explained"},
    "gaming": {"game", "gaming", "minecraft", "roblox", "fps", "stream"},
    "technology": {"software", "tech", "coding", "developer", "programming", "python"},
    "lifestyle": {"routine", "mindset", "health", "fitness", "productivity", "life"},
}

NOISE_PATTERNS = (
    r"u00[0-9a-f]{2}",
    r"html5",
    r"enablejsapi",
    r"widgetid",
    r"origin",
    r"player",
)

YOUTUBE_PAGE_CONFIG_MARKERS = (
    "web_player_context_config",
    "serializedexperimentflags",
    "serializedclientexperimentflags",
    "innertubeapikey",
    "window.ytcfg",
    "ytcfg.set",
    "player_bootstrap_method",
    "trustedjsurl",
    "trustedcssurl",
    "xsrf_token",
    "client_transport",
    "live_chat_base_tango_config",
)


def clean_transcript_text(raw_text: str) -> str:
    text = html.unescape(raw_text)
    text = text.replace("\\u003d", " ").replace("\\u0026", " ")
    text = text.replace("u003d", " ").replace("u0026", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?:%s)" % "|".join(NOISE_PATTERNS), " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"\b[a-z]{1,3}\d+[a-z0-9]*\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:true|false|null)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def looks_like_youtube_page_config(text: str) -> bool:
    lowered = text.lower()
    marker_count = sum(marker in lowered for marker in YOUTUBE_PAGE_CONFIG_MARKERS)
    escaped_query_count = (
        lowered.count("\\u0026")
        + lowered.count("u0026")
        + lowered.count("\\u003d")
        + lowered.count("u003d")
    )
    player_flag_count = lowered.count("html5_") + lowered.count("web_player_")
    return marker_count >= 2 or escaped_query_count >= 40 or player_flag_count >= 20


def is_probably_transcript_text(text: str) -> bool:
    if looks_like_youtube_page_config(text):
        return False

    words = re.findall(r"[a-zA-Z][a-zA-Z']+", text)
    if len(words) < 5:
        return False

    token_count = max(len(re.findall(r"\S+", text)), 1)
    natural_word_ratio = len(words) / token_count
    return natural_word_ratio >= 0.35


def chunk_text(text: str, target_words: int = 220) -> list[str]:
    if not text.strip():
        return []

    words = text.split()
    chunks: list[str] = []
    for index in range(0, len(words), target_words):
        chunks.append(" ".join(words[index : index + target_words]))
    return chunks


def extract_candidate_topics(text: str, limit: int = 12) -> Counter[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
    filtered = [
        _normalize_topic_token(token)
        for token in tokens
        if token not in STOPWORDS
        and not token.isdigit()
        and len(token) > 2
        and not token.startswith("u00")
        and not re.search(r"\d", token)
    ]
    counts = Counter(filtered)
    return Counter(dict(counts.most_common(limit)))


def _normalize_topic_token(token: str) -> str:
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def build_topic_insights(
    topic_counter: Counter[str],
) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    items = topic_counter.most_common()
    return items[:5], items[5:10]


def detect_niche(topic_counter: Counter[str], joined_text: str) -> str:
    scores = {
        niche: sum(topic_counter.get(keyword, 0) for keyword in keywords)
        for niche, keywords in TOPIC_BUCKETS.items()
    }
    best_niche = max(scores, key=scores.get) if scores else "general"
    if scores.get(best_niche, 0) == 0:
        return "general commentary"
    return best_niche


def infer_tone(text: str) -> str:
    lowered = text.lower()
    if "step by step" in lowered or "how to" in lowered:
        return "educational and instructional"
    if lowered.count("!") >= 6:
        return "high-energy and emphatic"
    if any(word in lowered for word in ("story", "experience", "journey")):
        return "narrative and reflective"
    return "conversational and informative"


def infer_target_audience(text: str, titles: list[str]) -> str:
    joined = f"{text} {' '.join(titles)}".lower()
    if any(term in joined for term in ("beginner", "start", "intro", "explained")):
        return "beginners looking for accessible guidance"
    if any(term in joined for term in ("advanced", "deep dive", "architecture", "strategy")):
        return "intermediate to advanced viewers seeking depth"
    if any(term in joined for term in ("creator", "youtube", "content")):
        return "content creators and digital-first operators"
    return "a broad general-interest audience in the niche"


def infer_content_patterns(titles: list[str]) -> list[str]:
    patterns = []
    lowered_titles = [title.lower() for title in titles]
    if any("how to" in title for title in lowered_titles):
        patterns.append("Tutorial-led packaging appears frequently in recent uploads.")
    if any(char.isdigit() for title in titles for char in title):
        patterns.append("List-style or numbered framing is used to structure ideas.")
    if any("why" in title or "mistake" in title for title in lowered_titles):
        patterns.append("Curiosity and problem/solution framing are common hooks.")
    if not patterns:
        patterns.append("Recent uploads lean on direct, topic-first titling.")
    return patterns


def infer_strengths_and_gaps(
    topic_counter: Counter[str],
    transcript_count: int,
) -> tuple[list[str], list[str]]:
    topics = [topic for topic, _ in topic_counter.most_common(5)]
    strengths = []
    gaps = []

    if topics:
        strengths.append(
            f"Strong repetition around {', '.join(topics[:3])} creates a clear thematic identity."
        )
    if transcript_count >= 5:
        strengths.append(
            "The channel has enough recent transcript coverage to support pattern analysis."
        )
    else:
        gaps.append("Limited transcript coverage reduces confidence in deeper style analysis.")

    if len(topics) <= 3:
        gaps.append("Topic spread is narrow, leaving room for adjacent-topic experimentation.")
    else:
        strengths.append("Topic mix shows range without losing niche coherence.")

    if not gaps:
        gaps.append("Opportunity remains to test fresher hooks and regionalized topic angles.")

    return strengths, gaps
