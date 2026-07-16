/**
 * Akita — Theme
 * Path in project: src/lib/theme.ts
 *
 * Deliberately NOT a duplicate color store. design-tokens.css is the single
 * source of truth for every color/spacing/type value, and tailwind.config.ts
 * points its utility classes at those same CSS custom properties via var().
 *
 * This file only holds what CSS variables genuinely cannot serve:
 *   - plain numbers for JS logic (breakpoints for useMediaQuery, since
 *     matchMedia() needs a literal number, not a CSS var)
 * 
 *   - a typed getter for the rare case a component needs a raw color value
 *     in JS rather than a class name (e.g. Waveform's canvas fill,
 *     which can't take a Tailwind class)
 * 
 *   - the ThemeMode type used by useTheme
 *
 * Hex values for colours belong in
 * design-tokens.css instead -- that's the only place dark mode switching
 * actually works.
 */

export type ThemeMode = 'light' | 'dark';

// Numeric mirror of the --breakpoint-* custom properties in
// design-tokens.css. Kept here only because window.matchMedia() needs a
// literal number, and CSS custom properties can't be read into @media
// queries or into JS without a DOM read.
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export type Breakpoint = keyof typeof breakpoints;

// Color tokens that exist in design-tokens.css, kept as a name list (not
// values) so components get autocomplete when calling getColor() without
// re-declaring the actual hex anywhere.
const colorTokens = [
  'bg', 'bgElevated', 'border', 'borderStrong',
  'ink', 'inkMuted', 'inkSubtle',
  'brand', 'brandHover', 'brandMuted',
  'secondary', 'secondaryHover', 'secondaryMuted',
  'accent', 'accentHover', 'accentMuted',
  'statusPending', 'statusPendingBg',
  'statusApproved', 'statusApprovedBg',
  'statusRejected', 'statusRejectedBg',
  'focusRing', 'overlay', 'white',
] as const;

export type ColorToken = (typeof colorTokens)[number];

const tokenToCssVar: Record<ColorToken, string> = {
  bg: '--color-bg',
  bgElevated: '--color-bg-elevated',
  border: '--color-border',
  borderStrong: '--color-border-strong',
  ink: '--color-ink',
  inkMuted: '--color-ink-muted',
  inkSubtle: '--color-ink-subtle',
  brand: '--color-brand',
  brandHover: '--color-brand-hover',
  brandMuted: '--color-brand-muted',
  secondary: '--color-secondary',
  secondaryHover: '--color-secondary-hover',
  secondaryMuted: '--color-secondary-muted',
  accent: '--color-accent',
  accentHover: '--color-accent-hover',
  accentMuted: '--color-accent-muted',
  statusPending: '--color-status-pending',
  statusPendingBg: '--color-status-pending-bg',
  statusApproved: '--color-status-approved',
  statusApprovedBg: '--color-status-approved-bg',
  statusRejected: '--color-status-rejected',
  statusRejectedBg: '--color-status-rejected-bg',
  focusRing: '--color-focus-ring',
  overlay: '--color-overlay',
  white: '--color-white',
};

/**
 * Reads a color token's *current* resolved value from the DOM -- meaning it
 * automatically respects whichever theme (light/dark) is active via
 * [data-theme], with zero risk of drifting out of sync with
 * design-tokens.css, because it never stores the value itself.
 *
 * Use this only where a Tailwind class isn't an option -- e.g. Canvas
 * fillStyle in the Waveform component, or an inline SVG fill computed in JS.
 */
export function getColor(token: ColorToken): string {
  if (typeof window === 'undefined') return '';
  const cssVar = tokenToCssVar[token];
  return getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
}
