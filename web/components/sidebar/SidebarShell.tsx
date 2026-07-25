"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppShell } from "@/context/AppShellContext";
import { OceanSidebar } from "@/components/sidebar/ocean-sidebar/OceanSidebar";
import {
  BookOpen,
  BookText,
  Bot,
  Brain,
  ChevronDown,
  Github,
  HeartHandshake,
  House,
  LayoutGrid,
  Library,
  Lock,
  PanelLeftClose,
  PanelLeftOpen,
  PenLine,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import SessionList from "@/components/SessionList";
import { VersionBadge } from "@/components/sidebar/VersionBadge";
import type { SessionSummary } from "@/lib/session-api";
import { Tooltip } from "@/components/ui/Tooltip";
import { useCapabilityAccess } from "@/components/access/CapabilityAccessContext";
import type { Capability } from "@/lib/capability-routes";

interface NavEntry {
  href: string;
  label: string;
  icon: LucideIcon;
  tooltipKey?: string;
  /** Model capability this feature needs; locked when the user lacks it. */
  requires?: Capability;
}

const PRIMARY_NAV: NavEntry[] = [
  {
    href: "/home",
    label: "Home",
    icon: House,
    tooltipKey: "Home tooltip",
    requires: "llm",
  },
  {
    href: "/partners",
    label: "Partners",
    icon: HeartHandshake,
    tooltipKey: "Partners tooltip",
    requires: "llm",
  },
  {
    href: "/agents",
    label: "My Agents",
    icon: Bot,
    tooltipKey: "Agents tooltip",
  },
  {
    href: "/co-writer",
    label: "Co-Writer",
    icon: PenLine,
    tooltipKey: "Co-Writer tooltip",
    requires: "llm",
  },
  {
    href: "/book",
    label: "Book",
    icon: Library,
    tooltipKey: "Book tooltip",
    requires: "llm",
  },
  {
    href: "/space",
    label: "Learning Space",
    icon: LayoutGrid,
    tooltipKey: "Space tooltip",
  },
];

const SECONDARY_NAV: NavEntry[] = [
  {
    href: "/memory",
    label: "Memory",
    icon: Brain,
    tooltipKey: "Memory tooltip",
  },
  {
    href: "/knowledge",
    label: "Knowledge Center",
    icon: BookOpen,
    tooltipKey: "Knowledge tooltip",
  },
  { href: "/settings", label: "Settings", icon: Settings },
];

const GITHUB_REPO_URL = "https://github.com/HKUDS/DeepTutor";
const DOCS_URL = "https://deeptutor.info/";
const RECENTS_COLLAPSED_KEY = "deeptutor.sidebar.recentsCollapsed";

interface SidebarShellProps {
  sessions?: SessionSummary[];
  activeSessionId?: string | null;
  loadingSessions?: boolean;
  showSessions?: boolean;
  onNewChat?: () => void;
  onSelectSession?: (sessionId: string) => void | Promise<void>;
  onRenameSession?: (sessionId: string, title: string) => void | Promise<void>;
  onDeleteSession?: (sessionId: string) => void | Promise<void>;
  footerSlot?: ReactNode | ((collapsed: boolean) => ReactNode);
}

export function SidebarShell({
  sessions = [],
  activeSessionId = null,
  loadingSessions = false,
  showSessions = false,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  footerSlot,
}: SidebarShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useTranslation();
  const { has } = useCapabilityAccess();
  const { sidebarCollapsed: collapsed, setSidebarCollapsed: setCollapsed } =
    useAppShell();

  const navLocked = (item: NavEntry) =>
    item.requires ? !has(item.requires) : false;
  const lockedTooltip = t("Locked — contact your administrator to get access.");
  const [recentsCollapsed, setRecentsCollapsed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setRecentsCollapsed(
      window.localStorage.getItem(RECENTS_COLLAPSED_KEY) === "1",
    );
  }, []);

  const toggleRecents = () => {
    setRecentsCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(RECENTS_COLLAPSED_KEY, next ? "1" : "0");
      }
      return next;
    });
  };

  const handleHomeClick = (event: React.MouseEvent) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1)
      return;
    event.preventDefault();
    onNewChat?.();
    router.push("/home");
  };

  return (
    <div className="relative flex h-screen shrink-0 overflow-visible">
      <OceanSidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed(!collapsed)}
        expandedWidth={275}
        collapsedWidth={52}
      >
        {(spawnBubbles, isExpanded) => {
          const renderedFooter =
            typeof footerSlot === "function"
              ? footerSlot(!isExpanded)
              : footerSlot;

          return !isExpanded ? (
            /* ── Collapsed Rail Mode (52px width, centered icons) ── */
            <div className="flex h-full w-[52px] flex-col items-center pt-3 pb-4 overflow-hidden select-none">
              {/* Expand Toggle Button absorbed into rail header */}
              <button
                onClick={() => setCollapsed(false)}
                onMouseEnter={(e) => spawnBubbles(e)}
                className="mb-4 flex h-9 w-9 items-center justify-center rounded-xl border border-white/35 bg-white/20 text-white/90 shadow-md backdrop-blur-md transition-all duration-200 hover:scale-105 hover:bg-white/30 hover:text-white active:scale-95 cursor-pointer"
                aria-label={t("Expand sidebar") as string}
                title={t("Expand sidebar") as string}
              >
                <PanelLeftOpen size={18} strokeWidth={2.2} />
              </button>

              {/* Primary Nav Icons */}
              <div className="flex flex-col items-center space-y-3 w-full px-1">
                {PRIMARY_NAV.map((item) => {
                  const active = pathname.startsWith(item.href);
                  const locked = navLocked(item);
                  if (locked) {
                    return (
                      <Tooltip
                        key={item.href}
                        label={t(item.label)}
                        description={lockedTooltip}
                        side="right"
                      >
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl text-white/40 cursor-not-allowed">
                          <item.icon size={20} strokeWidth={1.5} />
                        </div>
                      </Tooltip>
                    );
                  }
                  return (
                    <Tooltip key={item.href} label={t(item.label)} side="right">
                      <Link
                        href={item.href}
                        onMouseEnter={(e) => spawnBubbles(e)}
                        onClick={(e) => {
                          spawnBubbles(e);
                          if (item.href === "/home") handleHomeClick(e);
                        }}
                        className={`relative flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200 ${
                          active
                            ? "text-cyan-300"
                            : "text-white/70 hover:text-white hover:bg-white/10"
                        }`}
                      >
                        {/* Glowing Cyan Pill Indicator on left rail edge */}
                        {active && (
                          <div className="absolute left-[-10px] w-1 h-7 bg-cyan-300 rounded-r-full shadow-[0_0_12px_rgba(103,232,249,0.9)]" />
                        )}
                        <item.icon
                          size={21}
                          className={active ? "text-cyan-300" : "text-white/70"}
                          strokeWidth={active ? 2.1 : 1.6}
                        />
                      </Link>
                    </Tooltip>
                  );
                })}
              </div>

              <div className="my-3 w-6 border-t border-white/20" />

              {/* Secondary Nav Icons */}
              <div className="flex flex-col items-center space-y-3 w-full px-1">
                {SECONDARY_NAV.map((item) => {
                  const active = pathname.startsWith(item.href);
                  return (
                    <Tooltip key={item.href} label={t(item.label)} side="right">
                      <Link
                        href={item.href}
                        onMouseEnter={(e) => spawnBubbles(e)}
                        onClick={(e) => spawnBubbles(e)}
                        className={`relative flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200 ${
                          active
                            ? "text-cyan-300"
                            : "text-white/70 hover:text-white hover:bg-white/10"
                        }`}
                      >
                        {active && (
                          <div className="absolute left-[-10px] w-1 h-7 bg-cyan-300 rounded-r-full shadow-[0_0_12px_rgba(103,232,249,0.9)]" />
                        )}
                        <item.icon
                          size={21}
                          className={active ? "text-cyan-300" : "text-white/70"}
                          strokeWidth={active ? 2.1 : 1.6}
                        />
                      </Link>
                    </Tooltip>
                  );
                })}
              </div>

              <div className="flex-1" />

              {/* Footer Slot (Icon-only) */}
              <div className="flex flex-col items-center space-y-2 w-full px-1">
                {renderedFooter}
              </div>
            </div>
          ) : (
            /* ── Expanded Full Sidebar Mode (275px width) ── */
            <div className="flex h-full w-full flex-col pt-3 pb-4 overflow-hidden select-none">
              {/* Header Row */}
              <div className="flex h-12 items-center justify-between px-3.5 mb-2 shrink-0">
                <Link
                  href="/"
                  className="group flex items-center gap-1.5 overflow-hidden"
                  onMouseEnter={(e) => spawnBubbles(e)}
                >
                  <Image
                    src="/logo.png"
                    alt="DeepTurtol"
                    width={22}
                    height={22}
                    className="h-[22px] w-[22px] shrink-0 transition-transform duration-200 group-hover:scale-105"
                  />
                  <Image
                    src="/banner.png"
                    alt="DeepTurtol"
                    width={897}
                    height={236}
                    priority
                    className="h-[22px] w-auto transition-transform duration-200 group-hover:scale-105"
                  />
                </Link>

                <button
                  onClick={() => setCollapsed(true)}
                  onMouseEnter={(e) => spawnBubbles(e)}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-white/35 bg-white/20 text-white/90 shadow-md backdrop-blur-md transition-all duration-200 hover:scale-105 hover:bg-white/30 hover:text-white active:scale-95 cursor-pointer"
                  aria-label={t("Collapse sidebar") as string}
                  title={t("Collapse sidebar") as string}
                >
                  <PanelLeftClose size={17} strokeWidth={2.2} />
                </button>
              </div>

              {/* Primary Nav */}
              <nav className="px-3 pt-1">
                <div className="flex flex-col space-y-1.5 w-full">
                  {PRIMARY_NAV.map((item) => {
                    const active = pathname.startsWith(item.href);
                    const locked = navLocked(item);
                    if (locked) {
                      return (
                        <Tooltip
                          key={item.href}
                          label={t(item.label)}
                          description={lockedTooltip}
                          side="right"
                        >
                          <div className="flex h-11 w-full items-center gap-3.5 rounded-xl px-3.5 text-white/40 cursor-not-allowed">
                            <item.icon size={20} strokeWidth={1.5} />
                            <span className="whitespace-nowrap font-sans text-[14px]">
                              {t(item.label)}
                            </span>
                            <Lock
                              size={13}
                              strokeWidth={1.8}
                              className="ml-auto"
                            />
                          </div>
                        </Tooltip>
                      );
                    }
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onMouseEnter={(e) => spawnBubbles(e)}
                        onClick={(e) => {
                          spawnBubbles(e);
                          if (item.href === "/home") handleHomeClick(e);
                        }}
                        className={`group relative flex h-11 w-full items-center space-x-3.5 px-3.5 rounded-xl transition-all duration-200 ${
                          active
                            ? "bg-white/20 border border-white/30 font-semibold text-cyan-300 shadow-md backdrop-blur-md"
                            : "text-white/80 hover:bg-white/10 hover:text-white border border-transparent"
                        }`}
                      >
                        {/* Glowing Cyan Indicator Pill matching ocean_sidebar (1) */}
                        {active && (
                          <motion.div
                            layoutId="activeCurrentExpanded"
                            className="absolute left-0 w-1 h-8 bg-cyan-300 rounded-r-full shadow-[0_0_12px_rgba(103,232,249,0.9)]"
                          />
                        )}
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center">
                          <item.icon
                            size={21}
                            className={
                              active
                                ? "text-cyan-300"
                                : "text-white/70 group-hover:text-white"
                            }
                            strokeWidth={active ? 2.1 : 1.6}
                          />
                        </div>
                        <span
                          className={`whitespace-nowrap font-sans font-medium text-[14px] tracking-wide ${
                            active
                              ? "text-cyan-300 font-semibold"
                              : "text-white/80 group-hover:text-white"
                          }`}
                        >
                          {t(item.label)}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              </nav>

              {/* Chat History Section */}
              {showSessions &&
              onSelectSession &&
              onRenameSession &&
              onDeleteSession ? (
                <section
                  className={`mt-4 flex min-h-0 flex-col ${
                    recentsCollapsed ? "" : "flex-1"
                  }`}
                >
                  <button
                    type="button"
                    onClick={(e) => {
                      spawnBubbles(e);
                      toggleRecents();
                    }}
                    onMouseEnter={(e) => spawnBubbles(e)}
                    className="group/recents mx-3 flex items-center justify-between rounded-md px-2 py-1 text-left text-[11.5px] font-normal text-white/70 transition-colors hover:bg-white/10 hover:text-white"
                    aria-expanded={!recentsCollapsed}
                    aria-label={
                      recentsCollapsed
                        ? (t("Show recents") as string)
                        : (t("Hide recents") as string)
                    }
                  >
                    <span>{t("Recents")}</span>
                    <ChevronDown
                      size={13}
                      strokeWidth={1.7}
                      className={`transition-all duration-200 ${
                        recentsCollapsed
                          ? "-rotate-90 opacity-60"
                          : "rotate-0 opacity-0 group-hover/recents:opacity-60"
                      }`}
                    />
                  </button>
                  {!recentsCollapsed && (
                    <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-2 pt-0.5">
                      <SessionList
                        sessions={sessions}
                        activeSessionId={activeSessionId}
                        loading={loadingSessions}
                        onSelect={onSelectSession}
                        onRename={onRenameSession}
                        onDelete={onDeleteSession}
                        compact
                      />
                    </div>
                  )}
                </section>
              ) : null}

              {/* Filler */}
              {(!showSessions ||
                !onSelectSession ||
                !onRenameSession ||
                !onDeleteSession ||
                recentsCollapsed) && <div className="flex-1" />}

              {/* Secondary Nav & Footer */}
              <div className="border-t border-white/20 px-3 py-2 shrink-0">
                <div className="flex flex-col space-y-1 w-full">
                  {SECONDARY_NAV.map((item) => {
                    const active = pathname.startsWith(item.href);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onMouseEnter={(e) => spawnBubbles(e)}
                        onClick={(e) => spawnBubbles(e)}
                        className={`group relative flex h-11 w-full items-center space-x-3.5 px-3.5 rounded-xl transition-all duration-200 ${
                          active
                            ? "bg-white/20 border border-white/30 font-semibold text-cyan-300 shadow-md backdrop-blur-md"
                            : "text-white/80 hover:bg-white/10 hover:text-white border border-transparent"
                        }`}
                      >
                        {active && (
                          <motion.div
                            layoutId="activeCurrentExpanded"
                            className="absolute left-0 w-1 h-8 bg-cyan-300 rounded-r-full shadow-[0_0_12px_rgba(103,232,249,0.9)]"
                          />
                        )}
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center">
                          <item.icon
                            size={21}
                            className={
                              active
                                ? "text-cyan-300"
                                : "text-white/70 group-hover:text-white"
                            }
                            strokeWidth={active ? 2.1 : 1.6}
                          />
                        </div>
                        <span
                          className={`whitespace-nowrap font-sans font-medium text-[14px] tracking-wide ${
                            active
                              ? "text-cyan-300 font-semibold"
                              : "text-white/80 group-hover:text-white"
                          }`}
                        >
                          {t(item.label)}
                        </span>
                      </Link>
                    );
                  })}
                </div>

                <div className="mt-1 flex flex-col space-y-1 w-full">
                  {renderedFooter}
                </div>

                <div className="mt-2 flex items-center gap-0.5 px-1">
                  <VersionBadge />
                  <a
                    href={DOCS_URL}
                    target="_blank"
                    rel="noreferrer noopener"
                    title={t("Docs") as string}
                    aria-label={t("Docs") as string}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-white/70 transition-colors hover:bg-white/15 hover:text-white"
                    onMouseEnter={(e) => spawnBubbles(e)}
                  >
                    <BookText size={14} strokeWidth={1.6} />
                  </a>
                  <a
                    href={GITHUB_REPO_URL}
                    target="_blank"
                    rel="noreferrer noopener"
                    title="GitHub"
                    aria-label="GitHub"
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-white/70 transition-colors hover:bg-white/15 hover:text-white"
                    onMouseEnter={(e) => spawnBubbles(e)}
                  >
                    <Github size={14} strokeWidth={1.6} />
                  </a>
                </div>
              </div>
            </div>
          );
        }}
      </OceanSidebar>
    </div>
  );
}
