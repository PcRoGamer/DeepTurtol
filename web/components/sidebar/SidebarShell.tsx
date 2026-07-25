"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import { useAppShell } from "@/context/AppShellContext";
import { OceanSidebar } from "@/components/sidebar/ocean-sidebar/OceanSidebar";
import {
  BookOpen,
  BookText,
  Bot,
  Brain,
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

          return (
            <div className="flex h-full w-full flex-col pt-3 pb-4 overflow-hidden select-none">
              {/* Header Row */}
              <div className="flex h-12 items-center justify-between px-2 mb-2 shrink-0">
                <Link
                  href="/"
                  className="group flex items-center gap-1.5 overflow-hidden pl-1"
                  onMouseEnter={(e) => spawnBubbles(e)}
                >
                  <Image
                    src="/logo.png"
                    alt="DeepTurtol"
                    width={22}
                    height={22}
                    className="h-[22px] w-[22px] shrink-0 transition-transform duration-200 group-hover:scale-105"
                  />
                  <motion.div
                    initial={false}
                    animate={{
                      opacity: isExpanded ? 1 : 0,
                      width: isExpanded ? "auto" : 0,
                    }}
                    transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <Image
                      src="/banner.png"
                      alt="DeepTurtol"
                      width={897}
                      height={236}
                      priority
                      className="h-[22px] w-auto transition-transform duration-200 group-hover:scale-105"
                    />
                  </motion.div>
                </Link>

                <button
                  onClick={() => setCollapsed(!collapsed)}
                  onMouseEnter={(e) => spawnBubbles(e)}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-white/35 bg-white/20 text-white/90 shadow-md backdrop-blur-md transition-all duration-200 hover:scale-105 hover:bg-white/30 hover:text-white active:scale-95 cursor-pointer"
                  aria-label={
                    collapsed
                      ? (t("Expand sidebar") as string)
                      : (t("Collapse sidebar") as string)
                  }
                  title={
                    collapsed
                      ? (t("Expand sidebar") as string)
                      : (t("Collapse sidebar") as string)
                  }
                >
                  {collapsed ? (
                    <PanelLeftOpen size={17} strokeWidth={2.2} />
                  ) : (
                    <PanelLeftClose size={17} strokeWidth={2.2} />
                  )}
                </button>
              </div>

              {/* Primary Nav */}
              <nav className="px-1.5 pt-1 shrink-0">
                <div className="flex flex-col w-full space-y-1">
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
                          <div className="flex h-11 w-full items-center rounded-xl px-1 text-white/40 cursor-not-allowed">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center">
                              <item.icon size={20} strokeWidth={1.5} />
                            </div>
                            <motion.span
                              initial={false}
                              animate={{
                                opacity: isExpanded ? 1 : 0,
                                width: isExpanded ? "auto" : 0,
                                marginLeft: isExpanded ? 10 : 0,
                              }}
                              transition={{
                                duration: 0.2,
                                ease: [0.22, 1, 0.36, 1],
                              }}
                              className="whitespace-nowrap overflow-hidden font-sans text-[14px]"
                            >
                              {t(item.label)}
                            </motion.span>
                            {isExpanded && (
                              <Lock
                                size={13}
                                strokeWidth={1.8}
                                className="ml-auto pr-2"
                              />
                            )}
                          </div>
                        </Tooltip>
                      );
                    }
                    return (
                      <Tooltip
                        key={item.href}
                        label={!isExpanded ? t(item.label) : ""}
                        side="right"
                      >
                        <Link
                          key={item.href}
                          href={item.href}
                          onMouseEnter={(e) => spawnBubbles(e)}
                          onClick={(e) => {
                            spawnBubbles(e);
                            if (item.href === "/home") handleHomeClick(e);
                          }}
                          className={`group relative flex h-11 w-full items-center rounded-xl px-1 transition-all duration-200 ${
                            active
                              ? isExpanded
                                ? "bg-white/20 border border-white/30 font-semibold text-cyan-300 shadow-md backdrop-blur-md"
                                : "text-cyan-300"
                              : "text-white/80 hover:bg-white/10 hover:text-white border border-transparent"
                          }`}
                        >
                          {active && (
                            <motion.div
                              layoutId="activeCurrentIndicator"
                              className="absolute left-0 top-0 bottom-0 w-1 h-full bg-cyan-300 rounded-full shadow-[0_0_14px_rgba(103,232,249,0.95)] z-20"
                            />
                          )}
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center">
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
                          <motion.span
                            initial={false}
                            animate={{
                              opacity: isExpanded ? 1 : 0,
                              width: isExpanded ? "auto" : 0,
                              marginLeft: isExpanded ? 8 : 0,
                            }}
                            transition={{
                              duration: 0.2,
                              ease: [0.22, 1, 0.36, 1],
                            }}
                            className={`whitespace-nowrap overflow-hidden font-sans font-medium text-[14px] tracking-wide ${
                              active
                                ? "text-cyan-300 font-semibold"
                                : "text-white/80 group-hover:text-white"
                            }`}
                          >
                            {t(item.label)}
                          </motion.span>
                        </Link>
                      </Tooltip>
                    );
                  })}
                </div>
              </nav>

              {/* Separator Divider */}
              <div className="mx-2.5 my-2 border-t border-white/20 shrink-0" />

              {/* Secondary Nav (Memory, Knowledge Center, Settings) */}
              <div className="px-1.5 shrink-0">
                <div className="flex flex-col w-full space-y-1">
                  {SECONDARY_NAV.map((item) => {
                    const active = pathname.startsWith(item.href);
                    return (
                      <Tooltip
                        key={item.href}
                        label={!isExpanded ? t(item.label) : ""}
                        side="right"
                      >
                        <Link
                          key={item.href}
                          href={item.href}
                          onMouseEnter={(e) => spawnBubbles(e)}
                          onClick={(e) => spawnBubbles(e)}
                          className={`group relative flex h-11 w-full items-center rounded-xl px-1 transition-all duration-200 ${
                            active
                              ? isExpanded
                                ? "bg-white/20 border border-white/30 font-semibold text-cyan-300 shadow-md backdrop-blur-md"
                                : "text-cyan-300"
                              : "text-white/80 hover:bg-white/10 hover:text-white border border-transparent"
                          }`}
                        >
                          {active && (
                            <motion.div
                              layoutId="activeCurrentIndicator"
                              className="absolute left-0 top-0 bottom-0 w-1 h-full bg-cyan-300 rounded-full shadow-[0_0_14px_rgba(103,232,249,0.95)] z-20"
                            />
                          )}
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center">
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
                          <motion.span
                            initial={false}
                            animate={{
                              opacity: isExpanded ? 1 : 0,
                              width: isExpanded ? "auto" : 0,
                              marginLeft: isExpanded ? 8 : 0,
                            }}
                            transition={{
                              duration: 0.2,
                              ease: [0.22, 1, 0.36, 1],
                            }}
                            className={`whitespace-nowrap overflow-hidden font-sans font-medium text-[14px] tracking-wide ${
                              active
                                ? "text-cyan-300 font-semibold"
                                : "text-white/80 group-hover:text-white"
                            }`}
                          >
                            {t(item.label)}
                          </motion.span>
                        </Link>
                      </Tooltip>
                    );
                  })}
                </div>
              </div>

              {/* Flexible spacer */}
              <div className="flex-1" />

              {/* Footer Section */}
              <div className="border-t border-white/20 px-1.5 py-2 shrink-0">
                <div className="flex flex-col w-full space-y-1">
                  {renderedFooter}
                </div>

                {isExpanded && (
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
                )}
              </div>
            </div>
          );
        }}
      </OceanSidebar>
    </div>
  );
}
