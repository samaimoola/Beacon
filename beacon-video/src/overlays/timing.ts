/**
 * Overlay timing, in seconds. Edit these numbers to re-time the overlays —
 * nothing else in the compositions hard-codes a time.
 *
 * How the defaults were chosen (initial pass, not verified by listening):
 * - Durations are ffprobe-measured from the supplied M4A files.
 * - Sentence boundaries are estimates from pauses in the narration's RMS
 *   energy (20 ms windows). No transcription was used, so word-level timing
 *   inside a sentence is approximate. Check alignment in the narrated previews.
 * - Source trims were measured frame-by-frame: the macOS recording dimming
 *   starts at 22.483 s (concierge) and 20.367 s (distinction) in the originals.
 */

export const CONCIERGE = {
  video: 'source/concierge receives.mov',
  audio: 'source/concierge receives.m4a',
  audioSeconds: 19.093,
  /** Source seconds where playback starts. Plays continuously to ~19.1 s (dimming at 22.483 s). */
  sourceStart: 0,

  // Estimated narration: S1 ≈ 1.0–6.1 s · S2 ≈ 6.6–13.2 s · S3 ≈ 13.8–18.7 s
  // (energy dips inside S2 at ≈ 7.4, 8.5, 9.5, 10.9 s; inside S3 at ≈ 16.5 s).
  stage1: { in: 0.35, out: 6.2 },
  /** "The concierge receives" → node; "selected set of scenario information"; "and calculated results". */
  explanation: 1.0,
  scenario: 2.45,
  results: 4.85,
  explanationLit: 5.45,

  stage2: { in: 6.5, out: 13.25 },
  /** Raw addresses · Meter identifiers · Employee details · Precise coordinates. */
  excluded: [6.75, 7.6, 8.7, 9.75] as const,

  stage3: { in: 13.7 },
  engineLine: 13.85,
  conciergeLine: 14.4,
  /** "…with the source and limitations visible." */
  support: 16.85,
} as const;

export const DISTINCTION = {
  video: 'source/distinction matters.mov',
  audio: 'source/distinction matters.m4a',
  audioSeconds: 17.643,
  /**
   * Once playing, output t shows source t + sourceOffset (one continuous
   * segment, no cuts, ending at source ≈ 19.667 s; dimming starts at 20.367 s).
   * Crew clicks run source 12.1–17.8 s → output 10.1–15.8 s, in real time.
   */
  sourceOffset: 2.0,
  /**
   * Source 4.0–11.1 s has the recording cursor and text-selection highlights on
   * "High" and on the range numbers. The opening therefore holds the clean,
   * unchanged frame at this source time (10 crews, 21.4–36.0 h, High) until
   * playback reaches it at output holdSource − sourceOffset = 9.5 s.
   */
  holdSource: 11.5,

  // Estimated narration: S1 0.58–2.26 · S2 2.76–5.78 · S3 6.42–9.54 · S4 10.00–14.56 · S5 15.22–17.24
  title: 0.3,
  /** Footage dims behind the opening title, then clears. */
  footageClear: [1.5, 2.55] as const,
  /** During "Overhead service and storm severity affect the risk band." */
  risk: 2.9,
  /** During "Crew availability and blocked access affect restoration." */
  repair: 6.55,
  /** "The interface keeps those explanations separate." — gentle pull-back reveals both explanation headings. */
  pullBack: [15.25, 16.75] as const,
} as const;

export const framesFor = (seconds: number, fps = 30) => Math.ceil(seconds * fps - 1e-6);
