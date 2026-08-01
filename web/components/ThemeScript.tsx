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
      var stored = localStorage.getItem('deeptutor-theme');
      var html = document.documentElement;
      html.classList.remove('dark', 'theme-glass', 'theme-snow', 'theme-beach', 'theme-ocean');
      if (stored === 'dark') {
        html.classList.add('dark');
      } else if (stored === 'glass') {
        html.classList.add('dark', 'theme-glass');
      } else if (stored === 'snow') {
        html.classList.add('theme-snow');
      } else if (stored === 'beach' || stored === 'ocean') {
        html.classList.add('theme-beach');
        if (stored === 'ocean') localStorage.setItem('deeptutor-theme', 'beach');
      } else if (stored === 'light') {
        // Cream — the plain no-class light palette.
      } else {
        // Default: Ocean Beach (matches getSystemTheme()).
        html.classList.add('theme-beach');
        localStorage.setItem('deeptutor-theme', 'beach');
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
