import React from 'react';
import { Composition, Folder } from 'remotion';
import { BeaconIntro } from './BeaconIntro';
import { BeaconOutro } from './BeaconOutro';
import { BeaconPreview, previewSeconds } from './BeaconPreview';
import { RepairDependencies } from './RepairDependencies';
import { INTRO, OUTRO, REPAIR } from './timing';
import { ConciergeReceives } from './overlays/ConciergeReceives';
import { DistinctionMatters } from './overlays/DistinctionMatters';
import { CONCIERGE, DISTINCTION, framesFor } from './overlays/timing';

const HD = { fps: 30, width: 1920, height: 1080 } as const;

// 1920×1080 · 30 fps · silent. Durations come from src/timing.ts (seconds).
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Folder name="Beacon-clips">
        <Composition id="BeaconIntro" component={BeaconIntro} durationInFrames={INTRO.duration * 30} fps={30} width={1920} height={1080} />
        <Composition
          id="RepairDependencies"
          component={RepairDependencies}
          durationInFrames={REPAIR.duration * 30}
          fps={30}
          width={1920}
          height={1080}
        />
        <Composition id="BeaconOutro" component={BeaconOutro} durationInFrames={OUTRO.duration * 30} fps={30} width={1920} height={1080} />
      </Folder>
      {/* Overlay clips: same visuals; the *Narrated variants add the supplied M4A for timing review. */}
      <Folder name="Beacon-overlays">
        <Composition
          id="ConciergeReceives"
          component={ConciergeReceives}
          durationInFrames={framesFor(CONCIERGE.audioSeconds)}
          defaultProps={{ narration: false }}
          {...HD}
        />
        <Composition
          id="ConciergeReceivesNarrated"
          component={ConciergeReceives}
          durationInFrames={framesFor(CONCIERGE.audioSeconds)}
          defaultProps={{ narration: true }}
          {...HD}
        />
        <Composition
          id="DistinctionMatters"
          component={DistinctionMatters}
          durationInFrames={framesFor(DISTINCTION.audioSeconds)}
          defaultProps={{ narration: false }}
          {...HD}
        />
        <Composition
          id="DistinctionMattersNarrated"
          component={DistinctionMatters}
          durationInFrames={framesFor(DISTINCTION.audioSeconds)}
          defaultProps={{ narration: true }}
          {...HD}
        />
      </Folder>
      <Composition
        id="BeaconPreview"
        component={BeaconPreview}
        durationInFrames={Math.round(previewSeconds * 30)}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
