/**
 * ThemeScript - Initializes theme from localStorage before React hydration
 * This prevents the flash of wrong theme on page load.
 *
 * Uses next/script with beforeInteractive so the browser executes the snippet
 * before React hydrates, even when this component is rendered client-side.
 */
import Script from "next/script";

export default function ThemeScript() {
  const themeScript = `
    try {
      const stored = localStorage.getItem('deeptutor-theme');
      document.documentElement.classList.remove('dark', 'theme-glass', 'theme-snow');
      if (stored === 'dark') {
        document.documentElement.classList.add('dark');
      } else if (stored === 'glass') {
        document.documentElement.classList.add('dark', 'theme-glass');
      } else if (stored === 'beach' || stored === 'light') {
        document.documentElement.classList.add('theme-beach');
      } else {
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          document.documentElement.classList.add('dark');
          localStorage.setItem('deeptutor-theme', 'dark');
        } else {
          document.documentElement.classList.add('theme-beach');
          localStorage.setItem('deeptutor-theme', 'beach');
        }
      }
    } catch (e) {}
  `;

  return (
    <Script
      id="theme-init"
      strategy="beforeInteractive"
      dangerouslySetInnerHTML={{ __html: themeScript }}
    />
  );
}
