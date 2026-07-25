/**
 * Theme persistence utilities
 * Handles light/dark theme with localStorage fallback and system preference detection
 */

export type Theme = "ocean" | "light" | "dark" | "glass" | "snow";

export const THEME_STORAGE_KEY = "deeptutor-theme";

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
    if (
      stored === "ocean" ||
      stored === "light" ||
      stored === "dark" ||
      stored === "glass" ||
      stored === "snow"
    ) {
      return stored;
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
 * Defaults to "ocean" (Ocean Beach Theme).
 */
export function getSystemTheme(): Theme {
  return "ocean";
}

/**
 * Apply theme to document
 */
export function applyThemeToDocument(theme: Theme): void {
  if (typeof document === "undefined") return;

  const html = document.documentElement;

  html.classList.remove("dark", "theme-glass", "theme-snow", "theme-ocean");

  if (theme === "ocean") {
    html.classList.add("theme-ocean");
  } else if (theme === "dark") {
    html.classList.add("dark");
  } else if (theme === "glass") {
    html.classList.add("dark", "theme-glass");
  } else if (theme === "snow") {
    html.classList.add("theme-snow");
  }
}

/**
 * Initialize theme on app startup
 * Priority: localStorage > default ("ocean")
 */
export function initializeTheme(): Theme {
  // Check localStorage first
  const stored = getStoredTheme();
  if (stored) {
    applyThemeToDocument(stored);
    return stored;
  }

  // Fall back to default ocean theme
  const defaultTheme: Theme = "ocean";
  applyThemeToDocument(defaultTheme);
  saveThemeToStorage(defaultTheme);
  return defaultTheme;
}

/**
 * Set theme and persist it
 */
export function setTheme(theme: Theme): void {
  applyThemeToDocument(theme);
  saveThemeToStorage(theme);
  notifyThemeChange(theme);
}
