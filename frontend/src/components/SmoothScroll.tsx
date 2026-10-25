'use client';

/**
 * SmoothScroll — the single scrolling implementation (Lenis).
 *
 *  - Wheel scrolling gets a short, responsive ease (lerp 0.14). Touch and keyboard
 *    stay fully native (syncTouch is off; Lenis never intercepts key events).
 *  - Nested scrollers (chat log, notice text, <select> popups) keep normal scrolling
 *    via allowNestedScroll + [data-lenis-prevent].
 *  - Skipped entirely under prefers-reduced-motion (and re-evaluated if it changes).
 *  - The frame loop runs ON DEMAND (while input/animation is active), not forever, so
 *    an idle page costs nothing.
 *  - In-page links (#id) get smooth, header-aware scrolling AND a history entry, so
 *    Back works. Direct links to /#section are handled by the browser; scroll-padding
 *    (kept in sync with the real sticky height) keeps headings visible.
 *  - Pure scrolling: no state resets, scenario evaluation, or provider calls.
 */
import { useEffect } from 'react';
import Lenis from 'lenis';
import { registerScroller, scrollToId, stickyOffset } from '@/lib/scroll';

const IDLE_GRACE_MS = 260;

export default function SmoothScroll() {
  // Keep CSS scroll-padding in sync with the sticky header + any alert banner.
  useEffect(() => {
    const root = document.documentElement;
    const sync = () => root.style.setProperty('--scroll-offset', `${stickyOffset()}px`);
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(document.body);
    window.addEventListener('resize', sync);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', sync);
    };
  }, []);

  // In-page anchor links: smooth, header-aware, and history-friendly.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.('a[href^="#"]') as HTMLAnchorElement | null;
      if (!a) return;
      const id = decodeURIComponent(a.getAttribute('href')!.slice(1));
      if (!id || !document.getElementById(id)) return;
      e.preventDefault();
      if (window.location.hash !== `#${id}`) window.history.pushState(null, '', `#${id}`);
      scrollToId(id);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);

  // Lenis itself — only when motion is allowed.
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    let lenis: Lenis | null = null;
    let raf = 0;
    let lastActive = 0;
    const cleanups: Array<() => void> = [];

    const tick = (t: number) => {
      lenis?.raf(t);
      if (lenis && (lenis.isScrolling || performance.now() - lastActive < IDLE_GRACE_MS)) {
        raf = requestAnimationFrame(tick);
      } else {
        raf = 0;
      }
    };
    const wake = () => {
      lastActive = performance.now();
      if (!raf && lenis) raf = requestAnimationFrame(tick);
    };

    const start = () => {
      if (lenis || mq.matches) return;
      lenis = new Lenis({
        autoRaf: false,
        lerp: 0.14,
        wheelMultiplier: 1,
        smoothWheel: true,
        syncTouch: false,
        allowNestedScroll: true,
      });
      registerScroller(lenis, wake);
      const onWheel = () => wake();
      const onScroll = () => wake();
      window.addEventListener('wheel', onWheel, { passive: true });
      window.addEventListener('scroll', onScroll, { passive: true });
      cleanups.push(
        () => window.removeEventListener('wheel', onWheel),
        () => window.removeEventListener('scroll', onScroll)
      );
    };

    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
      cleanups.splice(0).forEach((fn) => fn());
      registerScroller(null, null);
      lenis?.destroy();
      lenis = null;
    };

    const onMotionPref = () => (mq.matches ? stop() : start());
    start();
    mq.addEventListener('change', onMotionPref);
    return () => {
      mq.removeEventListener('change', onMotionPref);
      stop();
    };
  }, []);

  return null;
}
