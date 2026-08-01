/**
 * Theme persistence utilities
 * Handles light/dark theme with localStorage fallback and system preference detection
 */

export type Theme = "beach" | "light" | "dark" | "glass" | "snow";

export const THEME_STORAGE_KEY = "deeptutor-theme";

/** All theme classes ever applied to <html>. Cleared before each apply so
 *  switching themes never leaves a stale class behind (the old code forgot
 *  `theme-beach`, so it piled up with the next theme's class and won by
 *  CSS order — beach stuck even after picking dark/glass/snow). */
const THEME_CLASSES = [
  "dark",
  "theme-glass",
  "theme-snow",
  "theme-beach",
  "theme-ocean", // legacy — never written again, but clean it up if present
] as const;

/**
 * Normalize any stored/legacy value into a valid Theme.
 * - legacy "ocean" (old theme id) → "beach" (the CSS class has always been
 *   theme-beach; the id just never matched it)
 * - anything unknown → "beach" (the default)
 */
export function normalizeTheme(value: string | null | undefined): Theme {
  if (value === "ocean") return "beach";
  if (value === "beach") return "beach";
  if (value === "snow") return "snow";
  if (value === "light") return "light";
  if (value === "dark") return "dark";
  if (value === "glass") return "glass";
  return "beach";
}

type ThemeChangeListener = (theme: Theme) => void;
const themeListeners = new Set<ThemeChangeListener>();

/**
 * Subscribe to theme changes
 */
export function subscribeToThemeChanges(
  listener: ThemeChangeListener,
): () => void {
  themeListeners.add(listener);
  return () => themeListeners.delete(listener);
}

/**
 * Notify all listeners of theme change
 */
function notifyThemeChange(theme: Theme): void {
  themeListeners.forEach((listener) => listener(theme));
}

/**
 * Get the stored theme from localStorage
 */
export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored) {
      const theme = normalizeTheme(stored);
      // Migrate legacy ids ("ocean") and stray values ("beach" was written by
      // ThemeScript before lib/theme knew about it) to the canonical id.
      if (stored !== theme) {
        localStorage.setItem(THEME_STORAGE_KEY, theme);
      }
      return theme;
    }
  } catch (e) {
    // Silently fail - localStorage may be disabled
  }

  return null;
}

/**
 * Save theme to localStorage
 */
export function saveThemeToStorage(theme: Theme): boolean {
  if (typeof window === "undefined") return false;

  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    return true;
  } catch (e) {
    // Silently fail - localStorage may be disabled or full
    return false;
  }
}

/**
 * Get system preference for theme.
 * Defaults to "beach" (Ocean Beach Theme).
 */
export function getSystemTheme(): Theme {
  return "beach";
}

/**
 * Apply theme to document
 */
export function applyThemeToDocument(theme: Theme): void {
  if (typeof document === "undefined") return;

  const html = document.documentElement;

  for (const cls of THEME_CLASSES) {
    html.classList.remove(cls);
  }

  switch (theme) {
    case "beach":
      html.classList.add("theme-beach");
      break;
    case "dark":
      html.classList.add("dark");
      break;
    case "glass":
      html.classList.add("dark", "theme-glass");
      break;
    case "snow":
      html.classList.add("theme-snow");
      break;
    case "light":
      // Cream — the plain no-class light palette (:root variables).
      break;
  }
}

/**
 * Initialize theme on app startup
 * Priority: localStorage > default ("beach")
 */
export function initializeTheme(): Theme {
  // Check localStorage first
  const stored = getStoredTheme();
  if (stored) {
    applyThemeToDocument(stored);
    return stored;
  }

  // Fall back to default beach theme
  const defaultTheme: Theme = "beach";
  applyThemeToDocument(defaultTheme);
  saveThemeToStorage(defaultTheme);
  return defaultTheme;
}

/**
 * Set theme and persist it
 */
export function setTheme(theme: Theme): void {
  const normalized = normalizeTheme(theme);
  applyThemeToDocument(normalized);
  saveThemeToStorage(normalized);
  notifyThemeChange(normalized);
}
