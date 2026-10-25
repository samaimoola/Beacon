/**
 * Screen-recording footage placed with a simple camera: a point in source pixels
 * (cx, cy) is shown at the window centre, at k video-px per source-px. The
 * footage keeps its native 2940×1912 proportions — it is only scaled, never
 * stretched — and the window crops it.
 */
import React from 'react';
import { OffthreadVideo, staticFile, useVideoConfig } from 'remotion';

export const SRC_W = 2940;
export const SRC_H = 1912;

export type Camera = { cx: number; cy: number; k: number };
export type Win = { x: number; y: number; w: number; h: number };

/** Source pixel → video pixel for a camera inside a window. */
export const project = (cam: Camera, win: Win, sx: number, sy: number) => ({
  x: win.x + win.w / 2 + (sx - cam.cx) * cam.k,
  y: win.y + win.h / 2 + (sy - cam.cy) * cam.k,
});

export const lerpCam = (a: Camera, b: Camera, p: number): Camera => ({
  cx: a.cx + (b.cx - a.cx) * p,
  cy: a.cy + (b.cy - a.cy) * p,
  k: a.k + (b.k - a.k) * p,
});

export const Footage: React.FC<{
  src: string;
  /** Source seconds to start from (one continuous segment). */
  sourceStart: number;
  cam: Camera;
  win: Win;
  filter?: string;
}> = ({ src, sourceStart, cam, win, filter }) => {
  const { fps } = useVideoConfig();
  const tl = project(cam, win, 0, 0);
  return (
    <OffthreadVideo
      src={staticFile(src)}
      muted
      trimBefore={Math.round(sourceStart * fps)}
      style={{
        position: 'absolute',
        left: tl.x - win.x,
        top: tl.y - win.y,
        width: SRC_W * cam.k,
        height: SRC_H * cam.k,
        maxWidth: 'none',
        filter,
      }}
    />
  );
};
