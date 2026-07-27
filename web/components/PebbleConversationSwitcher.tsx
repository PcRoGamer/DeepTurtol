"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PebbleTabs, { type PebbleTabItem } from "@/components/pebble-tabs";
import { useUnifiedChat } from "@/context/UnifiedChatContext";
import {
  deleteSession,
  listSessions,
  type SessionSummary,
} from "@/lib/session-api";
import { discoverSubject } from "@/lib/subject-discovery";

export interface PebbleConversationSwitcherProps {
  className?: string;
}

export default function PebbleConversationSwitcher({
  className = "",
}: PebbleConversationSwitcherProps) {
  const router = useRouter();
  const {
    newSession,
    cancelStreamingTurn,
    selectedSessionId,
    sidebarRefreshToken,
  } = useUnifiedChat();

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const hasLoadedSessionsRef = useRef(false);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await listSessions(50, 0, { force: true });
      setSessions(data);
      hasLoadedSessionsRef.current = true;
    } catch (error) {
      console.error("Failed to load sessions for PebbleTabs", error);
    }
  }, []);

  useEffect(() => {
    void fetchSessions();
  }, [fetchSessions, sidebarRefreshToken]);

  // Synchronously compute PebbleTabItems with clean subject discovery
  const pebbleTabs: PebbleTabItem[] = sessions.map((session) => {
    const title = (session.title || "New conversation").trim();
    const discovery = discoverSubject(
      title,
      session.last_message,
      session.preferences?.capability,
    );

    return {
      id: session.session_id,
      title,
      subject: discovery.subject,
      emoji: discovery.emoji,
      updated_at: session.updated_at,
    };
  });

  const handleSelectTab = useCallback(
    (sessionId: string) => {
      router.push(`/home/${sessionId}`);
    },
    [router],
  );

  const handleNewTab = useCallback(() => {
    cancelStreamingTurn();
    newSession();
    router.push("/home");
  }, [cancelStreamingTurn, newSession, router]);

  const handleCloseTab = useCallback(
    async (sessionId: string) => {
      try {
        await deleteSession(sessionId);
        setSessions((prev) =>
          prev.filter((session) => session.session_id !== sessionId),
        );
        if (selectedSessionId === sessionId) {
          cancelStreamingTurn();
          newSession();
          router.push("/home");
        }
      } catch (error) {
        console.error("Failed to delete session from PebbleTabs", error);
      }
    },
    [cancelStreamingTurn, newSession, router, selectedSessionId],
  );

  return (
    <div className={`w-full flex-shrink-0 ${className}`}>
      <PebbleTabs
        tabs={pebbleTabs}
        activeTabId={selectedSessionId}
        onSelectTab={handleSelectTab}
        onCloseTab={handleCloseTab}
        onNewTab={handleNewTab}
      />
    </div>
  );
}
