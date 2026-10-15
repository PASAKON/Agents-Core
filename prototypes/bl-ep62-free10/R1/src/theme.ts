// BLACK LIQUIDITY — Measured Kit Constants & Deterministic Motion Helpers

export const BL = {
  ink: '#07080A',
  red: '#E0202F',
  neon: '#FF2D40',
  yellow: '#F4DF14',
  white: '#F4F6F7',
  muted: '#98A0A8',
  gold: '#FFD84D',
  scrim: 'rgba(10, 11, 13, 0.84)',
  capBg: 'rgba(5, 6, 8, 0.90)',
  legalBg: 'rgba(7, 8, 10, 0.90)',
  glowS: '0 0 10px rgba(255, 45, 64, 0.65), 0 0 22px rgba(224, 32, 47, 0.38)',
  glowM: '0 0 14px rgba(255, 45, 64, 0.85), 0 0 34px rgba(224, 32, 47, 0.55)',
  glowL: '0 0 20px rgba(255, 45, 64, 0.95), 0 0 48px rgba(224, 32, 47, 0.75), 0 0 84px rgba(224, 32, 47, 0.40)',
  textGlowNeon:
    '0 0 14px rgba(255, 45, 64, 0.90), 0 0 32px rgba(224, 32, 47, 0.60), -2px -2px 0 #07080A, 2px -2px 0 #07080A, -2px 2px 0 #07080A, 2px 2px 0 #07080A, 0 4px 12px rgba(0, 0, 0, 0.95)',
  textGlowYellow:
    '0 0 16px rgba(244, 223, 20, 0.55), -2px -2px 0 #07080A, 2px -2px 0 #07080A, -2px 2px 0 #07080A, 2px 2px 0 #07080A, 0 4px 12px rgba(0, 0, 0, 0.95)',
  textOutline:
    '-2px -2px 0 #07080A, 2px -2px 0 #07080A, -2px 2px 0 #07080A, 2px 2px 0 #07080A, 0 4px 14px rgba(0, 0, 0, 0.92)',
  safeLeft: 120,
  safeTop: 252,
  safeRightWide: 120, // x <= 960 when y < 900
  safeRightNarrow: 240, // x <= 840 when y >= 900
  safeBottom: 1500,
} as const;

export const clamp01 = (v: number): number => Math.max(0, Math.min(1, v));

// Measured BLACK LIQUIDITY reveal curve: expo.out
export const expoOut = (t: number): number => {
  const c = clamp01(t);
  return c === 1 ? 1 : 1 - Math.pow(2, -10 * c);
};

// Measured composite shrink curve: sine.out
export const sineOut = (t: number): number => {
  const c = clamp01(t);
  return Math.sin((c * Math.PI) / 2);
};

// Measured hook slide curve: power1.out / quad out
export const power1Out = (t: number): number => {
  const c = clamp01(t);
  return 1 - (1 - c) * (1 - c);
};

export const progress = (frame: number, startFrame: number, durationFrames: number): number => {
  if (durationFrames <= 0) return frame >= startFrame ? 1 : 0;
  return clamp01((frame - startFrame) / durationFrames);
};

export const expoProgress = (frame: number, startFrame: number, durationFrames: number): number =>
  expoOut(progress(frame, startFrame, durationFrames));

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

// Left-to-right clip-path wipe per BL-KIT motion grammar
export const wipeClip = (frame: number, startFrame: number, durationFrames = 10): string => {
  const p = expoProgress(frame, startFrame, durationFrames);
  const rightInset = ((1 - p) * 100).toFixed(2);
  return `inset(-12% ${rightInset}% -12% -4%)`;
};

// Deterministic seeded pseudo-random in [0, 1)
export const seeded = (seed: number): number => {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};
