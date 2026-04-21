from dataclasses import dataclass
import json
import re
from xml.etree.ElementTree import ParseError
from xml.etree import ElementTree

try:
    from youtube_transcript_api import (
        NoTranscriptFound,
        YouTubeTranscriptApi,
    )
    _TRANSCRIPT_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local env setup
    NoTranscriptFound = Exception
    YouTubeTranscriptApi = None
    _TRANSCRIPT_IMPORT_ERROR = exc

try:
    import yt_dlp
    from yt_dlp.networking.common import Request as YtDlpRequest
    _YTDLP_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local env setup
    yt_dlp = None
    YtDlpRequest = None
    _YTDLP_IMPORT_ERROR = exc


class TranscriptProviderError(Exception):
    pass


@dataclass(slots=True)
class TranscriptPayload:
    language: str | None
    source: str
    raw_text: str


class TranscriptClient:
    def fetch_transcript(self, youtube_video_id: str) -> TranscriptPayload:
        errors: list[str] = []

        if YouTubeTranscriptApi is not None:
            try:
                return self._fetch_with_youtube_transcript_api(youtube_video_id)
            except TranscriptProviderError as exc:
                errors.append(str(exc))
        elif _TRANSCRIPT_IMPORT_ERROR is not None:
            errors.append(
                "youtube-transcript-api is unavailable. Run `pip install -e .` in apps/api."
            )

        if yt_dlp is not None:
            try:
                return self._fetch_with_ytdlp(youtube_video_id)
            except TranscriptProviderError as exc:
                errors.append(str(exc))
        elif _YTDLP_IMPORT_ERROR is not None:
            errors.append("yt-dlp is unavailable. Run `pip install -e .` in apps/api.")

        raise TranscriptProviderError(" | ".join(dict.fromkeys(errors)) or "No transcript found for this video.")

    def _fetch_with_youtube_transcript_api(self, youtube_video_id: str) -> TranscriptPayload:
        if YouTubeTranscriptApi is None:
            raise TranscriptProviderError(
                "Transcript dependencies are missing. Run `pip install -e .` in apps/api."
            ) from _TRANSCRIPT_IMPORT_ERROR
        try:
            transcript = YouTubeTranscriptApi().fetch(
                youtube_video_id,
                languages=["en", "en-US", "en-GB", "hi"],
            )
        except (NoTranscriptFound, ParseError) as exc:
            raise TranscriptProviderError("No transcript found for this video.") from exc
        except Exception as exc:
            raise TranscriptProviderError("Transcript provider returned an unreadable response.") from exc

        parts = []
        snippets = getattr(transcript, "snippets", transcript)
        for item in snippets:
            text = item["text"] if isinstance(item, dict) else getattr(item, "text", "")
            text = text.strip()
            if text:
                parts.append(text)
        raw_text = " ".join(parts)
        if not raw_text:
            raise TranscriptProviderError("Transcript was empty after fetch.")

        source = "generated" if getattr(transcript, "is_generated", False) else "manual"
        return TranscriptPayload(
            language=getattr(transcript, "language_code", None),
            source=source,
            raw_text=raw_text,
        )

    def _fetch_with_ytdlp(self, youtube_video_id: str) -> TranscriptPayload:
        if yt_dlp is None:
            raise TranscriptProviderError(
                "yt-dlp is unavailable. Run `pip install -e .` in apps/api."
            ) from _YTDLP_IMPORT_ERROR

        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
        }
        video_url = f"https://www.youtube.com/watch?v={youtube_video_id}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
        except Exception as exc:
            raise TranscriptProviderError("yt-dlp could not inspect transcript tracks for this video.") from exc

        track, language, source = self._choose_ytdlp_track(info)
        if track is None:
            raise TranscriptProviderError("No transcript found for this video.")

        subtitle_text = self._download_subtitle_text(ydl, track)
        raw_text = self._parse_subtitle_text(subtitle_text, track.get("ext"))
        if not raw_text:
            raise TranscriptProviderError("yt-dlp found a subtitle track, but it was empty.")

        return TranscriptPayload(language=language, source=source, raw_text=raw_text)

    @staticmethod
    def _choose_ytdlp_track(info: dict) -> tuple[dict | None, str | None, str]:
        preferred_languages = ["en", "en-US", "en-GB", "hi"]

        for bucket_name, source in (("subtitles", "manual_ytdlp"), ("automatic_captions", "generated_ytdlp")):
            tracks = info.get(bucket_name) or {}
            for language in preferred_languages + sorted(tracks.keys()):
                entries = tracks.get(language)
                if not entries:
                    continue
                selected = TranscriptClient._pick_best_track(entries)
                if selected is not None:
                    return selected, language, source
        return None, None, ""

    @staticmethod
    def _pick_best_track(entries: list[dict]) -> dict | None:
        preferred_exts = ["json3", "vtt", "srv3", "ttml", "srv1"]
        for ext in preferred_exts:
            for entry in entries:
                if entry.get("ext") == ext and entry.get("url"):
                    return entry
        for entry in entries:
            if entry.get("url"):
                return entry
        return None

    @staticmethod
    def _download_subtitle_text(ydl, track: dict) -> str:
        try:
            request = YtDlpRequest(
                track["url"],
                headers=track.get("http_headers") or {},
                extensions={"timeout": 20.0},
            )
            with ydl.urlopen(request) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            raise TranscriptProviderError("Failed to download subtitle track from yt-dlp.") from exc

    @staticmethod
    def _parse_subtitle_text(content: str, extension: str | None) -> str:
        if not content.strip():
            return ""

        if extension == "json3":
            return TranscriptClient._parse_json3(content)
        if extension in {"vtt", "srv3", "srv1"}:
            return TranscriptClient._parse_vtt_like(content)
        if extension == "ttml":
            return TranscriptClient._parse_ttml(content)

        parsed = TranscriptClient._parse_json3(content)
        if parsed:
            return parsed
        parsed = TranscriptClient._parse_vtt_like(content)
        if parsed:
            return parsed
        return TranscriptClient._parse_ttml(content)

    @staticmethod
    def _parse_json3(content: str) -> str:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return ""

        parts: list[str] = []
        for event in payload.get("events", []):
            for segment in event.get("segs", []):
                text = (segment.get("utf8") or "").strip()
                if text:
                    parts.append(text)
        return TranscriptClient._normalize_joined_text(parts)

    @staticmethod
    def _parse_vtt_like(content: str) -> str:
        lines = []
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line == "WEBVTT":
                continue
            if "-->" in line:
                continue
            if re.fullmatch(r"\d+", line):
                continue
            if line.startswith(("Kind:", "Language:")):
                continue
            lines.append(line)
        return TranscriptClient._normalize_joined_text(lines)

    @staticmethod
    def _parse_ttml(content: str) -> str:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return ""

        parts = []
        for element in root.iter():
            text = "".join(element.itertext()).strip()
            if text:
                parts.append(text)
        return TranscriptClient._normalize_joined_text(parts)

    @staticmethod
    def _normalize_joined_text(parts: list[str]) -> str:
        text = " ".join(parts)
        text = re.sub(r"\s+", " ", text).strip()
        return text
