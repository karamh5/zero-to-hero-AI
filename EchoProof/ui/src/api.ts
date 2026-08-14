/** Typed fetch client for the read-only API. Every screen goes through this,
 * so "backend disconnected" is one designed state rather than eight ad-hoc
 * catch blocks. */

import type {
  Availability,
  ConversationPack,
  Campaign,
  ClaimDetail,
  CorpusDetail,
  Criteria,
  Finding,
  JobInfo,
  Measurements,
  RerunDelta,
  RunDetail,
  RunSummary,
  Span,
} from "./types";

export class ApiError extends Error {
  status: number;
  disconnected: boolean;

  constructor(status: number, message: string, disconnected = false) {
    super(message);
    this.status = status;
    this.disconnected = disconnected;
  }
}

async function get<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path);
  } catch {
    throw new ApiError(0, "The API server is not reachable.", true);
  }
  if (!response.ok) {
    let message = `${response.status}`;
    try {
      const body = await response.json();
      if (body?.error) message = String(body.error);
    } catch {
      /* non-JSON error body; the status is the message */
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export const api = {
  runs: () => get<{ runs: RunSummary[] }>("/api/runs"),
  run: (id: string) => get<RunDetail>(`/api/runs/${encodeURIComponent(id)}`),
  findings: (id: string) =>
    get<{ run_id: string; findings: Finding[] }>(
      `/api/runs/${encodeURIComponent(id)}/findings`,
    ),
  spans: (id: string) =>
    get<{ run_id: string; head: string; spans: Span[] }>(
      `/api/runs/${encodeURIComponent(id)}/spans`,
    ),
  claim: (runId: string, claimId: string) =>
    get<ClaimDetail>(
      `/api/runs/${encodeURIComponent(runId)}/claims/${encodeURIComponent(claimId)}`,
    ),
  campaign: (id: string) => get<Campaign>(`/api/runs/${encodeURIComponent(id)}/campaign`),
  rerun: (id: string) => get<RerunDelta>(`/api/runs/${encodeURIComponent(id)}/rerun`),
  corpusList: () =>
    get<{ packs: { pack_id: string; label: string; citation: string; record_count: number; version: string }[] }>(
      "/api/corpus",
    ),
  corpus: (packId: string, run?: string) =>
    get<CorpusDetail>(
      `/api/corpus/${encodeURIComponent(packId)}${run ? `?run=${encodeURIComponent(run)}` : ""}`,
    ),
  criteria: () => get<Criteria>("/api/criteria"),
  measurements: () => get<Measurements>("/api/measurements"),
  availability: () => get<Availability>("/api/adjudicate/availability"),
  conversations: () => get<{ packs: ConversationPack[] }>("/api/conversations"),
  conversationPack: (packId: string) =>
    get<ConversationPack>(`/api/conversations/${encodeURIComponent(packId)}`),
  job: (jobId: string) => get<JobInfo>(`/api/adjudicate/${encodeURIComponent(jobId)}`),

  /** Run one prepared, role-labelled conversation. The API refuses free
   * text, so there is no client path that can submit unlabelled turns. */
  runConversation: async (
    packId: string,
    conversationId: string,
    title: string,
  ): Promise<JobInfo> => {
    let response: Response;
    try {
      response = await fetch("/api/adjudicate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pack_id: packId,
          conversation_id: conversationId,
          title,
        }),
      });
    } catch {
      throw new ApiError(0, "The API server is not reachable.", true);
    }
    const body = await response.json();
    if (!response.ok) throw new ApiError(response.status, String(body?.error ?? response.status));
    return body as JobInfo;
  },

  clipUrl: (runId: string, digest: string) =>
    `/api/runs/${encodeURIComponent(runId)}/clips/${encodeURIComponent(digest)}`,
  reportUrl: (runId: string) => `/api/runs/${encodeURIComponent(runId)}/report`,
  eventsUrl: (jobId: string) => `/api/adjudicate/${encodeURIComponent(jobId)}/events`,
};
