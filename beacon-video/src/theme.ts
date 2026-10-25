/**
 * Beacon visual system, copied from the app's design tokens
 * (frontend/src/app/globals.css and tailwind.config.js) so the film and the
 * product read as one identity.
 */
export const C = {
  storm950: '#08191d',
  storm900: '#0d2429',
  storm800: '#123137',
  storm700: '#1a4047',
  storm600: '#24545a',
  storm500: '#336a6e',
  night: '#050f12',
  ivory: '#f6f1e6',
  ivory200: '#ece4d2',
  ink: '#1b2829',
  seaglass: '#8fb9a8',
  seaglassDeep: '#3d6d60',
  mist: '#bfe3e6',
  mistDeep: '#7fc0c7',
  lamp: '#f2b45a',
  lampWarm: '#f6c76c',
  lampDeep: '#8a520c',
  line: '#21393a',
} as const;

export const FONT_DISPLAY = "'Fraunces', Georgia, serif";
export const FONT_UI = "'Inter', system-ui, -apple-system, sans-serif";

/** Fraunces as the site sets it: high optical size, soft terminals. */
export const displayVariation = (soft = 60): string => `'opsz' 144, 'SOFT' ${soft}`;

/** The site's hero sky (.hero__sky), used as the film's base atmosphere. */
export const HERO_SKY =
  'radial-gradient(60% 55% at 70% 60%, rgba(191, 227, 230, 0.26), transparent 70%),' +
  'radial-gradient(40% 30% at 18% 14%, rgba(143, 185, 168, 0.14), transparent 70%),' +
  'linear-gradient(180deg, #0a2126 0%, #12343a 38%, #1f4d52 72%, #2f6363 100%)';

/** Darker variant for the explainer (matches the app's concierge section). */
export const DEEP_SKY =
  'radial-gradient(55% 60% at 30% 55%, rgba(191, 227, 230, 0.09), transparent 70%),' +
  'radial-gradient(40% 40% at 85% 30%, rgba(242, 180, 90, 0.06), transparent 70%),' +
  'linear-gradient(180deg, #0a1f24 0%, #0d2429 45%, #11303a 100%)';

export const VIDEO = { width: 1920, height: 1080, fps: 30 } as const;
