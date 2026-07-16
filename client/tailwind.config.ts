// Path in project: tailwind.config.ts
//
// Colors are NOT duplicated here as hex values. Tailwind just points its
// utility classes (bg-brand, text-ink, border-status-pending, etc.) at the
// CSS custom properties defined in src/styles/design-tokens.css. This means:
//   - design-tokens.css remains the single source of truth for values
//   - [data-theme='dark'] swapping still works at runtime, because the
//     utility class always resolves through var(--color-x), never a
//     baked-in hex
//   - theme.ts does not have to carry color values at all
 
import type { Config } from 'tailwindcss';
import tailwindcssAnimate from 'tailwindcss-animate';
 
const config: Config = {
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}'
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        'bg-elevated': 'var(--color-bg-elevated)',
        border: 'var(--color-border)',
        'border-strong': 'var(--color-border-strong)',
 
        ink: 'var(--color-ink)',
        'ink-muted': 'var(--color-ink-muted)',
        'ink-subtle': 'var(--color-ink-subtle)',
 
        brand: {
          DEFAULT: 'var(--color-brand)',
          hover: 'var(--color-brand-hover)',
          muted: 'var(--color-brand-muted)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          hover: 'var(--color-secondary-hover)',
          muted: 'var(--color-secondary-muted)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          muted: 'var(--color-accent-muted)',
        },
 
        status: {
          pending: 'var(--color-status-pending)',
          'pending-bg': 'var(--color-status-pending-bg)',
          approved: 'var(--color-status-approved)',
          'approved-bg': 'var(--color-status-approved-bg)',
          rejected: 'var(--color-status-rejected)',
          'rejected-bg': 'var(--color-status-rejected-bg)',
        },
 
        'focus-ring': 'var(--color-focus-ring)',
      },
      fontFamily: {
        display: ['Fraunces', 'Source Serif 4', 'Georgia', 'serif'],
        body: ['Work Sans', 'Noto Sans', 'system-ui', 'sans-serif'],
        phonetic: [
          'Charis SIL',
          'Doulos SIL',
          'Noto Sans',
          'Noto Sans Display',
          'monospace',
        ],
      },
      fontSize: {
        xs: 'var(--text-xs)',
        sm: 'var(--text-sm)',
        base: 'var(--text-base)',
        md: 'var(--text-md)',
        lg: 'var(--text-lg)',
        xl: 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
        '4xl': 'var(--text-4xl)',
      },
      spacing: {
        1: 'var(--space-1)',
        2: 'var(--space-2)',
        3: 'var(--space-3)',
        4: 'var(--space-4)',
        5: 'var(--space-5)',
        6: 'var(--space-6)',
        8: 'var(--space-8)',
        10: 'var(--space-10)',
        12: 'var(--space-12)',
        16: 'var(--space-16)',
        20: 'var(--space-20)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
      zIndex: {
        dropdown: 'var(--z-dropdown)',
        sticky: 'var(--z-sticky)',
        drawer: 'var(--z-drawer)',
        modal: 'var(--z-modal)',
        toast: 'var(--z-toast)',
      },
      transitionDuration: {
        fast: '120ms',
        base: '200ms',
        slow: '320ms',
      },
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
      },
    },
  },
  plugins: [tailwindcssAnimate],
};
export default config;