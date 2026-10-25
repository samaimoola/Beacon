/**
 * Every timing in the film, in SECONDS, in one place. Components convert with
 * useVideoConfig().fps, so changing a beat here re-times the clip.
 */
export const INTRO = {
  duration: 6,
  lightOn: [0.2, 1.0], // amber window light appears in the dark
  reveal: [1.2, 3.0], // clouds part, neighborhood fades up
  push: [1.2, 5.6], // slow camera push, settling before the end
  wordmark: [3.0, 3.8],
  slogan: [3.45, 4.35],
  tag: [3.95, 4.6],
  // 4.6 → 6.0: completed composition holds still for reading / the cut.
} as const;

export const REPAIR = {
  duration: 14,
  /** Stage boundaries (seconds). Crew count is the ONLY thing that changes. */
  stages: [
    { crews: 1, from: 0, to: 4 },
    { crews: 2, from: 4, to: 8 },
    { crews: 3, from: 8, to: 11 },
    { crews: 10, from: 11, to: 14 },
  ],
  crossfade: 0.4, // range / crew-count crossfade between stages
  playStart: 0.42, // seconds into each stage before the illustrative schedule plays
  /**
   * Compressed illustrative pace: the 1-crew schedule plays in this many seconds.
   * Every stage uses the same pace, so shorter schedules visibly finish sooner.
   */
  oneCrewPlaySeconds: 2.75,
  headingIn: [0.1, 0.8],
  emphasisAt: 12.15, // heading → "More crews can't skip repair dependencies."
} as const;

export const OUTRO = {
  duration: 5,
  settle: [0, 2.6], // clouds drift apart and settle
  wordmark: [0.7, 1.5],
  slogan: [1.2, 2.1],
  support: [1.8, 2.6],
  // 2.6 → 5.0: stable final frame, with open space for team names.
} as const;

/** Combined preview: fade length between clips (seconds). */
export const PREVIEW_FADE = 0.5;
