/**
 * Combined preview: intro → repair dependencies → outro, with short fades.
 * For reviewing pacing only; deliver the three individual clips to CapCut.
 */
import React from 'react';
import { useVideoConfig } from 'remotion';
import { linearTiming, TransitionSeries } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { BeaconIntro } from './BeaconIntro';
import { BeaconOutro } from './BeaconOutro';
import { RepairDependencies } from './RepairDependencies';
import { INTRO, OUTRO, PREVIEW_FADE, REPAIR } from './timing';

export const BeaconPreview: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence name="Intro" durationInFrames={INTRO.duration * fps}>
        <BeaconIntro />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: PREVIEW_FADE * fps })} />
      <TransitionSeries.Sequence name="Repair dependencies" durationInFrames={REPAIR.duration * fps}>
        <RepairDependencies />
      </TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: PREVIEW_FADE * fps })} />
      <TransitionSeries.Sequence name="Outro" durationInFrames={OUTRO.duration * fps}>
        <BeaconOutro />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};

/** Total preview length: the clips minus the two fade overlaps. */
export const previewSeconds = INTRO.duration + REPAIR.duration + OUTRO.duration - 2 * PREVIEW_FADE;
