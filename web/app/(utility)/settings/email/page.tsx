"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Mail } from "lucide-react";
import { useTranslation } from "react-i18next";

import { apiFetch, apiUrl } from "@/lib/api";
import {
  SettingRow,
  SettingSection,
  SettingsPageHeader,
  inputClass,
  selectClass,
} from "@/components/settings/shared";
import { useSettings } from "@/components/settings/SettingsContext";
import { Toggle } from "@/components/settings/Toggle";

interface EmailSettings {
  enabled: boolean;
  imap_host: string;
  imap_port: number;
  imap_use_ssl: boolean;
  username: string;
  password: string;
  mailbox: string;
  poll_interval_seconds: number;
  sender_filter: string;
  subject_filter: string;
  mark_seen: boolean;
  consent_granted: boolean;
  auth_mode: string;
  bootstrap_last_n: number;
}

interface MonitorStatus {
  enabled: boolean;
  consent_granted: boolean;
  last_poll_at: number | null;
  last_error: string | null;
  poll_count: number;
  todos_created: number;
  running: boolean;
}

const DEFAULT_SETTINGS: EmailSettings = {
  enabled: false,
  imap_host: "outlook.office365.com",
  imap_port: 993,
  imap_use_ssl: true,
  username: "",
  password: "",
  mailbox: "INBOX",
  poll_interval_seconds: 300,
  sender_filter: "",
  subject_filter: "",
  mark_seen: false,
  consent_granted: false,
  auth_mode: "imap",
  bootstrap_last_n: 0,
};

export default function EmailSettingsPage() {
  const { t } = useTranslation();
  const { registerExtension } = useSettings();
  const [settings, setSettings] = useState<EmailSettings | null>(null);
  const [serverSnapshot, setServerSnapshot] = useState<EmailSettings | null>(null);
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [saving, setSaving] = useState(false);

  // Load settings
  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      apiFetch(apiUrl("/api/v1/email-monitor/settings")).then(r => r.json()),
      apiFetch(apiUrl("/api/v1/email-monitor/status")).then(r => r.json()),
    ]).then(([settingsResp, statusResp]) => {
      if (cancelled) return;
      setSettings(settingsResp.settings ?? DEFAULT_SETTINGS);
      setServerSnapshot(settingsResp.settings ?? DEFAULT_SETTINGS);
      setStatus(statusResp.status ?? null);
    });
    return () => { cancelled = true; };
  }, []);

  const dirty =
    !!settings &&
    !!serverSnapshot &&
    JSON.stringify(settings) !== JSON.stringify(serverSnapshot);

  const settingsRef = useRef<EmailSettings | null>(null);
  useEffect(() => { settingsRef.current = settings; }, [settings]);

  const save = useCallback(async () => {
    const current = settingsRef.current;
    if (!current) return;
    setSaving(true);
    try {
      const res = await apiFetch(apiUrl("/api/v1/email-monitor/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(current),
      });
      const data = await res.json();
      setSettings(data.settings);
      setServerSnapshot(data.settings);
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    registerExtension("email", { dirty, save });
    return () => registerExtension("email", null);
  }, [dirty, save, registerExtension]);

  const patch = <K extends keyof EmailSettings>(key: K, value: EmailSettings[K]) => {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await apiFetch(apiUrl("/api/v1/email-monitor/test"), { method: "POST" });
      const data = await res.json();
      setTestResult(data.success ? "✅ Connection successful" : `❌ ${data.message}`);
    } catch {
      setTestResult("❌ Connection test failed");
    } finally {
      setTesting(false);
    }
  };

  const handlePollNow = async () => {
    setPolling(true);
    try {
      await apiFetch(apiUrl("/api/v1/email-monitor/poll-now"), { method: "POST" });
      // Refresh status
      const res = await apiFetch(apiUrl("/api/v1/email-monitor/status"));
      const data = await res.json();
      setStatus(data.status ?? null);
    } finally {
      setPolling(false);
    }
  };

  if (!settings) {
    return (
      <div className="grid h-[60vh] place-items-center text-[13px] text-[var(--muted-foreground)]">
        <Loader2 className="h-4 w-4 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <SettingsPageHeader
        title={t("University Email Monitor")}
        description={t(
          "Monitor your university inbox for assignments, exams, and deadlines. Extracts todos with due dates using AI.",
        )}
      />

      {/* Enable / Consent */}
      <SettingSection title={t("Enable")} description={t("Turn the email monitor on or off.")}>
        <SettingRow
          title={t("Enable email monitor")}
          description={t("Start polling your inbox for new messages.")}
          control={
            <Toggle
              checked={settings.enabled}
              onChange={(v) => patch("enabled", v)}
            />
          }
        />
        <SettingRow
          title={t("Consent")}
          description={t("I understand that emails will be read and processed by AI.")}
          control={
            <Toggle
              checked={settings.consent_granted}
              onChange={(v) => patch("consent_granted", v)}
            />
          }
        />
      </SettingSection>

      {/* Connection Method */}
      <SettingSection
        title={t("Connection Method")}
        description={t("Choose how to connect to your mailbox.")}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {/* IMAP option */}
          <div
            className={`cursor-default rounded-xl border-2 p-4 transition-colors ${
              settings.auth_mode === "imap"
                ? "border-[var(--primary)] bg-[var(--primary)]/5"
                : "border-[var(--border)]"
            }`}
          >
            <div className="flex items-center justify-between">
              <h4 className="text-[13px] font-semibold text-[var(--foreground)]">
                {t("IMAP")}
              </h4>
              <span className="rounded-full bg-[var(--primary)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--primary)]">
                {t("Active")}
              </span>
            </div>
            <p className="mt-1 text-[12px] text-[var(--muted-foreground)]">
              {t("Username + app password. Works with Microsoft 365 and any IMAP server.")}
            </p>
          </div>

          {/* Graph OAuth option */}
          <div className="cursor-default rounded-xl border-2 border-dashed border-[var(--border)] bg-[var(--muted)]/30 p-4 opacity-70">
            <div className="flex items-center justify-between">
              <h4 className="text-[13px] font-semibold text-[var(--foreground)]">
                {t("Microsoft Graph")}
              </h4>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                {t("Coming soon")}
              </span>
            </div>
            <p className="mt-1 text-[12px] text-[var(--muted-foreground)]">
              {t(
                "OAuth 2.0 sign-in with your Microsoft 365 account. No password needed.",
              )}
            </p>
          </div>
        </div>
      </SettingSection>

      {/* IMAP Configuration */}
      <SettingSection
        title={t("IMAP Configuration")}
        description={t(
          "Microsoft 365 preset is pre-filled. Use an app password if 2FA is enabled.",
        )}
      >
        <SettingRow
          title={t("IMAP Host")}
          control={
            <input
              type="text"
              value={settings.imap_host}
              onChange={(e) => patch("imap_host", e.target.value)}
              className={inputClass + " w-64"}
            />
          }
        />
        <SettingRow
          title={t("Port")}
          control={
            <input
              type="number"
              value={settings.imap_port}
              onChange={(e) => patch("imap_port", parseInt(e.target.value) || 993)}
              className={inputClass + " w-24"}
            />
          }
        />
        <SettingRow
          title={t("Username")}
          description={t("Your full email address.")}
          control={
            <input
              type="text"
              value={settings.username}
              onChange={(e) => patch("username", e.target.value)}
              className={inputClass + " w-64"}
            />
          }
        />
        <SettingRow
          title={t("Password")}
          description={t("App password for M365, or your IMAP password.")}
          control={
            <input
              type="password"
              value={settings.password}
              onChange={(e) => patch("password", e.target.value)}
              className={inputClass + " w-64"}
              placeholder="********"
            />
          }
        />
        <SettingRow
          title={t("Mailbox")}
          control={
            <input
              type="text"
              value={settings.mailbox}
              onChange={(e) => patch("mailbox", e.target.value)}
              className={inputClass + " w-48"}
            />
          }
        />
      </SettingSection>

      {/* Poll Settings */}
      <SettingSection
        title={t("Poll Settings")}
        description={t("How often to check for new emails.")}
      >
        <SettingRow
          title={t("Poll interval (seconds)")}
          description={t("Minimum 60 seconds.")}
          control={
            <input
              type="number"
              value={settings.poll_interval_seconds}
              onChange={(e) => patch("poll_interval_seconds", Math.max(60, parseInt(e.target.value) || 300))}
              min={60}
              className={inputClass + " w-24"}
            />
          }
        />
        <SettingRow
          title={t("Mark as seen")}
          description={t("Mark emails as read after processing.")}
          control={
            <Toggle
              checked={settings.mark_seen}
              onChange={(v) => patch("mark_seen", v)}
            />
          }
        />
        <SettingRow
          title={t("Bootstrap last N")}
          description={t("Process up to this many existing messages on first poll (0 = disabled, max 50).")}
          control={
            <input
              type="number"
              value={settings.bootstrap_last_n}
              onChange={(e) => patch("bootstrap_last_n", Math.min(50, Math.max(0, parseInt(e.target.value) || 0)))}
              min={0}
              max={50}
              className={inputClass + " w-24"}
            />
          }
        />
      </SettingSection>

      {/* Filters */}
      <SettingSection
        title={t("Filters")}
        description={t("Only process emails matching these criteria (leave blank for all).")}
      >
        <SettingRow
          title={t("Sender filter")}
          description={t("Glob pattern, e.g. *@unimelb.edu.au")}
          control={
            <input
              type="text"
              value={settings.sender_filter}
              onChange={(e) => patch("sender_filter", e.target.value)}
              className={inputClass + " w-64"}
              placeholder="*@unimelb.edu.au"
            />
          }
        />
        <SettingRow
          title={t("Subject filter")}
          description={t("Keyword filter, e.g. assignment")}
          control={
            <input
              type="text"
              value={settings.subject_filter}
              onChange={(e) => patch("subject_filter", e.target.value)}
              className={inputClass + " w-64"}
              placeholder="assignment"
            />
          }
        />
      </SettingSection>

      {/* Actions */}
      <SettingSection
        title={t("Actions")}
        description={t("Test your connection or trigger an immediate poll.")}
      >
        <SettingRow
          title={t("Test connection")}
          description={t("Verify IMAP credentials and connectivity.")}
          control={
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestConnection}
                disabled={testing}
                className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3.5 py-2 text-[13px] font-medium disabled:cursor-not-allowed disabled:opacity-40"
              >
                {testing ? t("Testing...") : t("Test Connection")}
              </button>
              {testResult && (
                <span className="text-[12px] text-[var(--muted-foreground)]">{testResult}</span>
              )}
            </div>
          }
        />
        <SettingRow
          title={t("Check now")}
          description={t("Run an immediate poll cycle.")}
          control={
            <button
              onClick={handlePollNow}
              disabled={polling || !settings.enabled || !settings.consent_granted}
              className="rounded-lg bg-[var(--primary)] px-3.5 py-2 text-[13px] font-medium text-[var(--primary-foreground)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {polling ? t("Polling...") : t("Check Now")}
            </button>
          }
        />
      </SettingSection>

      {/* Status */}
      {status && (
        <SettingSection
          title={t("Status")}
          description={t("Current monitor state.")}
        >
          <div className="space-y-2 text-[13px]">
            <div className="flex gap-4">
              <span className="w-32 text-[var(--muted-foreground)]">{t("Running:")}</span>
              <span>{status.running ? "✅ Yes" : "❌ No"}</span>
            </div>
            <div className="flex gap-4">
              <span className="w-32 text-[var(--muted-foreground)]">{t("Last poll:")}</span>
              <span>{status.last_poll_at ? new Date(status.last_poll_at * 1000).toLocaleString() : "—"}</span>
            </div>
            <div className="flex gap-4">
              <span className="w-32 text-[var(--muted-foreground)]">{t("Polls executed:")}</span>
              <span>{status.poll_count}</span>
            </div>
            <div className="flex gap-4">
              <span className="w-32 text-[var(--muted-foreground)]">{t("Todos created:")}</span>
              <span>{status.todos_created}</span>
            </div>
            {status.last_error && (
              <div className="flex gap-4">
                <span className="w-32 text-[var(--destructive)]">{t("Last error:")}</span>
                <span className="text-[var(--destructive)]">{status.last_error}</span>
              </div>
            )}
          </div>
        </SettingSection>
      )}
    </div>
  );
}
