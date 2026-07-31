"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Calendar,
  CheckCircle2,
  ClipboardList,
  Edit3,
  ExternalLink,
  Flag,
  Loader2,
  Mail,
  Plus,
  Trash2,
  XCircle,
} from "lucide-react";
import SpaceSectionHeader from "@/components/space/SpaceSectionHeader";
import {
  listTodos,
  createTodo,
  updateTodo,
  deleteTodo,
  completeTodo,
  getUpcomingTodos,
  type TodoItem,
} from "@/lib/todos-api";
import {
  summarizeEmails,
  getEmailMonitorStatus,
  type EmailMonitorStatus,
} from "@/lib/email-monitor-api";

const KIND_COLORS: Record<string, string> = {
  assignment:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  exam: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  meeting:
    "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  admin: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  other: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  manual:
    "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

const FILTERS = [
  { value: "upcoming", labelKey: "Upcoming" },
  { value: "open", labelKey: "Open" },
  { value: "done", labelKey: "Done" },
  { value: "all", labelKey: "All" },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  return new Date(dateStr) < new Date();
}

export default function TodosSection() {
  const { t } = useTranslation();
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("open");

  // Create form
  const [newTitle, setNewTitle] = useState("");
  const [newKind, setNewKind] = useState("manual");

  // Inline edit
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Partial<TodoItem>>({});

  // Email side panel
  const [summarizing, setSummarizing] = useState(false);
  const [summaryResult, setSummaryResult] = useState<string | null>(null);
  const [emailStatus, setEmailStatus] =
    useState<EmailMonitorStatus | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const items =
        filter === "upcoming"
          ? await getUpcomingTodos()
          : await listTodos(filter !== "all" ? { status: filter } : {});
      setTodos(items);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void getEmailMonitorStatus()
      .then(setEmailStatus)
      .catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    await createTodo({ title: newTitle.trim(), kind: newKind });
    setNewTitle("");
    setNewKind("manual");
    await load();
  };

  const handleComplete = async (id: string) => {
    await completeTodo(id);
    await load();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t("Delete this todo?"))) return;
    await deleteTodo(id);
    await load();
  };

  const handleStatusChange = async (id: string, status: string) => {
    await updateTodo(id, { status: status as TodoItem["status"] });
    await load();
  };

  const startEdit = (todo: TodoItem) => {
    setEditingId(todo.id);
    setEditValues({
      title: todo.title,
      due_at: todo.due_at,
      kind: todo.kind,
      course: todo.course,
      priority: todo.priority,
      notes: todo.notes,
    });
  };

  const saveEdit = async (id: string) => {
    await updateTodo(id, editValues);
    setEditingId(null);
    setEditValues({});
    await load();
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleSummarize = async () => {
    setSummarizing(true);
    try {
      const result = await summarizeEmails(1);
      setSummaryResult(
        result.summary?.overall_summary || t("Summary generated."),
      );
    } catch {
      setSummaryResult(t("Failed to generate summary."));
    } finally {
      setSummarizing(false);
    }
  };

  return (
    <div className="space-y-6">
      <SpaceSectionHeader
        icon={ClipboardList}
        title={t("Todos")}
        description={t(
          "Track assignments, exams, and deadlines from your university email.",
        )}
        meta={
          <span className="rounded-full border border-[var(--border)] bg-[var(--card)] px-2 py-0.5 text-[10.5px] font-medium text-[var(--muted-foreground)]">
            {todos.length} {t("items")}
          </span>
        }
      />

      {/* Create todo */}
      <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Plus size={15} className="text-[var(--muted-foreground)]" />
          <h2 className="text-[13.5px] font-semibold text-[var(--foreground)]">
            {t("Add todo")}
          </h2>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder={t("What needs to be done?")}
            className="min-w-[240px] flex-1 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[13px] text-[var(--foreground)] outline-none transition-colors focus:border-[var(--foreground)]/25"
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <select
            value={newKind}
            onChange={(e) => setNewKind(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[13px] text-[var(--foreground)] outline-none"
          >
            <option value="manual">{t("Task")}</option>
            <option value="assignment">{t("Assignment")}</option>
            <option value="exam">{t("Exam")}</option>
            <option value="meeting">{t("Meeting")}</option>
            <option value="admin">{t("Admin")}</option>
            <option value="other">{t("Other")}</option>
          </select>
          <button
            onClick={() => void handleCreate()}
            disabled={!newTitle.trim()}
            className="rounded-lg bg-[var(--primary)] px-3.5 py-2 text-[13px] font-medium text-[var(--primary-foreground)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {t("Add")}
          </button>
        </div>
      </section>

      {/* Main content: list + side panel */}
      <div className="grid gap-6 xl:grid-cols-[1fr_280px]">
        {/* Todo list */}
        <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
          {/* Filter tabs */}
          <div className="mb-5 flex items-center gap-1 rounded-lg bg-[var(--muted)] p-0.5">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-all ${
                  filter === f.value
                    ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                }`}
              >
                {t(f.labelKey)}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-[var(--muted-foreground)]" />
            </div>
          ) : todos.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--border)] px-6 py-12 text-center text-[13px] text-[var(--muted-foreground)]">
              {t("Nothing here yet. Add a todo or enable the email monitor.")}
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {todos.map((todo) => {
                const overdue =
                  todo.status === "open" && isOverdue(todo.due_at);
                const isEditing = editingId === todo.id;

                if (isEditing) {
                  return (
                    <div key={todo.id} className="space-y-3 py-4">
                      <input
                        value={editValues.title || ""}
                        onChange={(e) =>
                          setEditValues({
                            ...editValues,
                            title: e.target.value,
                          })
                        }
                        className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[13px] text-[var(--foreground)] outline-none"
                      />
                      <div className="flex flex-wrap gap-2">
                        <input
                          type="date"
                          value={
                            editValues.due_at
                              ? editValues.due_at.slice(0, 10)
                              : ""
                          }
                          onChange={(e) =>
                            setEditValues({
                              ...editValues,
                              due_at: e.target.value
                                ? new Date(e.target.value).toISOString()
                                : null,
                            })
                          }
                          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-[12px] text-[var(--foreground)] outline-none"
                        />
                        <select
                          value={editValues.kind || "manual"}
                          onChange={(e) =>
                            setEditValues({
                              ...editValues,
                              kind: e.target.value as TodoItem["kind"],
                            })
                          }
                          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-[12px] text-[var(--foreground)] outline-none"
                        >
                          <option value="manual">{t("Task")}</option>
                          <option value="assignment">{t("Assignment")}</option>
                          <option value="exam">{t("Exam")}</option>
                          <option value="meeting">{t("Meeting")}</option>
                          <option value="admin">{t("Admin")}</option>
                          <option value="other">{t("Other")}</option>
                        </select>
                        <select
                          value={editValues.priority || "normal"}
                          onChange={(e) =>
                            setEditValues({
                              ...editValues,
                              priority: e.target.value as TodoItem["priority"],
                            })
                          }
                          className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-[12px] text-[var(--foreground)] outline-none"
                        >
                          <option value="low">{t("Low")}</option>
                          <option value="normal">{t("Normal")}</option>
                          <option value="high">{t("High")}</option>
                        </select>
                        <input
                          value={editValues.course || ""}
                          onChange={(e) =>
                            setEditValues({
                              ...editValues,
                              course: e.target.value,
                            })
                          }
                          placeholder={t("Course")}
                          className="w-28 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-[12px] text-[var(--foreground)] outline-none"
                        />
                      </div>
                      <textarea
                        value={editValues.notes || ""}
                        onChange={(e) =>
                          setEditValues({
                            ...editValues,
                            notes: e.target.value,
                          })
                        }
                        placeholder={t("Notes")}
                        className="w-full resize-none rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-[12px] text-[var(--foreground)] outline-none"
                        rows={2}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => void saveEdit(todo.id)}
                          className="rounded-lg bg-[var(--primary)] px-3 py-1.5 text-[12px] font-medium text-[var(--primary-foreground)]"
                        >
                          {t("Save")}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-[12px] text-[var(--foreground)]"
                        >
                          {t("Cancel")}
                        </button>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={todo.id}
                    className={`group flex items-start gap-3 rounded-lg px-2 py-3.5 transition-colors hover:bg-[var(--muted)]/30 ${
                      todo.status === "done" ? "opacity-60" : ""
                    } ${overdue ? "border-l-2 border-l-red-400" : ""}`}
                  >
                    {/* Status action */}
                    <button
                      onClick={() => {
                        if (todo.status === "done") {
                          void handleStatusChange(todo.id, "open");
                        } else {
                          void handleComplete(todo.id);
                        }
                      }}
                      className="mt-0.5 shrink-0"
                      title={
                        todo.status === "done" ? t("Reopen") : t("Complete")
                      }
                    >
                      {todo.status === "done" ? (
                        <CheckCircle2 size={18} className="text-green-500" />
                      ) : (
                        <div className="h-[18px] w-[18px] rounded-full border-2 border-[var(--border)] group-hover:border-green-400" />
                      )}
                    </button>

                    {/* Content */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <span
                            className={`text-[14px] font-medium ${
                              todo.status === "done"
                                ? "text-[var(--muted-foreground)] line-through"
                                : "text-[var(--foreground)]"
                            }`}
                          >
                            {todo.title}
                          </span>

                          {/* Meta badges */}
                          <div className="mt-1.5 flex flex-wrap items-center gap-2">
                            {todo.kind && (
                              <span
                                className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-medium ${
                                  KIND_COLORS[todo.kind] || KIND_COLORS.other
                                }`}
                              >
                                {todo.kind}
                              </span>
                            )}

                            {todo.course && (
                              <span className="inline-flex items-center gap-1 rounded-md bg-[var(--muted)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--muted-foreground)]">
                                {todo.course}
                              </span>
                            )}

                            {todo.due_at && (
                              <span
                                className={`inline-flex items-center gap-1 text-[11px] ${
                                  overdue
                                    ? "font-medium text-red-500"
                                    : "text-[var(--muted-foreground)]"
                                }`}
                              >
                                <Calendar size={11} />
                                {formatDate(todo.due_at)}
                                {todo.due_at_confidence &&
                                  todo.due_at_confidence !== "high" && (
                                    <span className="text-[9px] opacity-60">
                                      ({todo.due_at_confidence})
                                    </span>
                                  )}
                              </span>
                            )}

                            {todo.priority === "high" && (
                              <span className="inline-flex items-center gap-1 text-[11px] text-amber-500">
                                <Flag size={11} />
                                {t("High")}
                              </span>
                            )}

                            {todo.source === "email" && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-[var(--muted-foreground)]">
                                <Mail size={10} />
                                {todo.source_subject
                                  ? todo.source_subject.slice(0, 30) + "\u2026"
                                  : t("Email")}
                              </span>
                            )}
                          </div>

                          {todo.notes && (
                            <p className="mt-1 line-clamp-2 text-[12px] text-[var(--muted-foreground)]/70">
                              {todo.notes}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      {todo.status === "open" && (
                        <button
                          onClick={() =>
                            void handleStatusChange(todo.id, "dismissed")
                          }
                          title={t("Dismiss")}
                          className="rounded-md p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                        >
                          <XCircle size={14} />
                        </button>
                      )}
                      <button
                        onClick={() => startEdit(todo)}
                        title={t("Edit")}
                        className="rounded-md p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
                      >
                        <Edit3 size={14} />
                      </button>
                      <button
                        onClick={() => void handleDelete(todo.id)}
                        title={t("Delete")}
                        className="rounded-md p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--destructive)]/10 hover:text-[var(--destructive)]"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Email activity side panel */}
        <aside className="space-y-4">
          <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <Mail size={15} className="text-[var(--muted-foreground)]" />
              <h2 className="text-[13.5px] font-semibold text-[var(--foreground)]">
                {t("Email Activity")}
              </h2>
            </div>

            {emailStatus && (
              <div className="mb-4 space-y-2 text-[12px]">
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">
                    {t("Monitor:")}
                  </span>
                  <span>
                    {emailStatus.running
                      ? "\u2705 " + t("Active")
                      : "\u23F8 " + t("Stopped")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">
                    {t("Poll count:")}
                  </span>
                  <span>{emailStatus.poll_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--muted-foreground)]">
                    {t("Todos from email:")}
                  </span>
                  <span>{emailStatus.todos_created}</span>
                </div>
                {emailStatus.last_poll_at && (
                  <div className="flex justify-between">
                    <span className="text-[var(--muted-foreground)]">
                      {t("Last poll:")}
                    </span>
                    <span>
                      {new Date(
                        emailStatus.last_poll_at * 1000,
                      ).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            )}

            <button
              onClick={() => void handleSummarize()}
              disabled={summarizing}
              className="w-full rounded-lg bg-[var(--primary)] px-3 py-2 text-[12px] font-medium text-[var(--primary-foreground)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {summarizing
                ? t("Summarizing\u2026")
                : t("Summarize last 24h")}
            </button>

            {summaryResult && (
              <div className="mt-3 rounded-lg bg-[var(--muted)] p-3 text-[12px] leading-relaxed text-[var(--foreground)]">
                {summaryResult}
              </div>
            )}

            <a
              href="/settings/email"
              className="mt-3 flex items-center justify-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-2 text-[12px] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              <ExternalLink size={12} />
              {t("Email Settings")}
            </a>
          </section>
        </aside>
      </div>
    </div>
  );
}
