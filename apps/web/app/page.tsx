"use client";

import { FormEvent, useMemo, useState } from "react";

type TopicInsight = {
  topic: string;
  mentions: number;
};

type ChannelSummary = {
  title: string;
  subscriber_count: number | null;
  thumbnail_url: string | null;
  channel_url: string;
};

type VideoSummary = {
  title: string;
  youtube_video_id: string;
  duration_seconds: number | null;
  view_count: number | null;
  thumbnail_url: string | null;
  transcript_status: string;
};

type AnalysisResult = {
  niche: string;
  primary_topics: TopicInsight[];
  secondary_topics: TopicInsight[];
  tone: string;
  target_audience: string;
  content_patterns: string[];
  strengths: string[];
  gaps: string[];
};

type VideoIdea = {
  title: string;
  premise: string;
  why_it_fits: string;
  target_viewer: string;
};

type ShortIdea = {
  hook: string;
  concept: string;
  source_moment: string;
};

type TitleHook = {
  title: string;
  angle: string;
};

type ThumbnailAngle = {
  concept: string;
  visual_elements: string[];
  text_overlay: string;
};

type CalendarItem = {
  week: number;
  focus: string;
  deliverable: string;
};

type IdeasResult = {
  video_ideas: VideoIdea[];
  shorts_ideas: ShortIdea[];
  title_hooks: TitleHook[];
  thumbnail_angles: ThumbnailAngle[];
  content_calendar: CalendarItem[];
};

type PipelineResponse = {
  job_id: string;
  channel_sync: {
    channel: ChannelSummary;
    videos: VideoSummary[];
  };
  transcript_sync: {
    fetched_transcripts: number;
    failed_transcripts: number;
    transcripts: Array<{
      status: string;
      language: string | null;
      source: string | null;
      chunk_count: number | null;
      error_message: string | null;
    }>;
  };
  analysis: {
    model_name: string | null;
    result: AnalysisResult;
  };
  ideas: {
    model_name: string | null;
    result: IdeasResult;
  };
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export default function Home() {
  const [channelUrl, setChannelUrl] = useState("https://www.youtube.com/@techwithvideep");
  const [result, setResult] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const selectedVideo = result?.channel_sync.videos[0];
  const transcript = result?.transcript_sync.transcripts[0];
  const topicChips = useMemo(() => {
    const topics = result?.analysis.result.primary_topics ?? [];
    return topics.slice(0, 6);
  }, [result]);

  async function runPipeline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/pipeline/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel_url: channelUrl,
          force_transcript_refresh: false,
          force_ideas_refresh: true
        })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Pipeline failed");
      }
      setResult(payload);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">ContentMate Studio</div>
        <h1>Turn a YouTube channel into a content strategy board.</h1>
        <p>
          Paste a channel URL. ContentMate pulls a long-form video, gets the transcript,
          analyzes the creator style, and generates production-ready ideas.
        </p>

        <form className="commandBar" onSubmit={runPipeline}>
          <input
            aria-label="YouTube channel URL"
            onChange={(event) => setChannelUrl(event.target.value)}
            placeholder="https://www.youtube.com/@channel"
            type="url"
            value={channelUrl}
          />
          <button disabled={isLoading} type="submit">
            {isLoading ? "Analyzing..." : "Analyze Channel"}
          </button>
        </form>
        {error ? <div className="errorCard">{error}</div> : null}
      </section>

      <section className="statusGrid">
        <StatusCard label="Ingest" state={result ? "Complete" : "Waiting"} />
        <StatusCard label="Transcript" state={transcript?.status ?? "Waiting"} />
        <StatusCard label="Analysis" state={result?.analysis.model_name ?? "Waiting"} />
        <StatusCard label="Ideas" state={result?.ideas.model_name ?? "Waiting"} />
      </section>

      {result ? (
        <div className="dashboard">
          <section className="panel channelPanel">
            <div>
              <p className="sectionLabel">Channel</p>
              <h2>{result.channel_sync.channel.title}</h2>
              <p>
                {formatNumber(result.channel_sync.channel.subscriber_count)} subscribers
              </p>
            </div>
            {result.channel_sync.channel.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt=""
                className="avatar"
                src={result.channel_sync.channel.thumbnail_url}
              />
            ) : null}
          </section>

          {selectedVideo ? (
            <section className="panel videoPanel">
              <p className="sectionLabel">Analyzed Video</p>
              <h2>{selectedVideo.title}</h2>
              <div className="metricRow">
                <span>{formatDuration(selectedVideo.duration_seconds)}</span>
                <span>{formatNumber(selectedVideo.view_count)} views</span>
                <span>{selectedVideo.transcript_status}</span>
              </div>
            </section>
          ) : null}

          <section className="panel widePanel">
            <p className="sectionLabel">Strategic Read</p>
            <h2>{result.analysis.result.niche}</h2>
            <p className="muted">{result.analysis.result.target_audience}</p>
            <div className="chipRow">
              {topicChips.map((topic) => (
                <span className="chip" key={topic.topic}>
                  {topic.topic} · {topic.mentions}
                </span>
              ))}
            </div>
          </section>

          <ListPanel
            eyebrow="Strengths"
            items={result.analysis.result.strengths}
            title="What is already working"
          />
          <ListPanel
            eyebrow="Gaps"
            items={result.analysis.result.gaps}
            title="Where to improve next"
          />

          <section className="panel widePanel">
            <p className="sectionLabel">Video Ideas</p>
            <div className="ideaGrid">
              {result.ideas.result.video_ideas.map((idea) => (
                <article className="ideaCard" key={idea.title}>
                  <h3>{idea.title}</h3>
                  <p>{idea.premise}</p>
                  <small>{idea.why_it_fits}</small>
                </article>
              ))}
            </div>
          </section>

          <section className="panel">
            <p className="sectionLabel">Shorts</p>
            {result.ideas.result.shorts_ideas.map((idea) => (
              <article className="compactItem" key={idea.hook}>
                <strong>{idea.hook}</strong>
                <span>{idea.concept}</span>
              </article>
            ))}
          </section>

          <section className="panel">
            <p className="sectionLabel">Thumbnail Angles</p>
            {result.ideas.result.thumbnail_angles.map((angle) => (
              <article className="compactItem" key={angle.concept}>
                <strong>{angle.concept}</strong>
                <span>{angle.text_overlay}</span>
              </article>
            ))}
          </section>

          <section className="panel widePanel">
            <p className="sectionLabel">4 Week Plan</p>
            <div className="calendarGrid">
              {result.ideas.result.content_calendar.map((item) => (
                <article className="calendarItem" key={`${item.week}-${item.focus}`}>
                  <span>Week {item.week}</span>
                  <strong>{item.focus}</strong>
                  <p>{item.deliverable}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
      ) : (
        <section className="emptyState">
          <div className="orbit" />
          <h2>Ready when you are.</h2>
          <p>The first run can take a little while because it fetches video data, transcript, analysis, and ideas.</p>
        </section>
      )}
    </main>
  );
}

function StatusCard({ label, state }: { label: string; state: string }) {
  return (
    <div className="statusCard">
      <span>{label}</span>
      <strong>{state}</strong>
    </div>
  );
}

function ListPanel({
  eyebrow,
  items,
  title
}: {
  eyebrow: string;
  items: string[];
  title: string;
}) {
  return (
    <section className="panel">
      <p className="sectionLabel">{eyebrow}</p>
      <h2>{title}</h2>
      <ul className="bulletList">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function formatNumber(value: number | null) {
  if (value === null) {
    return "Unknown";
  }
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

function formatDuration(value: number | null) {
  if (value === null) {
    return "Unknown duration";
  }
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}m ${seconds}s`;
}
