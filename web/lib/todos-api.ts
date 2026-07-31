/* Todos API — CRUD for personal todo items. */

import { apiFetch, apiUrl } from "@/lib/api";

export interface TodoItem {
  id: string;
  title: string;
  status: "open" | "done" | "dismissed";
  due_at: string | null;
  due_at_confidence: "high" | "medium" | "low" | null;
  kind: "assignment" | "exam" | "meeting" | "admin" | "other" | "manual";
  course: string | null;
  priority: "low" | "normal" | "high";
  notes: string;
  source: "email" | "manual";
  source_subject: string | null;
  source_from: string | null;
  created_at: number;
  updated_at: number;
  completed_at: number | null;
}

export async function listTodos(params?: {
  status?: string;
  kind?: string;
  due_before?: string;
  due_after?: string;
}): Promise<TodoItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.kind) searchParams.set("kind", params.kind);
  if (params?.due_before) searchParams.set("due_before", params.due_before);
  if (params?.due_after) searchParams.set("due_after", params.due_after);
  const qs = searchParams.toString();
  const res = await apiFetch(apiUrl(`/api/v1/todos${qs ? `?${qs}` : ""}`), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to list todos: ${res.status}`);
  return (await res.json()).todos ?? [];
}

export async function getUpcomingTodos(): Promise<TodoItem[]> {
  const res = await apiFetch(apiUrl("/api/v1/todos/upcoming"), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to get upcoming todos: ${res.status}`);
  return (await res.json()).todos ?? [];
}

export async function createTodo(data: {
  title: string;
  due_at?: string | null;
  kind?: string;
  course?: string;
  priority?: string;
  notes?: string;
}): Promise<TodoItem> {
  const res = await apiFetch(apiUrl("/api/v1/todos"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create todo: ${res.status}`);
  return (await res.json()).todo;
}

export async function updateTodo(
  id: string,
  data: Partial<TodoItem>,
): Promise<TodoItem> {
  const res = await apiFetch(apiUrl(`/api/v1/todos/${id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update todo: ${res.status}`);
  return (await res.json()).todo;
}

export async function deleteTodo(id: string): Promise<void> {
  const res = await apiFetch(apiUrl(`/api/v1/todos/${id}`), {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete todo: ${res.status}`);
}

export async function completeTodo(id: string): Promise<TodoItem> {
  return updateTodo(id, { status: "done" as const });
}
