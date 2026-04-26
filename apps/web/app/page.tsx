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
  creator_profile?: {
    creator_archetype: string;
    content_style: string;
    tone_profile: string;
    audience_profile: string;
    packaging_style: string;
    growth_direction: string;
  } | null;
  primary_topics: TopicInsight[];
  secondary_topics: TopicInsight[];
  tone: string;
  target_audience: string;
  content_patterns: string[];
  strengths: string[];
  gaps: string[];
  transcript_coverage_ratio: number;
  analyzed_video_count: number;
  analyzed_transcript_count: number;
};

type VideoIdea = {
  title: string;
  premise: string;
  why_it_fits: string;
  target_viewer: string;
  packaging?: {
    title_options: string[];
    thumbnail_concept: string;
    thumbnail_text: string;
    hook_line: string;
    packaging_rationale: string;
  } | null;
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

type TrendFit = {
  trend: string;
  relevance: string;
  why_it_fits: string;
  execution_angle: string;
};

type CalendarItem = {
  week: number;
  focus: string;
  deliverable: string;
};

type IdeasResult = {
  trend_fit?: TrendFit[];
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
  has_unlimited_analysis: boolean;
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
  unlimited_access: boolean;
  analysis_credit_balance: number;
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
  is_stale?: boolean;
};

type ProgressStage = {
  id: string;
  label: string;
  detail: string;
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
const PIPELINE_STAGES: ProgressStage[] = [
  {
    id: "channel_scan",
    label: "Channel Scan",
    detail: "Reviewing recent content, packaging signals, and creator patterns."
  },
  {
    id: "strategy",
    label: "Strategy Agent",
    detail: "Mapping niche, audience, strengths, and opportunity gaps."
  },
  {
    id: "longform",
    label: "Long-Form Agent",
    detail: "Generating full-length video opportunities with stronger packaging angles."
  },
  {
    id: "shortform",
    label: "Short-Form Agent",
    detail: "Finding quick-hit hooks, Shorts concepts, and repurposing opportunities."
  },
  {
    id: "planner",
    label: "Planner Agent",
    detail: "Sequencing the ideas into a realistic publishing roadmap."
  }
];

const DEMO_SLIDES = [
  {
    src: "/demo-carousel/1.png",
    title: "Start with a channel or video",
    detail: "Pick the analysis mode and paste the YouTube URL you want to work from."
  },
  {
    src: "/demo-carousel/2.png",
    title: "Set the input",
    detail: "Use a channel handle or a specific video URL depending on the planning task."
  },
  {
    src: "/demo-carousel/3.png",
    title: "Watch the agent workflow",
    detail: "Channel scan, strategy, long-form, short-form, and planner agents move the run forward."
  },
  {
    src: "/demo-carousel/4.png",
    title: "Track the progress state",
    detail: "The workflow panel makes it easy to see which specialist is active right now."
  },
  {
    src: "/demo-carousel/5.png",
    title: "Get the strategic read",
    detail: "See the channel context, the representative content item, and the high-level positioning."
  },
  {
    src: "/demo-carousel/6.png",
    title: "Review long-form opportunities",
    detail: "Strengths, gaps, and higher-conviction video ideas are laid out in one board."
  },
  {
    src: "/demo-carousel/7.png",
    title: "Package shorts and thumbnails",
    detail: "Short-form hooks and thumbnail angles come back as a separate creative layer."
  },
  {
    src: "/demo-carousel/8.png",
    title: "Leave with a concrete plan",
    detail: "The final board ends in a practical four-week publishing plan."
  }
] as const;

export default function Home() {
  const [analysisTarget, setAnalysisTarget] = useState<"channel" | "video">("channel");
  const [targetUrl, setTargetUrl] = useState("https://www.youtube.com/@techwithvideep");
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
  const [voucherCode, setVoucherCode] = useState("");
  const [isRedeemingVoucher, setIsRedeemingVoucher] = useState(false);
  const [voucherMessage, setVoucherMessage] = useState<string | null>(null);
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [demoSlideIndex, setDemoSlideIndex] = useState(0);
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const pendingAnalyzeRef = useRef(false);
  const loginWithGoogleRef = useRef<(credential: string) => Promise<void>>();

  const selectedVideo = result?.channel_sync.videos[0];
  const transcript = result?.transcript_sync.transcripts[0];
  const transcriptCoverage = result?.analysis.result.transcript_coverage_ratio ?? 0;
  const analyzedVideoCount = result?.analysis.result.analyzed_video_count ?? 0;
  const analyzedTranscriptCount = result?.analysis.result.analyzed_transcript_count ?? 0;
  const syncedVideoCount = result?.channel_sync.videos.length ?? 0;
  const analyzedVideosLabel =
    analyzedVideoCount === 1 ? "Analyzed Video Set" : "Analyzed Videos";
  const hasDetailedRead = analyzedTranscriptCount > 0;
  const usedMetadataFallback = !hasDetailedRead;
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
    if (!authToken) {
      setHistory([]);
      setUsage(null);
      return;
    }

    void loadUsage(authToken);
    void loadHistory(authToken);
  }, [authToken]);

  useEffect(() => {
    if (!isLoading) {
      return;
    }

    setActiveStageIndex(0);
    const timers = [2200, 6200, 10800, 15000].map((delay, index) =>
      window.setTimeout(() => {
        setActiveStageIndex(index + 1);
      }, delay)
    );

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [isLoading]);

  useEffect(() => {
    if (result || isLoading) {
      return;
    }

    const interval = window.setInterval(() => {
      setDemoSlideIndex((current) => (current + 1) % DEMO_SLIDES.length);
    }, 3200);

    return () => window.clearInterval(interval);
  }, [isLoading, result]);

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
    setVoucherCode("");
    setVoucherMessage(null);
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
      setUser(payload.user);
      window.localStorage.setItem("contentmate_user", JSON.stringify(payload.user));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not load usage");
    }
  }

  async function redeemVoucher() {
    if (!authToken) {
      setError("Sign in with Google to redeem a voucher.");
      return;
    }
    if (!voucherCode.trim()) {
      setError("Enter a voucher code.");
      return;
    }

    setIsRedeemingVoucher(true);
    setVoucherMessage(null);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/redeem-voucher`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ code: voucherCode })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Could not redeem voucher");
      }
      const authPayload = payload as AuthResponse;
      setUser(authPayload.user);
      setUsage(authPayload.usage);
      setVoucherCode("");
      setVoucherMessage("Voucher applied. This account now has unlimited analysis access.");
      window.localStorage.setItem("contentmate_user", JSON.stringify(authPayload.user));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not redeem voucher");
    } finally {
      setIsRedeemingVoucher(false);
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
      if (payload.is_stale) {
        throw new Error(
          "This saved analysis is out of date for the channel's current videos. Run a fresh analysis to see current insights."
        );
      }
      if (!payload.analysis || !payload.ideas) {
        throw new Error("This saved channel does not have analysis and ideas yet.");
      }

      setAnalysisTarget("channel");
      setTargetUrl(payload.channel.channel_url);
      setActiveStageIndex(PIPELINE_STAGES.length);
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
    setActiveStageIndex(0);
    setError(null);
    setResult(null);

    try {
      const isVideoRun = analysisTarget === "video";
      const response = await fetch(
        `${API_BASE_URL}${isVideoRun ? "/pipeline/run-video" : "/pipeline/run"}`,
        {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
          body: JSON.stringify(
            isVideoRun
              ? {
                  video_url: targetUrl,
                  force_transcript_refresh: false,
                  force_ideas_refresh: true
                }
              : {
                  channel_url: targetUrl,
                  force_transcript_refresh: false,
                  force_ideas_refresh: true
                }
          )
        }
      );

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "Pipeline failed");
      }
      setActiveStageIndex(PIPELINE_STAGES.length);
      setResult(payload);
      await loadUsage(token);
      await loadHistory(token);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Something went wrong");
      setActiveStageIndex(0);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="topBar">
        <div className="brandBlock">
          <div className="brandIdentity">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="ContentMatePro logo" src="/contentmatepro-logo.png" />
            <div>
              <strong>ContentMatePro</strong>
              <small>Capstone project by Videep Mishraa</small>
              <span>Creator strategy workspace</span>
            </div>
          </div>
        </div>
        <div className="topActions">
          <div className="contactLinks compact">
            <a href="mailto:create@contentmatepro.com">create@contentmatepro.com</a>
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
        </div>
      </header>

      <section className="hero">
        <div className="eyebrow">ContentMatePro Studio</div>
        <h1>Turn a YouTube channel or video into a content strategy board.</h1>
        <p>
          Paste a YouTube channel or specific video URL. ContentMatePro runs an
          agent workflow to turn it into analysis, strategy, and a practical plan.
        </p>

        <div className="filterRow">
          <label className="filterOption">
            <input
              checked={analysisTarget === "channel"}
              onChange={() => {
                setAnalysisTarget("channel");
                setTargetUrl("https://www.youtube.com/@techwithvideep");
              }}
              type="radio"
            />
            <span>Analyze Channel</span>
          </label>
          <label className="filterOption">
            <input
              checked={analysisTarget === "video"}
              onChange={() => {
                setAnalysisTarget("video");
                setTargetUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
              }}
              type="radio"
            />
            <span>Analyze Specific Video</span>
          </label>
        </div>
        <form className="commandBar" onSubmit={runPipeline}>
          <input
            aria-label={analysisTarget === "channel" ? "YouTube channel URL" : "YouTube video URL"}
            onChange={(event) => setTargetUrl(event.target.value)}
            placeholder={
              analysisTarget === "channel"
                ? "https://www.youtube.com/@channel"
                : "https://www.youtube.com/watch?v=VIDEO_ID"
            }
            type="url"
            value={targetUrl}
          />
          <button disabled={isLoading || isAuthLoading} type="submit">
            {isLoading
              ? "Analyzing..."
              : analysisTarget === "channel"
                ? "Analyze Channel"
                : "Analyze Video"}
          </button>
        </form>
        {analysisTarget === "channel" ? (
          <p className="historyEmpty">
            Channel analysis automatically reviews the latest 15 uploaded videos and uses titles,
            descriptions, and transcripts when available.
          </p>
        ) : (
          <p className="historyEmpty">
            Specific video analysis focuses the agent workflow on one chosen video and
            builds strategy ideas from that source.
          </p>
        )}
        {isLoginRequired && !user ? (
          <div className="loginPrompt">
            <strong>Google sign-in required</strong>
            <span>Use the Google button above. Analysis will start after login.</span>
          </div>
        ) : null}
        {error ? <div className="errorCard">{error}</div> : null}
      </section>

      {user ? (
        <section className="historyPanel">
          {usage?.unlimited_access ? (
            <div className="accessRow">
              <div className="accessMeta">
                <p className="sectionLabel">Access</p>
                <h2>Unlimited access enabled</h2>
              </div>
              <p className="historyEmpty">
                This account can run analyses without the daily counter being applied.
              </p>
            </div>
          ) : (
            <>
              <div className="accessRow">
                <div className="accessMeta">
                  <p className="sectionLabel">Access</p>
                  <h2>Access and credits</h2>
                </div>
                <p className="historyEmpty">
                  You get <strong>{usage?.daily_analysis_limit ?? 0} free analyses per day</strong>.
                  After that, each additional analysis uses <strong>1 credit</strong>. Current balance:{" "}
                  <strong>{usage?.analysis_credit_balance ?? 0}</strong>.
                </p>
                <div className="accessAction">
                  <input
                    aria-label="Voucher code"
                    onChange={(event) => setVoucherCode(event.target.value)}
                    placeholder="Enter voucher code"
                    type="text"
                    value={voucherCode}
                  />
                  <button
                    disabled={isRedeemingVoucher || !voucherCode.trim()}
                    onClick={redeemVoucher}
                    type="button"
                  >
                    {isRedeemingVoucher ? "Applying..." : "Apply Code"}
                  </button>
                </div>
              </div>
              {voucherMessage ? <p className="historyEmpty">{voucherMessage}</p> : null}
            </>
          )}
        </section>
      ) : null}

      <section className="statusGrid">
        <StatusCard
          label="Channel Scan"
          state={stageState(0, isLoading, result, activeStageIndex)}
        />
        <StatusCard
          label="Strategy Agent"
          state={stageState(1, isLoading, result, activeStageIndex)}
        />
        <StatusCard
          label="Agent Workflow"
          state={stageState(3, isLoading, result, activeStageIndex)}
        />
        <StatusCard
          label="Free Runs"
          state={
            usage
              ? usage.unlimited_access
                ? "Unlimited"
                : `${usage.analyses_remaining_today}/${usage.daily_analysis_limit} left today`
              : "Login required"
          }
        />
        <StatusCard
          label="Credits"
          state={usage ? `${usage.analysis_credit_balance} available` : "Login required"}
        />
      </section>

      {(isLoading || result) && (
        <section className="progressPanel">
          <div className="progressHeader">
            <p className="sectionLabel">Agent Workflow</p>
            <strong>{isLoading ? "In Progress" : "Complete"}</strong>
          </div>
          <div className="progressRail">
            {PIPELINE_STAGES.map((stage, index) => {
              const state = progressStageState(index, activeStageIndex, isLoading, Boolean(result));
              return (
                <div className={`progressStep ${state}`} key={stage.id}>
                  <span>{index + 1}</span>
                  <div>
                    <strong>{stage.label}</strong>
                    <small>{stage.detail}</small>
                  </div>
                </div>
              );
            })}
          </div>
          {isLoading ? (
            <p className="progressNote">
              Each specialist agent works on a different part of the strategy, so some runs can
              take a little longer.
            </p>
          ) : null}
        </section>
      )}

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
          <section
            className={`panel widePanel analysisSourcePanel ${usedMetadataFallback ? "fallback" : "transcript"}`}
          >
            <p className="sectionLabel">Analysis Complete</p>
            <h2>
              {usedMetadataFallback
                ? "Overall channel analysis complete"
                : "Detailed per-video analysis complete"}
            </h2>
            <p className="muted">
              {usedMetadataFallback
                ? "The system completed a full channel-level strategy read across the selected content set."
                : "The system completed a deeper multi-video strategy read across the selected content set."}
            </p>
            <div className="metricRow">
              <span>{result.analysis.result.analyzed_video_count} videos analyzed</span>
              <span>{analyzedTranscriptCount} detailed reads completed</span>
              <span>{result.transcript_sync.failed_transcripts} items skipped</span>
            </div>
          </section>

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
              <p className="sectionLabel">
                {analyzedVideoCount > 0 ? analyzedVideosLabel : "Representative Video"}
              </p>
              <h2>{selectedVideo.title}</h2>
              <p className="muted">
                {analyzedVideoCount > 1
                  ? `${analyzedVideoCount} videos contributed to this analysis. This card shows the most recent representative video from that set.`
                  : analyzedVideoCount === 1
                    ? "This run analyzed one video for the final result."
                    : "This card shows the most recent synced video from the channel surface for context."}
              </p>
              <div className="metricRow">
                <span>
                  {analyzedVideoCount > 0
                    ? `${analyzedVideoCount} analyzed`
                    : `${syncedVideoCount} synced`}
                </span>
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

          {result.analysis.result.creator_profile ? (
            <section className="panel widePanel">
              <p className="sectionLabel">Creator Profile</p>
              <h2>{result.analysis.result.creator_profile.creator_archetype}</h2>
              <p className="muted">{result.analysis.result.creator_profile.content_style}</p>
              <div className="ideaGrid">
                <article className="compactItem">
                  <strong>Tone</strong>
                  <span>{result.analysis.result.creator_profile.tone_profile}</span>
                </article>
                <article className="compactItem">
                  <strong>Audience Fit</strong>
                  <span>{result.analysis.result.creator_profile.audience_profile}</span>
                </article>
                <article className="compactItem">
                  <strong>Packaging Style</strong>
                  <span>{result.analysis.result.creator_profile.packaging_style}</span>
                </article>
                <article className="compactItem">
                  <strong>Growth Direction</strong>
                  <span>{result.analysis.result.creator_profile.growth_direction}</span>
                </article>
              </div>
            </section>
          ) : null}

          {result.ideas.result.trend_fit && result.ideas.result.trend_fit.length > 0 ? (
            <section className="panel widePanel">
              <p className="sectionLabel">Trend Fit</p>
              <h2>What is timely for this channel right now</h2>
              <div className="ideaGrid">
                {result.ideas.result.trend_fit.map((item) => (
                  <article className="ideaCard" key={`${item.trend}-${item.execution_angle}`}>
                    <div className="ideaHeader">
                      <strong>{item.trend}</strong>
                      <span className="chip">{item.relevance}</span>
                    </div>
                    <p>{item.why_it_fits}</p>
                    <small>{item.execution_angle}</small>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

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
                  {idea.packaging ? (
                    <div className="packagingBlock">
                      <div className="packagingSection">
                        <span className="sectionLabel">Title Options</span>
                        <ul className="packagingList">
                          {idea.packaging.title_options.map((titleOption) => (
                            <li key={titleOption}>{titleOption}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="packagingGrid">
                        <article className="packagingItem">
                          <span className="sectionLabel">Hook</span>
                          <strong>{idea.packaging.hook_line}</strong>
                        </article>
                        <article className="packagingItem">
                          <span className="sectionLabel">Thumbnail</span>
                          <strong>{idea.packaging.thumbnail_concept}</strong>
                          <small>{idea.packaging.thumbnail_text}</small>
                        </article>
                      </div>
                      <p className="packagingRationale">{idea.packaging.packaging_rationale}</p>
                    </div>
                  ) : null}
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
      ) : !user ? (
        <section className="demoPanel">
          <div className="demoHeader">
            <div>
              <p className="sectionLabel">Product Walkthrough</p>
              <h2>See the board before you run it.</h2>
            </div>
            <p>
              A quick guided preview of the full ContentMatePro workflow, from input to
              strategy to final publishing plan.
            </p>
          </div>
          <div className="demoCarousel">
            <div className="demoFrame">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                alt={DEMO_SLIDES[demoSlideIndex].title}
                className="demoImage"
                src={DEMO_SLIDES[demoSlideIndex].src}
              />
            </div>
            <div className="demoMeta">
              <span>
                {String(demoSlideIndex + 1).padStart(2, "0")} / {String(DEMO_SLIDES.length).padStart(2, "0")}
              </span>
              <strong>{DEMO_SLIDES[demoSlideIndex].title}</strong>
              <p>{DEMO_SLIDES[demoSlideIndex].detail}</p>
              <div className="demoDots">
                {DEMO_SLIDES.map((slide, index) => (
                  <button
                    aria-label={`Show demo slide ${index + 1}: ${slide.title}`}
                    className={index === demoSlideIndex ? "active" : ""}
                    key={slide.src}
                    onClick={() => setDemoSlideIndex(index)}
                    type="button"
                  />
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      <footer className="contactPanel">
        <div>
          <p className="sectionLabel">Contact</p>
          <h2>Videep Mishraa</h2>
          <span>Capstone project</span>
        </div>
        <div className="contactLinks">
          <a href="mailto:create@contentmatepro.com">create@contentmatepro.com</a>
          <a href="https://www.instagram.com/contentmatepro/" rel="noreferrer" target="_blank">
            Instagram
          </a>
          <a href="https://www.linkedin.com/in/videep/" rel="noreferrer" target="_blank">
            LinkedIn
          </a>
          <a href="/privacy">Privacy</a>
          <a href="/terms">Terms</a>
        </div>
      </footer>
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

function stageState(
  index: number,
  isLoading: boolean,
  result: PipelineResponse | null,
  activeStageIndex: number
) {
  if (result) {
    return "Complete";
  }
  if (!isLoading) {
    return "Waiting";
  }
  if (activeStageIndex === index) {
    return "Working";
  }
  if (activeStageIndex > index) {
    return "Complete";
  }
  return "Queued";
}

function progressStageState(
  index: number,
  activeStageIndex: number,
  isLoading: boolean,
  hasResult: boolean
) {
  if (hasResult) {
    return "complete";
  }
  if (!isLoading) {
    return "queued";
  }
  if (activeStageIndex === index) {
    return "active";
  }
  if (activeStageIndex > index) {
    return "complete";
  }
  return "queued";
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
