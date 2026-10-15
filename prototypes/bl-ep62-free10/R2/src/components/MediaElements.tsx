import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { FONT_ARCHIVO_800, FONT_KANIT_600, FONT_KANIT_800 } from '../fonts';

export type SyncedPresenterProps = {
  /** Exact global composition frame where the parent Sequence starts */
  readonly startFrame: number;
  readonly mode: 'full-frame' | 'card-right' | 'card-left' | 'split-top';
  readonly zoomFrom?: number;
  readonly zoomTo?: number;
  readonly durationInFrames: number;
  readonly label?: string;
};

/**
 * Renders avatar-lipsync-0-10s.mp4 strictly locked to the global composition time.
 * Because the parent <Sequence from={startFrame}> starts at `startFrame`,
 * passing `trimBefore={startFrame}` ensures the video frame at local frame `f`
 * is `startFrame + f === globalFrame`.
 */
export const SyncedPresenter: React.FC<SyncedPresenterProps> = ({
  startFrame,
  mode,
  zoomFrom = 1.04,
  zoomTo = 1.12,
  durationInFrames,
  label = 'BLACK LIQUIDITY · EP.62',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const globalFrame = startFrame + frame;

  const scale = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const enterSpring = spring({
    frame,
    fps,
    config: { damping: 16, stiffness: 180, mass: 0.7 },
  });

  if (mode === 'full-frame') {
    return (
      <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#050507' }}>
        <div
          style={{
            position: 'absolute',
            top: -40,
            left: 0,
            width: 1080,
            height: 1760,
            transform: `scale(${scale})`,
            transformOrigin: '50% 28%',
            filter: 'contrast(1.14) saturate(1.08) brightness(0.92)',
          }}
        >
          <OffthreadVideo
            src={staticFile('avatar-lipsync-0-10s.mp4')}
            muted
            trimBefore={startFrame}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: '50% 18%',
            }}
          />
        </div>
        {/* Editorial dark-crimson grading & vignette so typography pops */}
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(circle at 50% 30%, rgba(255,30,39,0.08) 0%, rgba(5,5,7,0.38) 52%, rgba(5,5,7,0.92) 90%)',
          }}
        />
        <AbsoluteFill
          style={{
            background:
              'linear-gradient(180deg, rgba(5,5,7,0.72) 0%, rgba(5,5,7,0.08) 22%, rgba(5,5,7,0.22) 52%, rgba(5,5,7,0.95) 84%, #050507 100%)',
          }}
        />
      </AbsoluteFill>
    );
  }

  if (mode === 'split-top') {
    return (
      <div
        style={{
          position: 'absolute',
          top: 138,
          left: 48,
          width: 984,
          height: 620,
          borderRadius: 24,
          overflow: 'hidden',
          border: '2px solid rgba(255, 30, 39, 0.65)',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.85), 0 0 40px rgba(255, 30, 39, 0.22)',
          backgroundColor: '#09090D',
          transform: `scale(${interpolate(enterSpring, [0, 1], [0.94, 1])})`,
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            transform: `scale(${scale})`,
            transformOrigin: '50% 24%',
            filter: 'contrast(1.15) saturate(1.08)',
          }}
        >
          <OffthreadVideo
            src={staticFile('avatar-lipsync-0-10s.mp4')}
            muted
            trimBefore={startFrame}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: '50% 20%',
            }}
          />
        </div>
        <AbsoluteFill
          style={{
            background:
              'linear-gradient(180deg, rgba(5,5,7,0.45) 0%, rgba(5,5,7,0) 35%, rgba(5,5,7,0.82) 100%)',
          }}
        />
        {/* Live Voice Waveform HUD on Presenter Frame */}
        <div
          style={{
            position: 'absolute',
            top: 18,
            left: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            backgroundColor: 'rgba(5, 5, 8, 0.82)',
            border: '1px solid rgba(255, 30, 39, 0.6)',
            borderRadius: 999,
            padding: '6px 16px',
          }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: '#FF1E27',
              boxShadow: '0 0 10px #FF1E27',
            }}
          />
          <span
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 18,
              color: '#F8FAFC',
              letterSpacing: 1.2,
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </span>
        </div>
      </div>
    );
  }

  const isRight = mode === 'card-right';
  const cardLeft = isRight ? 548 : 48;
  const cardSlideX = interpolate(enterSpring, [0, 1], [isRight ? 70 : -70, 0]);

  return (
    <div
      style={{
        position: 'absolute',
        top: 156,
        left: cardLeft,
        width: 484,
        height: 670,
        borderRadius: 24,
        overflow: 'hidden',
        border: '2.5px solid rgba(255, 30, 39, 0.8)',
        boxShadow: '0 26px 65px rgba(0,0,0,0.88), 0 0 36px rgba(255, 30, 39, 0.28)',
        backgroundColor: '#08080C',
        transform: `translateX(${cardSlideX}px)`,
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          transform: `scale(${scale})`,
          transformOrigin: '50% 25%',
          filter: 'contrast(1.16) saturate(1.06)',
        }}
      >
        <OffthreadVideo
          src={staticFile('avatar-lipsync-0-10s.mp4')}
          muted
          trimBefore={startFrame}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: '50% 18%',
          }}
        />
      </div>
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(5,5,7,0.35) 0%, rgba(5,5,7,0) 45%, rgba(5,5,7,0.88) 100%)',
        }}
      />
      {/* Bottom mini voice equalizer bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 14,
          left: 16,
          right: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(8, 8, 12, 0.86)',
          border: '1px solid rgba(255, 184, 0, 0.45)',
          borderRadius: 12,
          padding: '8px 14px',
        }}
      >
        <span
          style={{
            fontFamily: FONT_KANIT_600,
            fontSize: 18,
            color: '#FFB800',
            whiteSpace: 'nowrap',
          }}
        >
          {label}
        </span>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 20 }}>
          {[0, 1, 2, 3, 4, 5].map((barIdx) => {
            const barH =
              6 +
              Math.abs(Math.sin(globalFrame * 0.42 + barIdx * 1.15)) * 14;
            return (
              <div
                key={barIdx}
                style={{
                  width: 4,
                  height: barH,
                  borderRadius: 2,
                  backgroundColor: barIdx % 2 === 0 ? '#FF1E27' : '#FFB800',
                }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export type BrollBackgroundProps = {
  readonly file:
    | 'broll/hourglass-red-sand.mp4'
    | 'broll/red-digital-countdown.mp4'
    | 'broll/finger-taps-red-lock.mp4'
    | 'broll/red-forbidden-icon-glow.mp4'
    | 'broll/gold-bar-in-glass-cube.mp4'
    | 'broll/typewriter-red-neon-ticker-tape.mp4'
    | 'broll/contract-signature-wax-seal.mp4';
  readonly trimBefore?: number;
  readonly playbackRate?: number;
  readonly zoomFrom?: number;
  readonly zoomTo?: number;
  readonly durationInFrames: number;
  readonly opacity?: number;
  readonly tint?: 'crimson' | 'gold' | 'obsidian';
};

export const BrollBackground: React.FC<BrollBackgroundProps> = ({
  file,
  trimBefore = 0,
  playbackRate = 1.25,
  zoomFrom = 1.02,
  zoomTo = 1.14,
  durationInFrames,
  opacity = 0.85,
  tint = 'crimson',
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], [zoomFrom, zoomTo], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const overlayGradient =
    tint === 'gold'
      ? 'radial-gradient(circle at 50% 38%, rgba(255, 184, 0, 0.14) 0%, rgba(5, 5, 7, 0.62) 58%, rgba(5, 5, 7, 0.94) 100%)'
      : tint === 'crimson'
      ? 'radial-gradient(circle at 50% 38%, rgba(255, 30, 39, 0.18) 0%, rgba(5, 5, 7, 0.62) 58%, rgba(5, 5, 7, 0.95) 100%)'
      : 'radial-gradient(circle at 50% 38%, rgba(15, 23, 42, 0.25) 0%, rgba(5, 5, 7, 0.72) 58%, rgba(5, 5, 7, 0.96) 100%)';

  return (
    <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#050507' }}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale})`,
          opacity,
          filter: 'contrast(1.18) saturate(1.12)',
        }}
      >
        <OffthreadVideo
          src={staticFile(file)}
          muted
          trimBefore={trimBefore}
          playbackRate={playbackRate}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: overlayGradient }} />
    </AbsoluteFill>
  );
};

export type PostEvidenceCardProps = {
  readonly variant: 'claim' | 'account';
  readonly top: number;
  readonly left?: number;
  readonly width?: number;
  readonly rotateDeg?: number;
  /** Y offset inside the 420px cropped white band for the animated highlighter */
  readonly highlightTop: number;
  readonly highlightHeight?: number;
  readonly highlightDelay?: number;
  readonly highlightColor?: string;
  readonly badgeText?: string;
};

/**
 * Displays stills/cxm-post-claim.png or stills/cxm-post-account.png
 * cropped cleanly to the white post text band (y: 745..1165 of the 1080x1920 image).
 * Never un-blurs, sharpens, or zooms onto any blurred profile header.
 */
export const PostEvidenceCard: React.FC<PostEvidenceCardProps> = ({
  variant,
  top,
  left = 48,
  width = 884,
  rotateDeg = -1.2,
  highlightTop,
  highlightHeight = 48,
  highlightDelay = 3,
  highlightColor = 'rgba(255, 30, 39, 0.26)',
  badgeText = 'โพสต์ต้นทาง · ตามที่เจ้าของโพสต์เล่า',
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pop = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 210, mass: 0.65 },
  });

  const highlightProgress = interpolate(
    frame,
    [highlightDelay, highlightDelay + 12],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }
  );

  const scaleFactor = width / 1080;
  const bandSourceY = 748;
  const bandSourceHeight = 420;
  const cardBodyHeight = Math.round(bandSourceHeight * scaleFactor);

  const src =
    variant === 'claim'
      ? staticFile('stills/cxm-post-claim.png')
      : staticFile('stills/cxm-post-account.png');

  return (
    <div
      style={{
        position: 'absolute',
        top,
        left,
        width,
        transform: `translateY(${interpolate(pop, [0, 1], [42, 0])}px) scale(${interpolate(
          pop,
          [0, 1],
          [0.92, 1]
        )}) rotate(${rotateDeg}deg)`,
        transformOrigin: '50% 50%',
        borderRadius: 20,
        overflow: 'hidden',
        border: '3px solid #FF1E27',
        boxShadow:
          '0 28px 65px rgba(0, 0, 0, 0.9), 0 0 38px rgba(255, 30, 39, 0.35)',
        backgroundColor: '#FFFFFF',
      }}
    >
      {/* Top Evidence Dossier Bar */}
      <div
        style={{
          height: 42,
          backgroundColor: '#0B0B10',
          borderBottom: '2px solid #FF1E27',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 18px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: '#FF1E27',
            }}
          />
          <span
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 20,
              color: '#F8FAFC',
              whiteSpace: 'nowrap',
            }}
          >
            {badgeText}
          </span>
        </div>
        <span
          style={{
            fontFamily: FONT_ARCHIVO_800,
            fontSize: 16,
            color: '#FFB800',
            letterSpacing: 1.5,
            whiteSpace: 'nowrap',
          }}
        >
          EVIDENCE // FB POST
        </span>
      </div>

      {/* Cropped White Band from Original Still (untouched pixels, no sharpen/unblur) */}
      <div
        style={{
          position: 'relative',
          width,
          height: cardBodyHeight,
          overflow: 'hidden',
          backgroundColor: '#FFFFFF',
        }}
      >
        <Img
          src={src}
          style={{
            position: 'absolute',
            top: -Math.round(bandSourceY * scaleFactor),
            left: 0,
            width,
            height: Math.round(1920 * scaleFactor),
          }}
        />
        {/* Animated Red/Gold Marker Highlight Sweep */}
        <div
          style={{
            position: 'absolute',
            top: highlightTop,
            left: 16,
            width: Math.round((width - 32) * highlightProgress),
            height: highlightHeight,
            backgroundColor: highlightColor,
            borderLeft: '8px solid #FF1E27',
            borderBottom: '3px solid rgba(255, 30, 39, 0.85)',
            borderRadius: 6,
            boxShadow: '0 4px 16px rgba(255, 30, 39, 0.18)',
          }}
        />
      </div>
    </div>
  );
};
