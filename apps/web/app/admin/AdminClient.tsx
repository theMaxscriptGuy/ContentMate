"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type AdminActivityResponse = {
  summary: {
    total_users: number;
    total_channel_analyses: number;
    total_channels: number;
  };
  activity: Array<{
    analysis_id: string;
    analyzed_at: string;
    source_kind: string;
    analyzed_video_count: number;
    analyzed_transcript_count: number;
    model_name: string | null;
    user: {
      id: string;
      email: string;
      name: string | null;
    };
    channel: {
      id: string;
      title: string;
      channel_url: string;
      subscriber_count: number | null;
    };
  }>;
};

export default function AdminClient() {
  const [data, setData] = useState<AdminActivityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = window.localStorage.getItem("contentmate_token");
    if (!token) {
      setError("This page is unavailable.");
      setIsLoading(false);
      return;
    }

    const load = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/admin/activity`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            response.status === 401 || response.status === 403
              ? "This page is unavailable."
              : payload.detail ?? "Could not load this page."
          );
        }
        setData(payload);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "This page is unavailable.");
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, []);

  return (
    <main className="shell legalShell">
      <section className="hero adminHero">
        <p className="eyebrow">Workspace</p>
        <h1>Internal activity view.</h1>
        <p>
          A quick read on who is using ContentMatePro, what they analyzed, and how the
          product is being used in the wild.
        </p>
        <div className="contactLinks compact">
          <Link href="/">Back to app</Link>
        </div>
      </section>

      {error ? <div className="errorCard adminPanel">{error}</div> : null}

      {isLoading ? (
        <section className="dashboard adminDashboard">
          <div className="panel adminPanel">
            <p className="sectionLabel">Loading</p>
            <h2>Pulling activity</h2>
            <p>One moment while we load the latest records.</p>
          </div>
        </section>
      ) : null}

      {data ? (
        <>
          <section className="statusGrid adminStats">
            <StatusCard label="Users" value={String(data.summary.total_users)} />
            <StatusCard
              label="Analyses"
              value={String(data.summary.total_channel_analyses)}
            />
            <StatusCard
              label="Channels"
              value={String(data.summary.total_channels)}
            />
          </section>

          <section className="dashboard adminDashboard">
            <div className="panel widePanel adminPanel">
              <p className="sectionLabel">Recent Activity</p>
              <div className="adminTable">
                <div className="adminTableHead">
                  <span>User</span>
                  <span>Channel</span>
                  <span>Focus</span>
                  <span>Coverage</span>
                  <span>When</span>
                </div>
                {data.activity.map((item) => (
                  <div className="adminTableRow" key={item.analysis_id}>
                    <span>
                      <strong>{item.user.name ?? "Unknown user"}</strong>
                      <small>{item.user.email}</small>
                    </span>
                    <span>
                      <strong>{item.channel.title}</strong>
                      <small>
                        <a href={item.channel.channel_url} rel="noreferrer" target="_blank">
                          Open channel
                        </a>
                      </small>
                    </span>
                    <span>
                      <strong>
                        {item.source_kind === "video" ? "Specific video" : "Channel"}
                      </strong>
                      <small>{item.model_name ?? "Unknown model"}</small>
                    </span>
                    <span>
                      <strong>{item.analyzed_video_count} videos</strong>
                      <small>{item.analyzed_transcript_count} detailed reads</small>
                    </span>
                    <span>
                      <strong>{new Date(item.analyzed_at).toLocaleString()}</strong>
                      <small>{item.channel.subscriber_count ?? 0} subscribers</small>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="statusCard">
      <p className="sectionLabel">{label}</p>
      <strong>{value}</strong>
    </article>
  );
}
