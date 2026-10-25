'use client';

import { useRef } from 'react';
import StormScene from '@/components/scene/StormScene';
import { usePauseWhenHidden } from '@/hooks/usePauseWhenHidden';
import { capitalize, type Severity } from '@/lib/scenario';
import { scrollToId } from '@/lib/scroll';

interface HeroProps {
  severity: Severity;
  accessBlocked: boolean;
  crews: number;
}

export default function Hero({ severity, accessBlocked, crews }: HeroProps) {
  const ref = useRef<HTMLElement>(null);
  const paused = usePauseWhenHidden(ref);
  const explore = () => scrollToId('workspace');

  return (
    <section
      id="top"
      ref={ref}
      className="hero grain on-dark"
      data-severity={severity}
      data-paused={paused ? 'true' : 'false'}
      aria-labelledby="hero-title"
    >
      <div className="hero__sky" aria-hidden="true">
        <svg className="hero__strata" viewBox="0 0 1440 900" preserveAspectRatio="none">
          <defs>
            <radialGradient id="strata-g">
              <stop offset="0" stopColor="#bfe3e6" stopOpacity=".22" />
              <stop offset="1" stopColor="#bfe3e6" stopOpacity="0" />
            </radialGradient>
          </defs>
          <ellipse className="band" cx="320" cy="240" rx="520" ry="70" fill="url(#strata-g)" />
          <ellipse className="band b2" cx="1100" cy="170" rx="600" ry="60" fill="url(#strata-g)" />
          <ellipse className="band b3" cx="760" cy="760" rx="900" ry="120" fill="url(#strata-g)" />
        </svg>
        <div className="hero__dim" />
      </div>

      <div className="container-wide grid items-center gap-3 pb-6 pt-3 sm:gap-6 sm:pt-8 lg:grid-cols-12 lg:gap-4 lg:pb-5 lg:pt-8">
        <div className="hero__copy order-2 lg:order-1 lg:col-span-5 relative z-10">
          <p className="flex flex-wrap items-center gap-2">
            <span className="eyebrow text-mist">The Storm Observatory</span>
            <span className="chip chip--proto">Prototype · HackOHI/O 2026</span>
          </p>
          <h1 id="hero-title" className="display-hero mt-5">
            <span className="hero-line">When the lights go out,</span>{' '}
            <span className="hero-line">
              <em>your plan doesn&apos;t</em>
            </span>
          </h1>
          <p className="mt-4 max-w-[34rem] text-[1rem] leading-relaxed text-ivory/85 sm:mt-6 sm:text-[1.06rem]">
            Pick an anonymized household, simulate a storm, and get a calm, readable plan: an outage-risk band, a
            modeled restoration range, and what to prepare.
          </p>
          <p className="mt-3 max-w-[34rem] text-sm leading-relaxed text-mist">
            Network and labor references are real but anonymized. Every storm, damage preset, and notice here is
            simulated — not a forecast, outage report, or AEP commitment.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-3 sm:mt-8">
            <button type="button" className="btn btn--lamp text-base" onClick={explore}>
              Explore my scenario <span className="arrow" aria-hidden="true">↓</span>
            </button>
            <a href="#ask" className="btn btn--glass">
              Ask Beacon AI
            </a>
          </div>
        </div>

        <div className="hero__art order-1 lg:order-2 lg:col-span-7 lg:-mr-6">
          <div className="mx-auto max-w-[min(100%,54svh)] lg:max-w-none">
            <StormScene severity={severity} accessBlocked={accessBlocked} crews={crews} variant="hero" scrollTarget={ref} />
          </div>
          <div className="hero__caption" data-testid="hero-caption">
            <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1.5 sm:gap-x-2 lg:justify-end">
              <span className="chip chip--dark">Illustrative scenario</span>
              <span>Storm: {capitalize(severity)}<span className="hidden sm:inline"> (simulated)</span></span>
              <span aria-hidden="true" className="hidden sm:inline">·</span>
              <span>Access: {accessBlocked ? 'blocked' : 'clear'}</span>
              <span aria-hidden="true" className="hidden sm:inline">·</span>
              <span>Crew markers ×{crews}<span className="hidden sm:inline"> (symbolic)</span></span>
            </div>
            <p className="mt-1.5 text-center text-[0.74rem] leading-snug lg:text-right">
              Not a map, live weather, or outage status. Window lights and power lines are decorative.
            </p>
          </div>
        </div>
      </div>

      <a href="#workspace" className="hero__jump">
        Jump to the workspace <span aria-hidden="true">↓</span>
      </a>
    </section>
  );
}
