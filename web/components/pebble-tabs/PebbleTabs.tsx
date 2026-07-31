"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Plus, X, ChevronDown, ChevronUp, Folder } from 'lucide-react';

export interface PebbleTabItem {
  id: string;
  title: string;
  subject: string;
  emoji?: string;
  updated_at?: number;
}

export interface PebbleTabsProps {
  tabs?: PebbleTabItem[];
  activeTabId?: string | null;
  onSelectTab?: (id: string) => void;
  onCloseTab?: (id: string) => void;
  onNewTab?: () => void;
  className?: string;
}

const initialDemoTabs: PebbleTabItem[] = [
  { id: '1', title: 'Learn Rust in 24 hrs', subject: 'Coding', emoji: '🦀' },
  { id: '2', title: 'How to propagate monstera', subject: 'Lifestyle', emoji: '🌿' },
  { id: '3', title: 'Debugging obscure webpack errors', subject: 'Coding', emoji: '🐛' },
  { id: '4', title: 'Best sci-fi books 2024', subject: 'Lifestyle', emoji: '📚' },
  { id: '5', title: 'Drafting client proposal', subject: 'Work', emoji: '💼' },
  { id: '6', title: 'Midjourney prompt ideas', subject: 'Creative', emoji: '🎨' },
];

export const pebbleColors = [
  '#7C927F', // Celadon / Jade green
  '#7A7D91', // Slate blue/grey
  '#9B8D83', // Warm taupe/sandstone
  '#858C89', // Neutral grey-green
  '#A67C52', // Warm amber stone
  '#6B8E93', // Deep slate teal
];

const styles = `
  .pebble-tabs-container {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-bottom: none;
    position: relative;
    z-index: 20;
    width: 100%;
  }

  .pebble-tabs-scroll-area {
    display: flex;
    gap: 8px;
    flex-grow: 1;
    padding: 4px 4px 6px 4px;
    scrollbar-width: thin;
    scrollbar-color: rgba(163, 160, 141, 0.5) transparent;
  }


  .pebble-tabs-scroll-area::-webkit-scrollbar {
    width: 6px;
  }
  .pebble-tabs-scroll-area::-webkit-scrollbar-track {
    background: transparent;
  }
  .pebble-tabs-scroll-area::-webkit-scrollbar-thumb {
    background-color: #a3a08d;
    border-radius: 10px;
  }

  /* Folder Styling */
  .pebble-folder {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 20px 24px 22px 18px / 24px 18px 22px 20px; /* Irregular stone shape */
    font-size: 0.825rem;
    font-weight: 600;
    color: white;
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;
    user-select: none;
    white-space: nowrap;
    
    /* 3D Stone Lighting & Texture */
    box-shadow: 
      inset 0 4px 6px -2px rgba(255, 255, 255, 0.4),
      inset 0 -4px 6px -2px rgba(0, 0, 0, 0.4), 
      0 3px 5px -1px rgba(0, 0, 0, 0.15);
      
    background-image: 
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.15' style='mix-blend-mode: multiply;'/%3E%3C/svg%3E"),
      repeating-radial-gradient(ellipse at 20% 30%, rgba(255,255,255,0.05) 0, rgba(255,255,255,0.05) 1px, transparent 2px, transparent 15px),
      linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 40%, rgba(0,0,0,0.05) 60%, rgba(0,0,0,0.25) 100%);
    
    background-blend-mode: overlay, normal, normal;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }

  .pebble-folder-label {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 150px;
    line-height: 1.2;
    display: inline-block;
  }


  .pebble-folder:hover {
    transform: translateY(-1px);
    box-shadow: 
      inset 0 4px 6px -2px rgba(255, 255, 255, 0.4),
      inset 0 -4px 6px -2px rgba(0, 0, 0, 0.4), 
      0 5px 8px -1px rgba(0, 0, 0, 0.2);
    filter: brightness(1.05);
  }

  .pebble-folder.contains-active {
    box-shadow: 
      0 0 0 2px rgba(255,255,255,0.8),
      inset 0 4px 6px -2px rgba(255, 255, 255, 0.4), 
      inset 0 -4px 6px -2px rgba(0, 0, 0, 0.4), 
      0 3px 5px -1px rgba(0, 0, 0, 0.15);
  }

  .pebble-folder-count {
    background-color: rgba(0,0,0,0.25);
    border-radius: 10px;
    padding: 1px 6px;
    font-size: 0.725rem;
  }

  /* Individual Tab Styling (inside dropdown) */
  .pebble-dropdown-container {
    position: fixed;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 12px 20px 12px; 
    pointer-events: auto;
    max-height: 400px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .pebble-dropdown-tab {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    margin: 2px 4px 4px 4px;
    border-radius: 18px 22px 20px 24px / 20px 24px 18px 22px;
    font-size: 0.85rem;
    font-weight: 500;
    color: #f3f4f6;
    cursor: pointer;
    transition: all 0.2s ease;
    user-select: none;
    flex-shrink: 0;

    
    box-shadow: 
      inset 0 4px 6px -2px rgba(255, 255, 255, 0.3),
      inset 0 -4px 6px -2px rgba(0, 0, 0, 0.4), 
      0 3px 5px -1px rgba(0, 0, 0, 0.15);
      
    background-image: 
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.12' style='mix-blend-mode: multiply;'/%3E%3C/svg%3E"),
      repeating-radial-gradient(ellipse at 80% 70%, rgba(255,255,255,0.05) 0, rgba(255,255,255,0.05) 1px, transparent 2px, transparent 15px),
      linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 40%, rgba(0,0,0,0.05) 60%, rgba(0,0,0,0.25) 100%);
    
    background-blend-mode: overlay, normal, normal;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    
    opacity: 0;
    animation: cascadeDown 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.27) forwards;
  }

  .pebble-dropdown-tab:hover {
    transform: translateY(-2px) scale(1.02) !important;
    filter: brightness(1.1);
  }

  /* Active State (White Quartz look) */
  .pebble-dropdown-tab.active {
    background-color: #e5e5dd !important;
    color: #2d3748;
    text-shadow: none;
    font-weight: 600;
    
    box-shadow: 
      inset 0 4px 6px -2px rgba(255, 255, 255, 0.9), 
      inset 0 -3px 5px -2px rgba(0, 0, 0, 0.15), 
      0 4px 8px -2px rgba(0, 0, 0, 0.1);
      
    background-image: 
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.5' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.05' style='mix-blend-mode: multiply;'/%3E%3C/svg%3E"),
      linear-gradient(135deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0) 50%, rgba(0,0,0,0.02) 100%);
  }

  .pebble-title {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
  }

  .pebble-close {
    opacity: 0.6;
    transition: opacity 0.2s;
    border-radius: 50%;
    padding: 2px;
    color: #e5e7eb;
    margin-left: auto;
  }

  .pebble-dropdown-tab:hover .pebble-close {
    opacity: 1;
  }

  .pebble-close:hover {
    background-color: rgba(255,255,255,0.25);
    color: white;
  }
  
  .pebble-dropdown-tab.active .pebble-close { color: #6b7280; }
  .pebble-dropdown-tab.active .pebble-close:hover { background-color: rgba(0,0,0,0.1); color: #111827; }

  @keyframes cascadeDown {
    0% {
      opacity: 0;
      transform: translateY(-8px) scale(0.95);
    }
    100% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .pebble-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    padding-left: 10px;
  }

  .pebble-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 40% 60% 55% 45% / 50% 45% 55% 50%;
    background-color: #B3ADA2;
    color: #fff;
    text-shadow: 0 1px 1px rgba(0,0,0,0.2);
    transition: all 0.2s ease;
    
    box-shadow: 
      inset 0 3px 5px -2px rgba(255, 255, 255, 0.4),
      inset 0 -3px 5px -2px rgba(0, 0, 0, 0.3),
      0 2px 4px -1px rgba(0, 0, 0, 0.15);
      
    background-image: 
      url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.08' style='mix-blend-mode: multiply;'/%3E%3C/svg%3E"),
      linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 40%, rgba(0,0,0,0.05) 60%, rgba(0,0,0,0.15) 100%);
  }

  .pebble-btn:hover {
    background-color: #A39D92;
    transform: translateY(-1px);
    box-shadow: 
      inset 0 3px 5px -2px rgba(255, 255, 255, 0.4),
      inset 0 -3px 5px -2px rgba(0, 0, 0, 0.3),
      0 4px 6px -1px rgba(0, 0, 0, 0.2);
  }
`;

export default function PebbleTabs({
  tabs: controlledTabs,
  activeTabId: controlledActiveTabId,
  onSelectTab,
  onCloseTab,
  onNewTab,
  className = '',
}: PebbleTabsProps) {
  const [localTabs, setLocalTabs] = useState<PebbleTabItem[]>(initialDemoTabs);
  const [localActiveTab, setLocalActiveTab] = useState<string | null>(initialDemoTabs[0].id);
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<{
    subject: string;
    top: number;
    left: number;
  } | null>(null);

  const tabs = controlledTabs ?? localTabs;
  const activeTab = controlledActiveTabId !== undefined ? controlledActiveTabId : localActiveTab;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        activeDropdown &&
        target &&
        !target.closest('.pebble-folder') &&
        !target.closest('.pebble-dropdown-container')
      ) {
        setActiveDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [activeDropdown]);

  const handleCloseTab = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (onCloseTab) {
      onCloseTab(id);
    } else {
      const newTabs = localTabs.filter((t) => t.id !== id);
      setLocalTabs(newTabs);
      if (localActiveTab === id && newTabs.length > 0) {
        setLocalActiveTab(newTabs[0].id);
      } else if (newTabs.length === 0) {
        setLocalActiveTab(null);
      }
    }
  };

  const handleSelectTab = (id: string) => {
    if (onSelectTab) {
      onSelectTab(id);
    } else {
      setLocalActiveTab(id);
    }
    setActiveDropdown(null);
  };

  const handleAddTab = () => {
    if (onNewTab) {
      onNewTab();
    } else {
      const newId = String(Date.now());
      const newTab: PebbleTabItem = {
        id: newId,
        title: 'New Session',
        subject: 'General',
        emoji: '🐚',
      };
      setLocalTabs([newTab, ...localTabs]);
      setLocalActiveTab(newId);
    }
  };

  // Group tabs by subject
  const groupedTabs = tabs.reduce<Record<string, PebbleTabItem[]>>((acc, tab) => {
    const sub = tab.subject || 'General';
    if (!acc[sub]) {
      acc[sub] = [];
    }
    acc[sub].push(tab);
    return acc;
  }, {});

  // Sort subject folders by the timestamp of their most recent chat:
  // Left = Most recent chat activity; Right = Oldest chat activity.
  const sortedSubjectEntries = Object.entries(groupedTabs).sort((a, b) => {
    const maxTimeA = Math.max(...a[1].map((t) => t.updated_at || 0));
    const maxTimeB = Math.max(...b[1].map((t) => t.updated_at || 0));
    return maxTimeB - maxTimeA;
  });

  const toggleDropdown = (e: React.MouseEvent<HTMLDivElement>, subject: string) => {
    e.stopPropagation();
    if (activeDropdown?.subject === subject) {
      setActiveDropdown(null);
    } else {
      const rect = e.currentTarget.getBoundingClientRect();
      setActiveDropdown({
        subject,
        top: rect.bottom + 4,
        left: rect.left,
      });
    }
  };

  return (
    <div className={`pebble-tabs-wrapper w-full ${className}`}>
      <style>{styles}</style>

      <div className="pebble-tabs-container min-h-[52px]">
        <div
          className="pebble-tabs-scroll-area"
          style={{
            height: isExpanded ? '130px' : '48px',
            minHeight: '48px',
            flexWrap: isExpanded ? 'wrap' : 'nowrap',
            overflowX: isExpanded ? 'hidden' : 'auto',
            overflowY: isExpanded ? 'auto' : 'visible',
            alignItems: 'center',
            transition: 'height 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            position: isExpanded ? 'absolute' : 'relative',
            top: isExpanded ? '6px' : 'auto',
            left: isExpanded ? '14px' : 'auto',
            right: isExpanded ? '80px' : 'auto',
            background: isExpanded ? 'rgba(215, 210, 198, 0.95)' : 'transparent',
            backdropFilter: isExpanded ? 'blur(8px)' : 'none',
            zIndex: isExpanded ? 30 : 'auto',
            borderRadius: isExpanded ? '14px' : '0',
            boxShadow: isExpanded ? '0 10px 25px -5px rgba(0, 0, 0, 0.2)' : 'none',
            padding: isExpanded ? '10px' : '4px 4px 6px 4px',
          }}
        >
          {sortedSubjectEntries.map(([subject, subjectTabs], groupIndex) => {
            const groupColor = pebbleColors[groupIndex % pebbleColors.length];
            const isActiveGroup = subjectTabs.some((t) => t.id === activeTab);
            const firstEmoji = subjectTabs[0]?.emoji;

            return (
              <div key={subject} className="flex flex-col">
                <div
                  className={`pebble-folder ${isActiveGroup ? 'contains-active' : ''}`}
                  style={{ backgroundColor: groupColor }}
                  onClick={(e) => toggleDropdown(e, subject)}
                  title={`${subject} (${subjectTabs.length} sessions)`}
                >
                  <Folder size={14} />
                  <span className="pebble-folder-label">
                    {firstEmoji ? `${firstEmoji} ` : ''}
                    {subject}
                  </span>
                  <span className="pebble-folder-count">{subjectTabs.length}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pebble-actions">
          <button
            type="button"
            className="pebble-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse rows' : 'Expand to show all subject folders'}
          >
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <button
            type="button"
            className="pebble-btn"
            onClick={handleAddTab}
            title="New Chat Session"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      {activeDropdown && groupedTabs[activeDropdown.subject] && (
        <div
          className="pebble-dropdown-container"
          style={{
            top: `${activeDropdown.top}px`,
            left: `${activeDropdown.left}px`,
          }}
        >
          {groupedTabs[activeDropdown.subject]
            .slice()
            .sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0))
            .map((tab, index) => {
              const isActive = activeTab === tab.id;
              const groupIndex = sortedSubjectEntries.findIndex(
                ([sub]) => sub === activeDropdown.subject,
              );
              const tabColor = pebbleColors[(groupIndex >= 0 ? groupIndex : 0) % pebbleColors.length];

              return (
                <div
                  key={tab.id}
                  className={`pebble-dropdown-tab ${isActive ? 'active' : ''}`}
                  style={{
                    backgroundColor: isActive ? '#f9fafb' : tabColor,
                    animationDelay: `${index * 0.04}s`,
                  }}
                  onClick={() => handleSelectTab(tab.id)}
                  title={tab.title}
                >
                  {tab.emoji && <span className="text-sm">{tab.emoji}</span>}
                  <span className="pebble-title">{tab.title}</span>
                  <button
                    type="button"
                    className="pebble-close"
                    onClick={(e) => {
                      handleCloseTab(e, tab.id);
                      if (groupedTabs[activeDropdown.subject]?.length === 1) {
                        setActiveDropdown(null);
                      }
                    }}
                    title="Close conversation"
                  >
                    <X size={13} />
                  </button>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}

