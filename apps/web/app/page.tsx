"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type TopicInsight = {
  topic: string;
  mentions: number;
};

type ChannelSummary = {
  id: string;
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

type AuthUser = {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
};

type AuthResponse = {
  access_token: string;
  user: AuthUser;
  usage: UsageStatus;
};

type UsageStatus = {
  daily_analysis_limit: number;
  analyses_used_today: number;
  analyses_remaining_today: number;
  resets_at: string;
};

type HistoryItem = {
  channel: ChannelSummary;
  analyzed_at: string | null;
  idea_count: number;
  latest_video_title: string | null;
};

type SavedChannelResponse = {
  channel: ChannelSummary;
  videos: VideoSummary[];
  analysis: PipelineResponse["analysis"] | null;
  ideas: PipelineResponse["ideas"] | null;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              theme: "outline" | "filled_blue" | "filled_black";
              size: "large" | "medium" | "small";
              width?: number;
            }
          ) => void;
        };
      };
    };
  }
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function Home() {
  const [channelUrl, setChannelUrl] = useState("https://www.youtube.com/@techwithvideep");
  const [result, setResult] = useState<PipelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [isLoginRequired, setIsLoginRequired] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [usage, setUsage] = useState<UsageStatus | null>(null);
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const pendingAnalyzeRef = useRef(false);
  const loginWithGoogleRef = useRef<(credential: string) => Promise<void>>();

  const selectedVideo = result?.channel_sync.videos[0];
  const transcript = result?.transcript_sync.transcripts[0];
  const topicChips = useMemo(() => {
    const topics = result?.analysis.result.primary_topics ?? [];
    return topics.slice(0, 6);
  }, [result]);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("contentmate_token");
    const savedUser = window.localStorage.getItem("contentmate_user");
    if (savedToken) {
      setAuthToken(savedToken);
    }
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        window.localStorage.removeItem("contentmate_user");
      }
    }
  }, []);

  useEffect(() => {
    if (!authToken || !user) {
      setHistory([]);
      setUsage(null);
      return;
    }

    void loadUsage(authToken);
    void loadHistory(authToken);
  }, [authToken, user]);

  async function loginWithGoogle(credential: string) {
    setIsAuthLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Google login failed");
      }

      const authPayload = payload as AuthResponse;
      window.localStorage.setItem("contentmate_token", authPayload.access_token);
      window.localStorage.setItem("contentmate_user", JSON.stringify(authPayload.user));
      setAuthToken(authPayload.access_token);
      setUser(authPayload.user);
      setUsage(authPayload.usage);
      setIsLoginRequired(false);
      await loadHistory(authPayload.access_token);
      if (pendingAnalyzeRef.current) {
        pendingAnalyzeRef.current = false;
        await runPipelineWithToken(authPayload.access_token);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Google login failed");
    } finally {
      setIsAuthLoading(false);
    }
  }

  loginWithGoogleRef.current = loginWithGoogle;

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !googleButtonRef.current || user) {
      return;
    }

    const renderGoogleButton = () => {
      if (!window.google || !googleButtonRef.current) {
        return;
      }

      googleButtonRef.current.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          if (!response.credential) {
            setError("Google did not return a login credential.");
            return;
          }
          await loginWithGoogleRef.current?.(response.credential);
        }
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        width: 260
      });
    };

    if (window.google) {
      renderGoogleButton();
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[src="https://accounts.google.com/gsi/client"]'
    );
    if (existingScript) {
      existingScript.addEventListener("load", renderGoogleButton, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = renderGoogleButton;
    document.head.appendChild(script);
  }, [user]);

  function signOut() {
    window.localStorage.removeItem("contentmate_token");
    window.localStorage.removeItem("contentmate_user");
    setAuthToken(null);
    setUser(null);
    setResult(null);
    setHistory([]);
    setUsage(null);
  }

  async function loadUsage(token: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Could not load usage");
      }
      setUsage(payload.usage);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not load usage");
    }
  }

  async function loadHistory(token: string) {
    setIsHistoryLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/me/channels`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Could not load history");
      }
      setHistory(payload.channels ?? []);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not load history");
    } finally {
      setIsHistoryLoading(false);
    }
  }

  async function openSavedChannel(channelId: string) {
    if (!authToken) {
      setError("Sign in with Google to open saved analyses.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/me/channels/${channelId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const payload = (await response.json()) as SavedChannelResponse & { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail ?? "Could not open saved analysis");
      }
      if (!payload.analysis || !payload.ideas) {
        throw new Error("This saved channel does not have analysis and ideas yet.");
      }

      setChannelUrl(payload.channel.channel_url);
      setResult({
        job_id: `saved-${channelId}`,
        channel_sync: {
          channel: payload.channel,
          videos: payload.videos
        },
        transcript_sync: {
          fetched_transcripts: 0,
          failed_transcripts: 0,
          transcripts: payload.videos.map((video) => ({
            status: video.transcript_status,
            language: null,
            source: null,
            chunk_count: null,
            error_message: null
          }))
        },
        analysis: payload.analysis,
        ideas: payload.ideas
      });
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not open saved analysis");
    } finally {
      setIsLoading(false);
    }
  }

  async function runPipeline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!authToken) {
      pendingAnalyzeRef.current = true;
      setIsLoginRequired(true);
      setError("Sign in with Google to analyze this channel.");
      return;
    }

    await runPipelineWithToken(authToken);
  }

  async function runPipelineWithToken(token: string) {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/pipeline/run`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
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
      await loadUsage(token);
      await loadHistory(token);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="topBar">
        <div>
          <strong>ContentMate</strong>
          <span>Creator strategy workspace</span>
        </div>
        <div className="authDock">
          {user ? (
            <div className="userBadge">
              {user.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img alt="" src={user.avatar_url} />
              ) : null}
              <span>{user.name ?? user.email}</span>
              <button onClick={signOut} type="button">
                Sign out
              </button>
            </div>
          ) : (
            <>
              <div ref={googleButtonRef} />
              {!GOOGLE_CLIENT_ID ? (
                <span className="authHint">Google login is not configured.</span>
              ) : null}
              {isAuthLoading ? <span className="authHint">Signing in...</span> : null}
            </>
          )}
        </div>
      </header>

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
          <button disabled={isLoading || isAuthLoading} type="submit">
            {isLoading ? "Analyzing..." : "Analyze Channel"}
          </button>
        </form>
        {isLoginRequired && !user ? (
          <div className="loginPrompt">
            <strong>Google sign-in required</strong>
            <span>Use the Google button above. Analysis will start after login.</span>
          </div>
        ) : null}
        {error ? <div className="errorCard">{error}</div> : null}
      </section>

      <section className="statusGrid">
        <StatusCard label="Ingest" state={result ? "Complete" : "Waiting"} />
        <StatusCard label="Transcript" state={transcript?.status ?? "Waiting"} />
        <StatusCard label="Analysis" state={result?.analysis.model_name ?? "Waiting"} />
        <StatusCard
          label="Daily Limit"
          state={
            usage
              ? `${usage.analyses_remaining_today}/${usage.daily_analysis_limit} left`
              : "Login required"
          }
        />
      </section>

      {user ? (
        <section className="historyPanel">
          <div className="historyHeader">
            <div>
              <p className="sectionLabel">My Channels</p>
              <h2>Saved analyses</h2>
            </div>
            <button
              disabled={!authToken || isHistoryLoading}
              onClick={() => authToken && loadHistory(authToken)}
              type="button"
            >
              {isHistoryLoading ? "Loading" : "Refresh"}
            </button>
          </div>
          {history.length > 0 ? (
            <div className="historyList">
              {history.map((item) => (
                <button
                  className="historyItem"
                  key={item.channel.id}
                  onClick={() => openSavedChannel(item.channel.id)}
                  type="button"
                >
                  {item.channel.thumbnail_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img alt="" src={item.channel.thumbnail_url} />
                  ) : null}
                  <span>
                    <strong>{item.channel.title}</strong>
                    <small>
                      {item.idea_count} ideas
                      {item.latest_video_title ? ` · ${item.latest_video_title}` : ""}
                    </small>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="historyEmpty">
              {isHistoryLoading ? "Loading saved channels..." : "Analyzed channels will appear here."}
            </p>
          )}
        </section>
      ) : null}

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
