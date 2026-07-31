/* Email Monitor API — status, summarise, and settings. */

import { apiFetch, apiUrl } from "@/lib/api";

export interface EmailMonitorStatus {
  enabled: boolean;
  consent_granted: boolean;
  last_poll_at: number | null;
  last_error: string | null;
  poll_count: number;
  todos_created: number;
  running: boolean;
}

export interface EmailSummary {
  overall_summary?: string;
  [key: string]: unknown;
}

/**
 * Get the current email monitor status.
 */
export async function getEmailMonitorStatus(): Promise<EmailMonitorStatus> {
  const res = await apiFetch(apiUrl("/api/v1/email-monitor/status"), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to get email status: ${res.status}`);
  const body = await res.json();
  return body.status;
}

/**
 * Generate an on-demand digest of recent emails.
 */
export async function summarizeEmails(
  sinceDays: number = 1,
): Promise<{ success: boolean; summary?: EmailSummary; message_count?: number }> {
  const res = await apiFetch(apiUrl("/api/v1/email-monitor/summarize"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ since_days: sinceDays }),
  });
  if (!res.ok) throw new Error(`Failed to summarise emails: ${res.status}`);
  return res.json();
}

/**
 * List cached email digests.
 */
export async function listEmailSummaries(): Promise<
  { id: string; data: EmailSummary }[]
> {
  const res = await apiFetch(apiUrl("/api/v1/email-monitor/summaries"), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to list email summaries: ${res.status}`);
  const body = await res.json();
  return body.summaries ?? [];
}
