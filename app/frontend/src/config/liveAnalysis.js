const DEFAULT_DISPLAY_TARGET_DEPTH = 10;
const DEFAULT_WORKER_TARGET_DEPTH = 70;
const DEFAULT_DISPLAY_LAG_DEPTH = 2;
const MAX_ANALYSIS_DEPTH = 70;
const MAX_DISPLAY_LAG_DEPTH = 10;

function clampInteger(value, fallback, minimum, maximum) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) {
    return fallback;
  }

  return Math.max(minimum, Math.min(parsed, maximum));
}

const configuredDisplayTargetDepth = clampInteger(
  import.meta.env.VITE_LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
  DEFAULT_DISPLAY_TARGET_DEPTH,
  1,
  MAX_ANALYSIS_DEPTH,
);

export const LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH = configuredDisplayTargetDepth;
export const LIVE_ANALYSIS_WORKER_TARGET_DEPTH = Math.max(
  configuredDisplayTargetDepth,
  clampInteger(
    import.meta.env.VITE_LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
    DEFAULT_WORKER_TARGET_DEPTH,
    1,
    MAX_ANALYSIS_DEPTH,
  ),
);
export const LIVE_ANALYSIS_DISPLAY_LAG_DEPTH = clampInteger(
  import.meta.env.VITE_LIVE_ANALYSIS_DISPLAY_LAG_DEPTH,
  DEFAULT_DISPLAY_LAG_DEPTH,
  0,
  MAX_DISPLAY_LAG_DEPTH,
);
