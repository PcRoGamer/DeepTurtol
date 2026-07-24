"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAppShell } from "@/context/AppShellContext";
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
    // My Agents is its own top-level feature (pulled out of the Learning
    // Space): connect a live local Claude Code / Codex to consult in chat,
    // and manage imported agent conversations. Ungated — managing connections
    // and imports needs no per-user model grant.
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
    // Memory is its own top-level console (pulled out of the Learning Space):
    // a place to inspect and curate the tutor's long-term memory, not a daily
    // workspace. Never gated — memory has no per-user model requirement.
    href: "/memory",
    label: "Memory",
    icon: Brain,
    tooltipKey: "Memory tooltip",
  },
  {
    // Knowledge Center sits just above Settings: it's a console for managing
    // KBs and retrieval engines, not a daily workspace. Never gated — embedding
    // / search are shared admin infrastructure, no per-user model grant needed.
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
  /** Clicking the Chat nav item resets to a fresh session via this handler. */
  onNewChat?: () => void;
  onSelectSession?: (sessionId: string) => void | Promise<void>;
  onRenameSession?: (sessionId: string, title: string) => void | Promise<void>;
  onDeleteSession?: (sessionId: string) => void | Promise<void>;
  /**
   * Footer content rendered below the nav. Pass a render function to receive
   * the current ``collapsed`` state so footer items (e.g. Admin / Sign out) can
   * switch to their icon-only variant when the rail is collapsed.
   */
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
  const renderedFooter =
    typeof footerSlot === "function" ? footerSlot(collapsed) : footerSlot;
  const [recentsCollapsed, setRecentsCollapsed] = useState(false);

  // Hydrate Recents collapse from localStorage after first render to stay SSR-safe.
  useEffect(() => {
    if (typeof window === "undefined") return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
    // Always reset to a fresh session (mirrors the old "New Chat" affordance);
    // let modifier-clicks fall through to default Link behavior so middle-click
    // open-in-new-tab still works.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1)
      return;
    event.preventDefault();
    onNewChat?.();
    router.push("/home");
  };

  /* ---- Turtol Smooth Ocean Wave Architecture ---- */
  return (
    <div className="relative flex h-screen shrink-0 overflow-visible">
      {/* 1. Single Static Toggle Button ALWAYS Fixed at Top-Left */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="sand-fixed-toggle-btn"
        aria-label={collapsed ? (t("Expand sidebar") as string) : (t("Collapse sidebar") as string)}
        title={collapsed ? (t("Expand sidebar") as string) : (t("Collapse sidebar") as string)}
      >
        {collapsed ? (
          <PanelLeftOpen size={18} strokeWidth={2.2} />
        ) : (
          <PanelLeftClose size={18} strokeWidth={2.2} />
        )}
      </button>

      {/* 2. Persistent Underneath Rail (always visible when collapsed) */}
      <div className="sand-rail-container pt-14">
        {/* Logo at top */}
        <Link
          href="/"
          aria-label="DeepTurtol"
          className="mb-4 flex h-9 w-9 items-center justify-center rounded-xl bg-white/15 transition-transform hover:scale-105"
        >
          <Image
            src="/logo.png"
            alt="DeepTurtol"
            width={24}
            height={24}
            className="h-6 w-6 rounded-md"
          />
        </Link>

        {/* Sine-Wave Staggered Pebble Rocks on Rail */}
        <div className="flex flex-1 flex-col items-center gap-3.5 pt-1">
          {PRIMARY_NAV.slice(0, 5).map((item, idx) => {
            const active = pathname.startsWith(item.href);
            return (
              <Tooltip
                key={item.href}
                label={t(item.label)}
                side="right"
              >
                <Link
                  href={item.href}
                  onClick={item.href === "/home" ? handleHomeClick : undefined}
                  className={`sand-rail-rock-${idx} relative flex h-8 w-8 items-center justify-center rounded-full transition-all duration-200 ${
                    active
                      ? "bg-white text-[#028090] shadow-md ring-2 ring-white/60"
                      : "bg-white/30 text-white hover:bg-white/50"
                  }`}
                >
                  <item.icon size={15} strokeWidth={active ? 2.2 : 1.7} />
                </Link>
              </Tooltip>
            );
          })}
        </div>
      </div>

      {/* 3. Wet Sand Texture Layer on Shore (revealed as water recedes) */}
      <div
        className="sand-wet-wash"
        style={{ opacity: collapsed ? 0.2 : 0.85 }}
      />

      {/* 4. Smooth Ocean Wave Panel (Extends Far Beyond Viewport Bounds Top/Bottom/Left, Seafoam Underneath Water) */}
      {!collapsed && (
        <aside
          className={`absolute left-0 top-0 bottom-0 z-30 flex h-screen w-[275px] flex-col py-0 ${
            collapsed ? "sand-layer-wave-collapse" : "sand-layer-wave-expand"
          }`}
        >
          {/* Extended Background SVG (Starts 140px above top, 140px below bottom, and 600px off-screen left!) */}
          <svg
            className="absolute -top-[140px] -bottom-[140px] -left-[600px] h-[calc(100vh+280px)] w-[900px] pointer-events-none drop-shadow-2xl overflow-visible"
            viewBox="0 0 900 1000"
            preserveAspectRatio="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="oceanWaveGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2A9D8F" />
                <stop offset="45%" stopColor="#00a896" />
                <stop offset="100%" stopColor="#05668d" />
              </linearGradient>

              {/* Seafoam texture blur filter */}
              <filter id="seafoamGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" />
              </filter>
            </defs>

            {/* Layer 1 (UNDERNEATH): Soft White Seafoam Foam Body (Rendered BEHIND water, extends left & 15px right onto shore) */}
            <path
              className="sand-seafoam-underlayer-ambient"
              d="M 0,0 L 878,0 C 904,75 855,150 886,225 C 916,300 862,375 894,450 C 922,525 855,600 886,675 C 916,750 862,825 894,900 C 910,950 882,985 878,1000 L 0,1000 Z"
              fill="rgba(255, 255, 255, 0.72)"
              filter="url(#seafoamGlow)"
            />

            {/* Layer 2 (ON TOP OF SEAFOAM): Solid Gradient Ocean Body (Deep Swell Ambient 5.4s) */}
            <path
              className="sand-ocean-body-ambient"
              d="M 0,0 L 860,0 C 883,75 840,150 867,225 C 893,300 845,375 873,450 C 897,525 840,600 867,675 C 893,750 845,825 873,900 C 887,950 863,985 860,1000 L 0,1000 Z"
              fill="url(#oceanWaveGrad)"
            />

            {/* Layer 3 (ON EDGE): Glowing White Seafoam Crest Line (Out-of-Phase Foam Crest Swell 7.2s) */}
            <path
              className="sand-seafoam-crest-ambient drop-shadow-[0_0_8px_rgba(255,255,255,0.85)]"
              d="M 860,0 C 883,75 840,150 867,225 C 893,300 845,375 873,450 C 897,525 840,600 867,675 C 893,750 845,825 873,900 C 887,950 863,985 860,1000"
              fill="none"
              stroke="rgba(255, 255, 255, 0.95)"
              strokeWidth="5"
              strokeLinecap="round"
            />
          </svg>

          {/* Sidebar Content (Text & Nav links — Staggered Layer 2) */}
          <div
            className={`relative z-10 flex h-full w-[220px] flex-col pl-14 pt-3 ${
              collapsed ? "sand-layer-content-collapse" : "sand-layer-content-expand"
            }`}
          >
            {/* Header: logo */}
            <div className="flex h-12 items-center px-2 mb-2">
              <Link href="/" className="group flex items-center gap-1.5">
                <Image
                  src="/logo.png"
                  alt="DeepTurtol"
                  width={22}
                  height={22}
                  className="h-[22px] w-[22px] transition-transform duration-200 group-hover:scale-105"
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
            </div>

            {/* Primary nav */}
            <nav className="px-2 pt-1">
              <div className="space-y-px">
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
                        <div
                          aria-label={`${t(item.label)} — ${lockedTooltip}`}
                          aria-disabled
                          className="flex cursor-not-allowed items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] text-white/40"
                        >
                          <item.icon size={16} strokeWidth={1.5} />
                          <span className="whitespace-nowrap">{t(item.label)}</span>
                          <Lock size={13} strokeWidth={1.8} className="ml-auto" />
                        </div>
                      </Tooltip>
                    );
                  }
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={item.href === "/home" ? handleHomeClick : undefined}
                      className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] transition-colors ${
                        active
                          ? "bg-white/20 font-semibold text-white shadow-sm"
                          : "text-white/90 hover:bg-white/15 hover:text-white"
                      }`}
                    >
                      <item.icon size={16} strokeWidth={active ? 1.9 : 1.5} />
                      <span className="whitespace-nowrap">{t(item.label)}</span>
                    </Link>
                  );
                })}
              </div>
            </nav>

            {/* Chat history — visible when expanded */}
            {showSessions && onSelectSession && onRenameSession && onDeleteSession ? (
              <section
                className={`mt-4 flex min-h-0 flex-col ${
                  recentsCollapsed ? "" : "flex-1"
                }`}
              >
                <button
                  type="button"
                  onClick={toggleRecents}
                  className="group/recents mx-2 flex items-center justify-between rounded-md px-2 py-1 text-left text-[11.5px] font-normal text-white/70 transition-colors hover:bg-white/10 hover:text-white"
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
                  <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2 pt-0.5">
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

            {/* Secondary nav + footer */}
            <div className="border-t border-white/20 px-2 py-2">
              {SECONDARY_NAV.map((item) => {
                const active = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] transition-colors ${
                      active
                        ? "bg-white/20 font-semibold text-white shadow-sm"
                        : "text-white/90 hover:bg-white/15 hover:text-white"
                    }`}
                  >
                    <item.icon size={16} strokeWidth={active ? 1.9 : 1.5} />
                    <span className="whitespace-nowrap">{t(item.label)}</span>
                  </Link>
                );
              })}
              {renderedFooter}
              <div className="mt-0.5 flex items-center gap-0.5">
                <VersionBadge />
                <a
                  href={DOCS_URL}
                  target="_blank"
                  rel="noreferrer noopener"
                  title={t("Docs") as string}
                  aria-label={t("Docs") as string}
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-white/70 transition-colors hover:bg-white/15 hover:text-white"
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
                >
                  <Github size={14} strokeWidth={1.6} />
                </a>
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
