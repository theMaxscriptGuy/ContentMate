from dataclasses import dataclass
from xml.etree import ElementTree

import httpx

from app.core.config import get_settings

settings = get_settings()


class TrendProviderError(Exception):
    pass


@dataclass(slots=True)
class TrendSnapshot:
    geo: str
    items: list[str]
    source: str


class TrendClient:
    def __init__(self) -> None:
        self.timeout = settings.trend_request_timeout_seconds
        self.max_items = settings.trend_max_items

    def fetch_trending_searches(self, geo: str) -> TrendSnapshot:
        geo = (geo or settings.trend_default_geo).upper()
        errors: list[str] = []

        for source_name, url in self._candidate_urls(geo):
            try:
                response = httpx.get(
                    url,
                    timeout=self.timeout,
                    headers={"User-Agent": "ContentMatePro/1.1"},
                    follow_redirects=True,
                )
                response.raise_for_status()
                items = self._parse_rss_titles(response.text)
                if items:
                    return TrendSnapshot(
                        geo=geo,
                        items=items[: self.max_items],
                        source=source_name,
                    )
                errors.append(f"{source_name}: empty trend response")
            except Exception as exc:
                errors.append(f"{source_name}: {exc}")

        raise TrendProviderError(" | ".join(errors) or "No trend data available.")

    @staticmethod
    def _candidate_urls(geo: str) -> list[tuple[str, str]]:
        return [
            ("google_trends_rss", f"https://trends.google.com/trending/rss?geo={geo}"),
            (
                "google_trends_daily_rss",
                f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}",
            ),
        ]

    @staticmethod
    def _parse_rss_titles(content: str) -> list[str]:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise TrendProviderError("Trend feed returned unreadable XML.") from exc

        titles: list[str] = []
        for item in root.findall("./channel/item"):
            title = item.findtext("title")
            if title:
                normalized = " ".join(title.split())
                if normalized:
                    titles.append(normalized)
        return titles
