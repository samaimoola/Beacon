/**
 * Pure helpers over the engine export (src/data/repair-demo.json). Nothing here
 * invents numbers: restoration ranges are shown exactly as exported, and job
 * states come from the engine-matched schedule timeline for each crew count.
 */
import data from '../data/repair-demo.json';

export type JobId = 'poleA' | 'condA' | 'poleB' | 'condB' | 'xfmr';
export type IconKind = 'pole' | 'conductor' | 'transformer';

export type Job = {
  id: JobId;
  label: string;
  icon: IconKind;
  depends_on: JobId[];
};

export type Stage = {
  crews: number;
  restoration_window: string;
  dependency_limited: boolean;
  schedule_hours: number;
  critical_path_hours: number;
  timeline: { job: JobId; start: number; end: number }[];
};

export const JOBS = data.jobs as Job[];
export const STAGES = data.stages as Stage[];
export const SCENARIO = data.scenario;
export const MAX_SCHEDULE = Math.max(...STAGES.map((s) => s.schedule_hours));

export const stageFor = (crews: number): Stage => {
  const s = STAGES.find((x) => x.crews === crews);
  if (!s) throw new Error(`No engine stage for ${crews} crews — re-run scripts/export_engine_data.py`);
  return s;
};

export type JobState =
  | { kind: 'waiting-dep'; on: JobId }
  | { kind: 'waiting-crew' }
  | { kind: 'working'; progress: number }
  | { kind: 'done' };

const jobLabel = (id: JobId) => JOBS.find((j) => j.id === id)!.label;

/** State of one job at schedule time `h` (hours on the engine-matched timeline). */
export const jobState = (stage: Stage, id: JobId, h: number): JobState => {
  const slot = stage.timeline.find((x) => x.job === id)!;
  if (h >= slot.end - 1e-9) return { kind: 'done' };
  if (h >= slot.start - 1e-9 && h > 0) return { kind: 'working', progress: (h - slot.start) / (slot.end - slot.start) };
  if (h === 0 && slot.start === 0) return { kind: 'waiting-crew' };
  const job = JOBS.find((j) => j.id === id)!;
  const blocked = job.depends_on.find((d) => {
    const ds = stage.timeline.find((x) => x.job === d)!;
    return h < ds.end - 1e-9;
  });
  return blocked ? { kind: 'waiting-dep', on: blocked } : { kind: 'waiting-crew' };
};

export const statusText = (st: JobState): string => {
  switch (st.kind) {
    case 'waiting-dep':
      // "Replace pole A" -> "pole A"
      return `Waits for ${jobLabel(st.on).replace(/^Replace (\w)/, (_m, c: string) => c.toLowerCase())}`;
    case 'waiting-crew':
      return 'Waiting for a crew';
    case 'working':
      return 'Crew working';
    case 'done':
      return 'Done';
  }
};

/** Jobs being worked at time h (never exceeds the stage's crews — asserted below). */
export const workingCount = (stage: Stage, h: number) =>
  stage.timeline.filter((x) => h > 0 && h >= x.start - 1e-9 && h < x.end - 1e-9).length;

export const maxConcurrent = (stage: Stage) => {
  const edges = stage.timeline.flatMap((x) => [x.start, x.end]);
  return Math.max(...edges.map((e) => stage.timeline.filter((x) => e >= x.start && e < x.end).length));
};

for (const s of STAGES) {
  if (maxConcurrent(s) > s.crews) throw new Error(`Timeline for ${s.crews} crews exceeds its crews`);
}

const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
const cap = (w: string) => w[0].toUpperCase() + w.slice(1);

/** One short, data-derived line about how the crews are used in a stage. */
export const crewNote = (stage: Stage): string => {
  const m = maxConcurrent(stage);
  if (stage.crews === 1) return 'One crew works one job at a time.';
  if (m === stage.crews) return `${cap(WORDS[m])} jobs can run at the same time.`;
  // True for the whole stage: peak concurrency is below the crew count.
  return `At most ${WORDS[m]} jobs are ever ready at once.`;
};
