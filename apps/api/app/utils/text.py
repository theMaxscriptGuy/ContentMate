import re
from collections import Counter

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "being",
    "channel",
    "content",
    "from",
    "have",
    "into",
    "just",
    "like",
    "more",
    "most",
    "really",
    "that",
    "their",
    "them",
    "they",
    "this",
    "video",
    "videos",
    "want",
    "with",
    "would",
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


def clean_transcript_text(raw_text: str) -> str:
    text = raw_text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[[^\]]+\]", "", text)
    return text.strip()


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
        token
        for token in tokens
        if token not in STOPWORDS and not token.isdigit() and len(token) > 2
    ]
    counts = Counter(filtered)
    return Counter(dict(counts.most_common(limit)))


def build_topic_insights(topic_counter: Counter[str]) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
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


def infer_strengths_and_gaps(topic_counter: Counter[str], transcript_count: int) -> tuple[list[str], list[str]]:
    topics = [topic for topic, _ in topic_counter.most_common(5)]
    strengths = []
    gaps = []

    if topics:
        strengths.append(f"Strong repetition around {', '.join(topics[:3])} creates a clear thematic identity.")
    if transcript_count >= 5:
        strengths.append("The channel has enough recent transcript coverage to support pattern analysis.")
    else:
        gaps.append("Limited transcript coverage reduces confidence in deeper style analysis.")

    if len(topics) <= 3:
        gaps.append("Topic spread is narrow, leaving room for adjacent-topic experimentation.")
    else:
        strengths.append("Topic mix shows range without losing niche coherence.")

    if not gaps:
        gaps.append("Opportunity remains to test fresher hooks and regionalized topic angles.")

    return strengths, gaps
