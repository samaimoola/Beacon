'use client';

import { useEffect, useState, type RefObject } from 'react';

/**
 * True when the element is offscreen or the tab is hidden. Used to pause
 * decorative CSS animation (via a data-paused attribute) to save battery.
 * Starts `false` on both server and client to avoid hydration mismatches.
 */
export function usePauseWhenHidden(ref: RefObject<Element>, rootMargin = '160px'): boolean {
  const [inView, setInView] = useState(true);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) setInView(e.isIntersecting);
      },
      { rootMargin }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, rootMargin]);

  useEffect(() => {
    const sync = () => setHidden(document.visibilityState === 'hidden');
    sync();
    document.addEventListener('visibilitychange', sync);
    return () => document.removeEventListener('visibilitychange', sync);
  }, []);

  return !inView || hidden;
}
