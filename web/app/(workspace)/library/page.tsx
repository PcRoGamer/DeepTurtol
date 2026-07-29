"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  CloudDownload,
  Download,
  ExternalLink,
  FileAudio,
  FileVideo,
  Loader2,
  Play,
  Puzzle,
  RefreshCw,
  Search,
  Upload,
  Waves,
} from "lucide-react";
import { apiFetch, apiUrl } from "@/lib/api";
import {
  closeLmsTab,
  getConnectorInfo,
  getExpectedConnectorVersion,
  hasEcho360Connector,
  listEcho360Courses,
  listEcho360Recordings,
  openEcho360ThroughLms,
  resolveEcho360Sources,
} from "@/lib/echo360-userscript";
import { listKnowledgeBases } from "@/lib/knowledge-api";

type MediaItem = {
  id: string;
  title: string;
  original_name: string;
  content_type: string;
  status: string;
  progress: string;
  created_at: string;
  summary?: string;
  kb_name?: string;
  source?: string;
  source_id?: string;
  course_name?: string;
};

type EchoCourse = { id: string; name: string; url: string };
type EchoRecording = {
  id: string;
  title: string;
  date: string;
  course_name: string;
  has_media: boolean;
  imported: boolean;
};


async function responseError(response: Response, fallback: string) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail || fallback;
  } catch {
    return fallback;
  }
}

export default function MediaLibraryPage() {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [active, setActive] = useState<MediaItem | null>(null);
  const [query, setQuery] = useState("");
  const [uploading, setUploading] = useState(false);
  const [kbName, setKbName] = useState("");
  const [echoBusy, setEchoBusy] = useState(false);
  const [echoError, setEchoError] = useState("");
  const [echoMessage, setEchoMessage] = useState("");
  const [echoBrowser, setEchoBrowser] = useState("");
  const [echoConnectorInstalled, setEchoConnectorInstalled] = useState<boolean | null>(null);
  const [echoConnectorVersion, setEchoConnectorVersion] = useState<string | null>(null);
  const [echoExpectedVersion, setEchoExpectedVersion] = useState<string | null>(null);
  const [showEchoViewer, setShowEchoViewer] = useState(false);
  const [echoViewerLoaded, setEchoViewerLoaded] = useState(false);
  const [echoViewerKey, setEchoViewerKey] = useState(0);
  const [echoCourses, setEchoCourses] = useState<EchoCourse[]>([]);
  const [courseId, setCourseId] = useState("");
  const [echoRecordings, setEchoRecordings] = useState<EchoRecording[]>([]);
  const [selectedRecordings, setSelectedRecordings] = useState<Set<string>>(new Set());
  const input = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    const response = await apiFetch(apiUrl("/api/v1/lectures"), { cache: "no-store" });
    if (response.ok) {
      setItems(((await response.json()) as { items: MediaItem[] }).items);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void refresh();
      void listKnowledgeBases().then((kbs) =>
        setKbName((kbs.find((kb) => kb.is_default) ?? kbs[0])?.name ?? ""),
      );
    }, 0);
    return () => window.clearTimeout(initialLoad);
  }, [refresh]);

  useEffect(() => {
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const upload = async (file?: File) => {
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("kb_name", kbName);
    const response = await apiFetch(apiUrl("/api/v1/lectures"), {
      method: "POST",
      body: form,
    });
    setUploading(false);
    if (response.ok) await refresh();
  };

  const loadEchoRecordings = useCallback(async (nextCourseId: string) => {
    if (!nextCourseId) return;
    setEchoBusy(true);
    setEchoError("");
    setEchoMessage("Reading the Echo360 course in your browser…");
    try {
      const body = await listEcho360Recordings(nextCourseId);
      const imported = new Set(
        items
          .filter((item) => item.source === "echo360")
          .map((item) => item.source_id ?? ""),
      );
      const recordings = body.recordings.map((recording) => ({
        ...recording,
        imported: imported.has(recording.id),
      }));
      setEchoRecordings(recordings);
      setSelectedRecordings(
        new Set(
          recordings
            .filter((recording) => !recording.imported && recording.has_media)
            .slice(0, 10)
            .map((recording) => recording.id),
        ),
      );
      setEchoMessage(
        recordings.length
          ? "Ready. The newest 10 unimported lectures are selected."
          : "No recorded lectures were found in this course.",
      );
    } catch (error) {
      setEchoError(
        error instanceof Error ? error.message : "Could not read this Echo360 course.",
      );
      setEchoMessage("");
    } finally {
      setEchoBusy(false);
    }
  }, [items]);

  const fetchEchoCourses = useCallback(async () => {
    setEchoBusy(true);
    setEchoError("");
    setEchoMessage("Loading your UniMelb Echo360 courses in your browser…");
    try {
      const body = await listEcho360Courses();
      setEchoBrowser("your normal browser");
      setEchoCourses(body.courses);
      const firstCourse = body.courses[0]?.id ?? "";
      setCourseId(firstCourse);
      if (firstCourse) await loadEchoRecordings(firstCourse);
      else setEchoMessage("Signed in, but Echo360 returned no current enrolments.");
    } catch (error) {
      setEchoError(error instanceof Error ? error.message : "Could not connect to UniMelb Echo360.");
      setEchoBrowser("");
      setEchoMessage("");
    } finally {
      setEchoBusy(false);
    }
  }, [loadEchoRecordings]);

  /* Auto-connect Echo360 once on mount — also checks version. */
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void (async () => {
        const info = await getConnectorInfo();
        const installed = info?.installed === true;
        setEchoConnectorInstalled(installed);
        if (info?.version) setEchoConnectorVersion(info.version);
        if (installed) {
          const expected = await getExpectedConnectorVersion();
          setEchoExpectedVersion(expected);
        }
        if (!installed) return;
        try {
          const body = await listEcho360Courses();
          setEchoBrowser("your normal browser");
          setEchoCourses(body.courses);
          const firstCourse = body.courses[0]?.id ?? "";
          setCourseId(firstCourse);
          if (firstCourse) await loadEchoRecordings(firstCourse);
        } catch {
          /* stale cookie — user clicks "Connect for import" */
        }
      })();
    }, 100);
    return () => window.clearTimeout(timer);
    // Intentionally runs once on mount so it doesn't re-fire when
    // loadEchoRecordings changes reference (it depends on `items`).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const connectEcho360 = async () => {
    setEchoBusy(true);
    setEchoError("");
    setEchoMessage("Checking the Echo360 connector…");

    const info = await getConnectorInfo();
    const installed = info?.installed === true;
    setEchoConnectorInstalled(installed);
    if (info?.version) setEchoConnectorVersion(info.version);
    if (installed) {
      const expected = await getExpectedConnectorVersion();
      setEchoExpectedVersion(expected);
    }
    if (!installed) {
      setEchoMessage("");
      setEchoBusy(false);
      return;
    }

    // Open the Canvas LMS launch so the Echo360 session cookie is fresh.
    // The userscript now makes API calls directly from this page via
    // GM_xmlhttpRequest — no Echo360 tab needs to be open.
    setEchoMessage("Opening Echo360 through UniMelb LMS…");
    try {
      await openEcho360ThroughLms();
    } catch {
      // best-effort
    }

    // Brief pause for the SSO redirect to set the cookie.
    await new Promise((r) => setTimeout(r, 3_000));

    setEchoMessage("Loading your UniMelb Echo360 courses in your browser…");
    try {
      const body = await listEcho360Courses();
      setEchoBrowser("your normal browser");
      setEchoCourses(body.courses);
      const firstCourse = body.courses[0]?.id ?? "";
      setCourseId(firstCourse);
      if (firstCourse) await loadEchoRecordings(firstCourse);
      else setEchoMessage("Signed in, but Echo360 returned no current enrolments.");
      closeLmsTab();
    } catch (error) {
      setEchoError(
        error instanceof Error
          ? error.message
          : "Could not connect to Echo360.",
      );
      setEchoMessage("");
    } finally {
      setEchoBusy(false);
    }
  };

  const importEcho360 = async () => {
    if (!courseId || !selectedRecordings.size) return;
    setEchoBusy(true);
    setEchoError("");
    setEchoMessage("Resolving selected Echo360 lectures in your browser…");
    let sources;
    try {
      sources = await resolveEcho360Sources(courseId, [...selectedRecordings]);
    } catch (error) {
      setEchoError(error instanceof Error ? error.message : "Could not resolve the selected Echo360 lectures.");
      setEchoMessage("");
      setEchoBusy(false);
      return;
    }
    setEchoMessage("Queueing Echo360 lectures in the background…");
    const response = await apiFetch(apiUrl("/api/v1/lectures/echo360/import"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        course_id: courseId,
        sources: sources.sources,
        kb_name: kbName,
      }),
    });
    if (!response.ok) {
      setEchoError(await responseError(response, "Could not queue Echo360 imports."));
      setEchoMessage("");
      setEchoBusy(false);
      return;
    }
    const body = (await response.json()) as {
      queued: MediaItem[];
      skipped: number;
    };
    setEchoMessage(
      `${body.queued.length} lecture${body.queued.length === 1 ? "" : "s"} queued` +
        (body.skipped ? `; ${body.skipped} already imported.` : "."),
    );
    setSelectedRecordings(new Set());
    setEchoBusy(false);
    await refresh();
    await loadEchoRecordings(courseId);
  };

  const toggleRecording = (recordingId: string) => {
    setSelectedRecordings((current) => {
      const next = new Set(current);
      if (next.has(recordingId)) next.delete(recordingId);
      else next.add(recordingId);
      return next;
    });
  };

  const visible = useMemo(
    () =>
      items.filter((item) =>
        `${item.title} ${item.summary ?? ""} ${item.course_name ?? ""}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [items, query],
  );
  return (
    <main className="h-full overflow-y-auto bg-[var(--background)] px-5 py-6 md:px-8">
      <section className="mx-auto max-w-7xl">
        <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[.18em] text-[var(--primary)]">
              <Waves size={15} /> DeepTurtol Library
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--foreground)]">
              Your learning media, remembered.
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-[var(--muted-foreground)]">
              Record lectures, upload course videos, or import from UniMelb Echo360.
              DeepTurtol keeps the original, creates a transcript and study notes,
              and makes them available to the learning agent.
            </p>
          </div>
          <button
            onClick={() => input.current?.click()}
            disabled={uploading}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-foreground)] shadow-sm disabled:opacity-50"
          >
            {uploading ? <Loader2 size={17} className="animate-spin" /> : <Upload size={17} />}
            Add recording
          </button>
          <input
            ref={input}
            type="file"
            className="hidden"
            accept="audio/*,video/mp4,video/webm,video/quicktime"
            onChange={(event) => void upload(event.target.files?.[0])}
          />
        </div>

        <div className="mb-6 rounded-2xl border border-cyan-500/25 bg-gradient-to-br from-cyan-500/10 via-[var(--card)] to-[var(--card)] p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex gap-3">
              <span className="mt-0.5 rounded-xl bg-cyan-500/15 p-2.5 text-cyan-600">
                <CloudDownload size={21} />
              </span>
              <div>
                <h2 className="font-semibold">UniMelb Echo360</h2>
                <p className="mt-1 max-w-2xl text-sm text-[var(--muted-foreground)]">
                  View Echo360 here through your normal browser session. Connect the
                  local bridge when you want DeepTurtol to import, transcribe, and
                  study your recordings.
                </p>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button
                onClick={() => {
                  if (!showEchoViewer) setEchoViewerLoaded(false);
                  setShowEchoViewer((current) => !current);
                }}
                aria-pressed={showEchoViewer}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-cyan-600 px-4 text-sm font-medium text-white"
              >
                <Play size={16} fill="currentColor" />
                {showEchoViewer ? "Hide Echo360" : "Open Echo360 here"}
              </button>
              <button
                onClick={() => void connectEcho360()}
                disabled={echoBusy}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-cyan-500/30 bg-[var(--background)] px-4 text-sm font-medium text-cyan-700 disabled:opacity-50 dark:text-cyan-300"
              >
                {echoBusy ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : echoBrowser ? (
                  <RefreshCw size={16} />
                ) : (
                  <CloudDownload size={16} />
                )}
                {echoConnectorInstalled === false ? "Set up import" : echoBrowser ? `Refresh from ${echoBrowser}` : "Connect for import"}
              </button>
            </div>
          </div>

          {showEchoViewer && (
            <div className="mt-5 overflow-hidden rounded-2xl border border-cyan-500/20 bg-[var(--background)] shadow-sm">
              <div className="flex flex-col gap-3 border-b border-[var(--border)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium">Echo360 Media Library</p>
                  <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">
                    Embedded from echo360.net.au using this browser&apos;s session.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => {
                      setEchoViewerLoaded(false);
                      setEchoViewerKey((current) => current + 1);
                    }}
                    className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 text-xs font-medium"
                  >
                    <RefreshCw size={13} />
                    Reload
                  </button>
                  <a
                    href="https://echo360.net.au/home"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-2.5 text-xs font-medium"
                  >
                    <ExternalLink size={13} />
                    Open in normal tab
                  </a>
                </div>
              </div>
              <div className="relative min-h-[420px] bg-white">
                {!echoViewerLoaded && (
                  <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-white text-sm text-slate-500">
                    <Loader2 size={17} className="mr-2 animate-spin" />
                    Loading Echo360…
                  </div>
                )}
                <iframe
                  key={echoViewerKey}
                  src="https://echo360.net.au/home"
                  title="UniMelb Echo360 Media Library"
                  className="h-[70vh] min-h-[420px] w-full border-0"
                  allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                  sandbox="allow-downloads allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts allow-storage-access-by-user-activation allow-top-navigation-by-user-activation"
                  referrerPolicy="strict-origin-when-cross-origin"
                  allowFullScreen
                  onLoad={() => setEchoViewerLoaded(true)}
                />
              </div>
              <p className="border-t border-[var(--border)] px-4 py-3 text-xs leading-5 text-[var(--muted-foreground)]">
                If UniMelb SSO refuses to appear inside the frame, use “Open in
                normal tab”, sign in with autofill, then return and reload this
                viewer. Viewing stays separate from importing so the learning agent
                only receives recordings you explicitly select.
              </p>
            </div>
          )}

          {echoError && (
            <p className="mt-4 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-600">
              {echoError}
            </p>
          )}
          {echoMessage && (
            <p className="mt-4 text-sm text-[var(--muted-foreground)]">{echoMessage}</p>
          )}

          {(echoConnectorInstalled === false) && (
            <div className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-sm">
              <div className="flex gap-3">
                <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-600">
                  <Puzzle size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">Set up Echo360 import</p>
                  <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">
                    One-time browser setup to let DeepTurtol import your recordings.
                  </p>

                  <div className="mt-4 space-y-0">
                    {[
                      {
                        title: "Install Tampermonkey",
                        desc: "Browser extension for Echo360 import.",
                        action: (
                          <a
                            href="https://www.tampermonkey.net/"
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-cyan-600 px-3 text-xs font-medium text-white"
                          >
                            <Download size={13} />
                            Get Tampermonkey
                          </a>
                        ),
                      },
                      {
                        title: "Install the connector script",
                        desc: "Adds the Echo360 import bridge.",
                        action: (
                          <a
                            href={apiUrl("/api/v1/lectures/echo360/connector.user.js")}
                            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-cyan-600 px-3 text-xs font-medium text-white"
                          >
                            <Download size={13} />
                            Install script
                          </a>
                        ),
                      },
                      {
                        title: "Enable script permissions",
                        desc: 'Chrome 138+ needs Developer Mode at chrome://extensions, or "Allow User Scripts" in Tampermonkey settings.',
                        action: null,
                      },
                      {
                        title: "Sign into Echo360",
                        desc: "Open echo360.net.au and log in with your UniMelb account.",
                        action: (
                          <a
                            href="https://echo360.net.au/home"
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 text-xs font-medium"
                          >
                            <ExternalLink size={13} />
                            Open Echo360
                          </a>
                        ),
                      },
                    ].map((step, index) => (
                      <div key={index} className="flex items-start gap-3 border-b border-[var(--border)] py-3 last:border-0">
                        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-500/10 text-xs font-semibold text-cyan-600">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm">{step.title}</p>
                          <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{step.desc}</p>
                        </div>
                        <div className="shrink-0">{step.action}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 text-sm font-medium text-white"
              >
                <RefreshCw size={14} />
                Reload page &mdash; I&apos;ve completed the steps above
              </button>
            </div>
          )}

          {/* Version mismatch banner */}
          {echoConnectorInstalled === true &&
            echoConnectorVersion &&
            echoExpectedVersion &&
            echoConnectorVersion !== echoExpectedVersion && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 shrink-0">⚠️</span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-amber-900">Connector needs update</p>
                  <p className="mt-1 text-amber-700">
                    Installed version <code className="rounded bg-amber-100 px-1 py-0.5">{echoConnectorVersion}</code>
                    &nbsp;— latest is <code className="rounded bg-amber-100 px-1 py-0.5">{echoExpectedVersion}</code>.
                    Reinstall from the link below to pick up the latest fixes.
                  </p>
                  <a
                    href={apiUrl("/api/v1/lectures/echo360/connector.user.js")}
                    className="mt-2 inline-flex h-8 items-center gap-1.5 rounded-lg bg-amber-600 px-3 text-xs font-medium text-white hover:bg-amber-700"
                  >
                    <Download size={13} />
                    Update script
                  </a>
                </div>
              </div>
            </div>
          )}

          {!!echoCourses.length && (
            <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(240px,.7fr)_minmax(0,1.3fr)]">
              <label className="text-sm">
                <span className="mb-2 block text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                  Course
                </span>
                <select
                  value={courseId}
                  onChange={(event) => {
                    const next = event.target.value;
                    setCourseId(next);
                    void loadEchoRecordings(next);
                  }}
                  className="h-11 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 outline-none"
                >
                  {echoCourses.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.name}
                    </option>
                  ))}
                </select>
              </label>

              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                    Recordings
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        setSelectedRecordings(
                          new Set(
                            echoRecordings
                              .filter((recording) => !recording.imported && recording.has_media)
                              .map((recording) => recording.id),
                          ),
                        )
                      }
                      className="text-xs font-medium text-[var(--primary)]"
                    >
                      Select all new
                    </button>
                    <span className="text-xs text-[var(--border)]">|</span>
                    <button
                      onClick={() => setSelectedRecordings(new Set())}
                      className="text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                    >
                      Deselect all
                    </button>
                  </div>
                </div>
                <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                  {echoRecordings.map((recording) => {
                    const selected = selectedRecordings.has(recording.id);
                    const disabled = recording.imported || !recording.has_media;
                    return (
                      <button
                        key={recording.id}
                        onClick={() => !disabled && toggleRecording(recording.id)}
                        disabled={disabled}
                        className="flex w-full items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2.5 text-left disabled:opacity-55"
                      >
                        <span
                          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border ${
                            selected
                              ? "border-cyan-500 bg-cyan-500 text-white"
                              : "border-[var(--border)]"
                          }`}
                        >
                          {selected && <Check size={14} />}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">
                            {recording.title}
                          </span>
                          <span className="text-xs text-[var(--muted-foreground)]">
                            {recording.date || "Undated"}
                          </span>
                        </span>
                        <span className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">
                          {recording.imported
                            ? "Imported"
                            : recording.has_media
                              ? "New"
                              : "Unavailable"}
                        </span>
                      </button>
                    );
                  })}
                </div>
                <button
                  onClick={() => void importEcho360()}
                  disabled={echoBusy || !selectedRecordings.size}
                  className="mt-3 inline-flex h-10 items-center gap-2 rounded-xl bg-cyan-600 px-4 text-sm font-medium text-white disabled:opacity-50"
                >
                  {echoBusy ? <Loader2 size={16} className="animate-spin" /> : <CloudDownload size={16} />}
                  Import {selectedRecordings.size || ""} selected
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="mb-5 flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3">
          <Search size={17} className="text-[var(--muted-foreground)]" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search titles, summaries, and courses"
            className="h-11 flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--muted-foreground)]"
          />
        </div>

        {active && (
          <div className="mb-7 grid gap-5 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-sm lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,.8fr)]">
            <div className="overflow-hidden rounded-xl bg-black">
              {active.content_type.startsWith("video/") ? (
                <video
                  controls
                  autoPlay
                  className="aspect-video w-full"
                  src={apiUrl(`/api/v1/lectures/${active.id}/media`)}
                >
                  <track
                    kind="subtitles"
                    src={apiUrl(`/api/v1/lectures/${active.id}/subtitles`)}
                    label="English"
                    default
                  />
                </video>
              ) : (
                <div className="flex min-h-48 items-center justify-center p-8">
                  <audio
                    controls
                    autoPlay
                    className="w-full"
                    src={apiUrl(`/api/v1/lectures/${active.id}/media`)}
                  />
                </div>
              )}
            </div>
            <div>
              <p className="text-xs uppercase tracking-widest text-[var(--primary)]">
                Now studying
              </p>
              <h2 className="mt-2 text-xl font-semibold">{active.title}</h2>
              {active.course_name && (
                <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                  {active.course_name}
                </p>
              )}
              <p className="mt-3 line-clamp-8 whitespace-pre-line text-sm leading-6 text-[var(--muted-foreground)]">
                {active.summary || active.progress}
              </p>
              <div className="mt-4 flex gap-3 text-xs">
                <a
                  className="text-[var(--primary)] underline"
                  href={apiUrl(`/api/v1/lectures/${active.id}/notes`)}
                  target="_blank"
                >
                  Study notes
                </a>
                <a
                  className="text-[var(--primary)] underline"
                  href={apiUrl(`/api/v1/lectures/${active.id}/transcript`)}
                  target="_blank"
                >
                  Transcript
                </a>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visible.map((item, index) => {
            const Icon = item.content_type.startsWith("video/") ? FileVideo : FileAudio;
            return (
              <button
                key={item.id}
                onClick={() => setActive(item)}
                className="group overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--card)] text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div
                  className={`relative flex aspect-video flex-col justify-between p-5 text-white ${
                    [
                      "bg-gradient-to-br from-cyan-700 to-sky-950",
                      "bg-gradient-to-br from-teal-600 to-emerald-950",
                      "bg-gradient-to-br from-indigo-600 to-slate-950",
                    ][index % 3]
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <Icon size={22} className="opacity-80" />
                    {item.source === "echo360" && (
                      <span className="rounded-full bg-black/25 px-2 py-1 text-[10px] uppercase tracking-wider">
                        Echo360
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="line-clamp-3 text-xl font-semibold leading-tight">
                      {item.title}
                    </p>
                    <p className="mt-2 line-clamp-2 text-xs text-white/70">
                      {item.summary || item.progress}
                    </p>
                  </div>
                  <span className="absolute bottom-4 right-4 rounded-full bg-black/35 p-2 backdrop-blur">
                    <Play size={16} fill="currentColor" />
                  </span>
                </div>
                <div className="flex items-center justify-between p-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {item.course_name || item.original_name}
                    </p>
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                      {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2 py-1 text-[10px] font-medium ${
                      item.status === "ready"
                        ? "bg-emerald-500/10 text-emerald-600"
                        : item.status === "failed"
                          ? "bg-red-500/10 text-red-600"
                          : "bg-amber-500/10 text-amber-600"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {!visible.length && (
          <div className="rounded-2xl border border-dashed border-[var(--border)] py-20 text-center text-sm text-[var(--muted-foreground)]">
            Your library is waiting for its first lecture.
          </div>
        )}
      </section>

    </main>
  );
}
