'use client';

import { useEffect, useState } from 'react';
import type { Connection } from '@/hooks/useStormReady';

const LINKS = [
  { id: 'workspace', label: 'Scenario' },
  { id: 'reading', label: 'Reading' },
  { id: 'ask', label: 'Ask AI' },
  { id: 'notices', label: 'Notices' },
];

export function Logo({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <circle cx="20" cy="20" r="19" fill="#123137" stroke="#bfe3e6" strokeOpacity=".35" />
      <path d="M9 17c0-3 2.4-5.4 5.4-5.4 1-2.4 3.3-4 6-4 3.6 0 6.5 2.9 6.5 6.5h.3c2.4 0 4.3 1.9 4.3 4.3H9z" fill="#bfe3e6" />
      <path d="M13 31v-7l7-5.5 7 5.5v7z" fill="#f6f1e6" />
      <rect x="18.3" y="25" width="3.4" height="4" rx=".6" fill="#f2b45a" />
      <path d="M10 33h20" stroke="#8fb9a8" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function StatusPill({ connection, backend }: { connection: Connection; backend: string | null }) {
  let color = '#bfe3e6';
  let label = 'Connecting to engine…';
  let short = 'Connecting';
  if (connection === 'offline') {
    color = '#e0735f';
    label = 'Engine disconnected';
    short = 'Offline';
  } else if (connection === 'online' && backend === 'demo') {
    color = '#f2b45a';
    label = 'Synthetic demo data';
    short = 'Synthetic';
  } else if (connection === 'online') {
    color = '#8fb9a8';
    label = 'Engine · anonymized network data';
    short = 'Engine';
  }
  return (
    <span
      className="chip chip--dark"
      role="status"
      aria-live="polite"
      title={label}
      style={{ borderColor: `${color}55` }}
    >
      <span className="dot" style={{ background: color }} />
      <span className="hidden md:inline">{label}</span>
      <span className="md:hidden">{short}</span>
    </span>
  );
}

export default function Nav({ connection, backend }: { connection: Connection; backend: string | null }) {
  const [scrolled, setScrolled] = useState(false);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const onScroll = () => {
      const s = window.scrollY > 24;
      setScrolled((prev) => (prev === s ? prev : s));
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id);
      },
      { rootMargin: '-40% 0px -55% 0px' }
    );
    LINKS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, []);

  return (
    <header className="nav on-dark" data-sticky-top data-scrolled={scrolled ? 'true' : 'false'}>
      <div className="container-wide flex items-center gap-3">
        <a href="#top" className="flex items-center gap-2.5 shrink-0" aria-label="Beacon, back to top">
          <Logo className="h-8 w-8" />
          <span className="hidden font-display text-[1.28rem] tracking-tight sm:inline" style={{ fontWeight: 500 }}>
            Beacon
          </span>
        </a>
        <nav aria-label="Sections" className="min-w-0 flex-1">
          <ul className="nav__links flex items-center justify-start gap-0.5 overflow-x-auto sm:justify-center">
            {LINKS.map((l) => (
              <li key={l.id}>
                <a href={`#${l.id}`} aria-current={active === l.id ? 'true' : undefined}>
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="shrink-0">
          <StatusPill connection={connection} backend={backend} />
        </div>
      </div>
    </header>
  );
}
