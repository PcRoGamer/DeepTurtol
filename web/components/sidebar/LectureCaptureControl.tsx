"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, Loader2, Mic, Square } from "lucide-react";
import { apiFetch, apiUrl } from "@/lib/api";
import { listKnowledgeBases } from "@/lib/knowledge-api";

type State = "idle" | "recording" | "processing" | "ready" | "error";

/** Separate long-form recorder; it intentionally never shares chat STT state. */
export default function LectureCaptureControl({ collapsed }: { collapsed: boolean }) {
  const [state, setState] = useState<State>("idle");
  const [label, setLabel] = useState("Lecture capture");
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stream = useRef<MediaStream | null>(null);

  const release = useCallback(() => {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }, []);

  const submit = useCallback(async () => {
    const blob = new Blob(chunks.current, { type: recorder.current?.mimeType || "audio/webm" });
    chunks.current = [];
    if (!blob.size) { setState("idle"); return; }
    setState("processing"); setLabel("Preparing lecture notes…");
    try {
      const kbs = await listKnowledgeBases();
      const kb = kbs.find((item) => item.is_default) ?? kbs[0];
      const form = new FormData();
      // The library is independently durable. A knowledge base is an optional
      // downstream index, so first-time users can record before creating one.
      form.append("kb_name", kb?.name ?? "");
      form.append("file", blob, "lecture.webm");
      const response = await apiFetch(apiUrl("/api/v1/lectures"), { method: "POST", body: form });
      if (!response.ok) {
        const failure = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(
          failure?.detail || "Could not queue lecture processing.",
        );
      }
      const { id: itemId } = (await response.json()) as { id: string };
      if (!itemId) throw new Error("Lecture was queued without a library item ID.");
      const timer = window.setInterval(async () => {
        const result = await apiFetch(apiUrl(`/api/v1/lectures/${itemId}`));
        if (!result.ok) return;
        const job = (await result.json()) as { status: string; progress: string };
        setLabel(job.progress);
        if (job.status === "ready" || job.status === "failed") {
          window.clearInterval(timer);
          setState(job.status === "failed" ? "error" : "ready");
        }
      }, 1500);
    } catch (error) { setState("error"); setLabel(error instanceof Error ? error.message : "Lecture capture failed."); }
  }, []);

  const toggle = useCallback(async () => {
    if (state === "recording") { recorder.current?.stop(); return; }
    if (state !== "idle" && state !== "ready" && state !== "error") return;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = media; chunks.current = [];
      const next = new MediaRecorder(media);
      recorder.current = next;
      next.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      next.onstop = () => { release(); void submit(); };
      next.start(10_000); setState("recording"); setLabel("Recording lecture — click to stop");
    } catch { setState("error"); setLabel("Microphone permission was denied."); }
  }, [release, state, submit]);

  useEffect(() => () => { recorder.current?.stop(); release(); }, [release]);
  const busy = state === "recording" || state === "processing";
  return <button type="button" onClick={() => void toggle()} title={label}
    className={`group flex h-11 w-full items-center rounded-xl px-1 transition-all ${state === "recording" ? "bg-red-500/25 text-red-100" : "text-white/80 hover:bg-white/10 hover:text-white"}`}>
    <span className="flex h-9 w-9 shrink-0 items-center justify-center">{state === "processing" ? <Loader2 size={20} className="animate-spin" /> : state === "recording" ? <Square size={17} fill="currentColor" /> : <Mic size={21} />}</span>
    {!collapsed && <span className="ml-2 truncate text-left text-[13px] font-medium">{busy ? label : state === "ready" ? "Lecture notes ready" : "Lecture capture"}</span>}
    {!collapsed && <BookOpen size={14} className="ml-auto mr-2 opacity-65" />}
  </button>;
}
