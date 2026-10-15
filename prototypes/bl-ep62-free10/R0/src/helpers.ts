import { Easing, interpolate, spring } from 'remotion';

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const DURATION_FRAMES = 300;

// TikTok safe zone constants:
// Right edge (x > 960 below y 960) and bottom (y > 1500) are covered by TikTok UI.
export const SAFE_LEFT = 48;
export const SAFE_RIGHT = 936;
export const SAFE_WIDTH = SAFE_RIGHT - SAFE_LEFT; // 888px
export const SAFE_TOP = 64;
export const SAFE_BOTTOM = 1484;

export const COLORS = {
  bgDark: '#060609',
  bgPanel: '#0D0E14',
  crimson: '#E6192E',
  crimsonBright: '#FF243B',
  crimsonDark: '#6E0712',
  gold: '#FFD166',
  goldBright: '#FFE484',
  amber: '#FF9F1C',
  cyberWhite: '#F8F9FA',
  silver: '#B8BDC9',
  neonCyan: '#00F0FF',
  warningYellow: '#FFE600',
};

/**
 * Deterministic seeded PRNG in [0, 1)
 */
export const seeded = (seed: number): number => {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453123;
  return x - Math.floor(x);
};

/**
 * Deterministic 2D camera shake decaying over `duration` frames from `triggerFrame`
 */
export const getImpactShake = (
  frame: number,
  triggerFrame: number,
  intensity = 18,
  duration = 8
): { x: number; y: number; rotate: number } => {
  const local = frame - triggerFrame;
  if (local < 0 || local >= duration) {
    return { x: 0, y: 0, rotate: 0 };
  }
  const decay = interpolate(local, [0, duration], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const rx = (seeded(frame * 17 + triggerFrame) - 0.5) * 2 * intensity * decay;
  const ry = (seeded(frame * 31 + triggerFrame * 3) - 0.5) * 2 * intensity * decay;
  const rot = (seeded(frame * 47 + triggerFrame * 7) - 0.5) * 1.8 * decay;
  return { x: rx, y: ry, rotate: rot };
};

/**
 * Punchy spring scale for kinetic typography slams (overshoots then settles to 1.0)
 */
export const slamScale = (
  frame: number,
  startFrame: number,
  fromScale = 1.65
): number => {
  const s = spring({
    frame: frame - startFrame,
    fps: FPS,
    config: {
      damping: 11,
      stiffness: 240,
      mass: 0.65,
    },
  });
  return interpolate(s, [0, 1], [fromScale, 1]);
};

/**
 * Fast pop-in from 0.4 -> 1.0 with bounce
 */
export const popScale = (frame: number, startFrame: number): number => {
  if (frame < startFrame) return 0;
  const s = spring({
    frame: frame - startFrame,
    fps: FPS,
    config: {
      damping: 12,
      stiffness: 260,
      mass: 0.55,
    },
  });
  return interpolate(s, [0, 1], [0.35, 1]);
};

/**
 * Quick opacity fade-in over `dur` frames
 */
export const fadeIn = (frame: number, startFrame: number, dur = 4): number => {
  return interpolate(frame, [startFrame, startFrame + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

/**
 * Smooth slide offset with cubic out easing
 */
export const slideOffset = (
  frame: number,
  startFrame: number,
  fromPx = 56,
  dur = 7
): number => {
  return interpolate(frame, [startFrame, startFrame + dur], [fromPx, 0], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

/**
 * Format integer with commas (e.g. 5,999,999)
 */
export const formatNumber = (n: number): string => {
  return Math.floor(n).toLocaleString('en-US');
};
