/**
 * Shared scroll helpers. There is exactly ONE smooth-scroll implementation
 * (Lenis, mounted by <SmoothScroll/>). Everything that needs to move the page —
 * nav links, hero buttons, the "jump" link — goes through scrollToId() so CSS and
 * JavaScript scroll animations never compete.
 *
 * When Lenis isn't active (reduced motion, or before hydration) scrolling is the
 * browser's normal instant behavior.
 */
import type Lenis from 'lenis';

let instance: Lenis | null = null;
let kick: (() => void) | null = null;

/** Called by <SmoothScroll/> on mount/unmount. */
export function registerScroller(lenis: Lenis | null, wake: (() => void) | null) {
  instance = lenis;
  kick = wake;
}

/** Wake the on-demand frame loop (no-op without Lenis). */
export function wakeScroller() {
  kick?.();
}

/** Height (px) of sticky chrome at the top of the viewport, plus breathing room. */
export function stickyOffset(): number {
  let bottom = 0;
  document.querySelectorAll<HTMLElement>('[data-sticky-top]').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.height > 0) bottom = Math.max(bottom, r.bottom);
  });
  return Math.round(bottom + 12);
}

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Scroll to a section by id, landing it just below the sticky header(s).
 * Moves focus to the section's heading (if it has tabindex=-1) without scrolling again.
 */
export function scrollToId(id: string, { focus = true }: { focus?: boolean } = {}) {
  const el = document.getElementById(id);
  if (!el) return;
  const offset = id === 'top' ? 0 : stickyOffset();
  // Absolute target computed once, so landing never depends on CSS scroll-padding
  // (Lenis would otherwise subtract it a second time).
  const y = Math.max(0, Math.round(el.getBoundingClientRect().top + window.scrollY - offset));
  if (instance && !prefersReducedMotion()) {
    instance.scrollTo(y, { duration: 1.05, easing: (t) => 1 - Math.pow(1 - t, 4) });
    kick?.();
  } else {
    window.scrollTo({ top: y, behavior: 'auto' });
  }
  if (focus) {
    const heading = el.querySelector<HTMLElement>('[tabindex="-1"]') ?? (el.getAttribute('tabindex') === '-1' ? el : null);
    if (heading) window.setTimeout(() => heading.focus({ preventScroll: true }), prefersReducedMotion() ? 0 : 500);
  }
}
