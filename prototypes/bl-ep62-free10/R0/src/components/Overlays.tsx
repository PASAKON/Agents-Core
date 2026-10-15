import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
} from 'remotion';
import { FONT_ARCHIVO_800, FONT_KANIT_600 } from '../fonts';
import {
  COLORS,
  SAFE_LEFT,
  SAFE_WIDTH,
  seeded,
} from '../helpers';

interface SyncedAvatarProps {
  shotStartFrame: number;
  shotDuration: number;
  frame: number;
  style?: React.CSSProperties;
  videoScale?: number;
  videoOffsetY?: number;
  borderColor?: string;
  label?: string;
  showWaveform?: boolean;
}

/**
 * Renders avatar-lipsync-0-10s.mp4 strictly synced to global timeline time:
 * Sequence starts at `shotStartFrame` and OffthreadVideo has `startFrom={shotStartFrame}`,
 * so at global frame F, media frame is (F - shotStartFrame) + shotStartFrame === F.
 */
export const SyncedAvatar: React.FC<SyncedAvatarProps> = ({
  shotStartFrame,
  shotDuration,
  frame,
  style,
  videoScale = 1.08,
  videoOffsetY = 0,
  borderColor = COLORS.crimson,
  label = 'BLACK LIQUIDITY · EP.62',
  showWaveform = true,
}) => {
  return (
    <div
      style={{
        position: 'absolute',
        overflow: 'hidden',
        borderRadius: 20,
        border: `3px solid ${borderColor}`,
        boxShadow: `0 18px 50px rgba(0, 0, 0, 0.85), 0 0 28px ${borderColor}55`,
        backgroundColor: '#08080C',
        ...style,
      }}
    >
      <OffthreadVideo
        src={staticFile('avatar-lipsync-0-10s.mp4')}
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${videoScale}) translateY(${videoOffsetY}px)`,
          filter: 'contrast(1.12) saturate(1.08)',
        }}
      />

      {/* Subtle editorial gradient & crimson rim light */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(180deg, rgba(230,25,46,0.14) 0%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.72) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Live audio waveform bars at bottom of avatar card */}
      {showWaveform && (
        <div
          style={{
            position: 'absolute',
            left: 16,
            right: 16,
            bottom: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 10,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              backgroundColor: 'rgba(8, 8, 12, 0.85)',
              padding: '4px 12px',
              borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.18)',
            }}
          >
            <div
              style={{
                width: 9,
                height: 9,
                borderRadius: '50%',
                backgroundColor: COLORS.crimsonBright,
                boxShadow: `0 0 10px ${COLORS.crimsonBright}`,
              }}
            />
            <span
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 16,
                color: COLORS.cyberWhite,
                letterSpacing: 0.8,
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </span>
          </div>

          {/* Deterministic animated equalizer bars */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 4,
              height: 26,
            }}
          >
            {Array.from({ length: 12 }).map((_, i) => {
              const speaking = frame < 279;
              const wave = speaking
                ? 0.25 +
                  0.75 *
                    Math.abs(
                      Math.sin(frame * 0.45 + i * 0.9) *
                        Math.cos(frame * 0.23 - i * 0.6)
                    )
                : 0.15;
              return (
                <div
                  key={i}
                  style={{
                    width: 4,
                    height: Math.round(6 + wave * 20),
                    borderRadius: 2,
                    backgroundColor:
                      i % 3 === 0 ? COLORS.gold : COLORS.crimsonBright,
                  }}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

interface EvidenceStillBandProps {
  stillFile: 'stills/cxm-post-claim.png' | 'stills/cxm-post-account.png';
  style?: React.CSSProperties;
  highlightProgress?: number;
  highlightTopPx?: number;
  highlightHeightPx?: number;
  highlightColor?: string;
  tagText?: string;
}

/**
 * Displays the white text band (y ~ 760..1155) from the 1080x1920 Facebook post stills.
 * Uses the still as-is: zero filter, zero sharpening, zero zoom on any blurred area.
 */
export const EvidenceStillBand: React.FC<EvidenceStillBandProps> = ({
  stillFile,
  style,
  highlightProgress = 1,
  highlightTopPx = 52,
  highlightHeightPx = 44,
  highlightColor = 'rgba(230, 25, 46, 0.24)',
  tagText = 'โพสต์ต้นทาง · ตามที่เจ้าของโพสต์เล่า',
}) => {
  // The text band in the 1080x1920 PNG sits at y = 760..1155 (height ~395px).
  // We scale the 1080px-wide image by 0.805 (width = 869px) so it fits cleanly inside SAFE_WIDTH (888px)
  // without touching any blurred area (claim & account PNGs have no blurred area anyway).
  const scale = 0.805;
  const scaledWidth = Math.round(1080 * scale); // 869px
  const bandStartY = Math.round(756 * scale); // 609px
  const bandHeight = Math.round(402 * scale); // 324px

  return (
    <div
      style={{
        position: 'absolute',
        width: scaledWidth,
        borderRadius: 18,
        overflow: 'hidden',
        border: '2px solid rgba(255, 255, 255, 0.28)',
        boxShadow:
          '0 22px 55px rgba(0, 0, 0, 0.88), 0 0 30px rgba(230, 25, 46, 0.28)',
        backgroundColor: '#FFFFFF',
        ...style,
      }}
    >
      {/* Evidence top header bar */}
      <div
        style={{
          height: 38,
          backgroundColor: '#111218',
          borderBottom: '2px solid #E6192E',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: COLORS.crimsonBright,
            }}
          />
          <span
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 18,
              color: COLORS.gold,
              whiteSpace: 'nowrap',
            }}
          >
            {tagText}
          </span>
        </div>
        <span
          style={{
            fontFamily: FONT_ARCHIVO_800,
            fontSize: 15,
            color: COLORS.silver,
            letterSpacing: 1,
            whiteSpace: 'nowrap',
          }}
        >
          EVIDENCE // FB POST
        </span>
      </div>

      {/* Cropped viewport showing the exact white text band of the still as-is */}
      <div
        style={{
          position: 'relative',
          width: scaledWidth,
          height: bandHeight,
          overflow: 'hidden',
          backgroundColor: '#FFFFFF',
        }}
      >
        <Img
          src={staticFile(stillFile)}
          style={{
            width: scaledWidth,
            height: Math.round(1920 * scale),
            transform: `translateY(-${bandStartY}px)`,
            display: 'block',
          }}
        />

        {/* Animated marker highlight sweep over the key line */}
        {highlightProgress > 0 && (
          <div
            style={{
              position: 'absolute',
              left: 18,
              top: highlightTopPx,
              width: Math.round((scaledWidth - 36) * highlightProgress),
              height: highlightHeightPx,
              backgroundColor: highlightColor,
              borderLeft: `6px solid ${COLORS.crimson}`,
              borderRadius: 4,
              pointerEvents: 'none',
            }}
          />
        )}
      </div>
    </div>
  );
};

interface BroadcastHUDProps {
  frame: number;
}

/**
 * Persistent top editorial bar + persistent legal label (0..10s) + cut flash effects.
 * Strictly respects TikTok safe zones (x <= 936, y <= 1484).
 */
export const BroadcastHUD: React.FC<BroadcastHUDProps> = ({ frame }) => {
  const progress = (frame + 1) / 300;
  const seconds = Math.floor(frame / 30);
  const framesRem = frame % 30;
  const timecode = `00:0${seconds}:${framesRem.toString().padStart(2, '0')}`;

  // Cut flash triggers at shot boundaries
  const cutFrames = [0, 30, 66, 108, 147, 192, 234, 279];
  let flashOpacity = 0;
  for (const cf of cutFrames) {
    const diff = frame - cf;
    if (diff >= 0 && diff < 4) {
      flashOpacity = Math.max(
        flashOpacity,
        interpolate(diff, [0, 4], [cf === 0 ? 0.28 : 0.42, 0])
      );
    }
  }

  return (
    <AbsoluteFill style={{ pointerEvents: 'none', zIndex: 900 }}>
      {/* Subtle CRT scanlines + dark vignette across canvas */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'repeating-linear-gradient(0deg, rgba(0,0,0,0.16) 0px, rgba(0,0,0,0.16) 2px, transparent 2px, transparent 5px)',
          opacity: 0.45,
        }}
      />

      {/* Beat cut flash overlay */}
      {flashOpacity > 0 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(circle at 50% 45%, rgba(255, 209, 102, 0.55), rgba(230, 25, 46, 0.75))',
            opacity: flashOpacity,
            mixBlendMode: 'screen',
          }}
        />
      )}

      {/* TOP BROADCAST HEADER BAR (x: 48..936, y: 64..128) */}
      <div
        style={{
          position: 'absolute',
          left: SAFE_LEFT,
          top: 64,
          width: SAFE_WIDTH,
          height: 62,
          borderRadius: 14,
          backgroundColor: 'rgba(8, 9, 14, 0.90)',
          border: '1.5px solid rgba(255, 255, 255, 0.16)',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 18px',
          overflow: 'hidden',
        }}
      >
        {/* Left: BL Logo + EP.62 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Img
            src={staticFile('bl-logo.png')}
            style={{
              height: 36,
              width: 'auto',
              objectFit: 'contain',
            }}
          />
          <div
            style={{
              width: 2,
              height: 26,
              backgroundColor: 'rgba(255,255,255,0.22)',
            }}
          />
          <div
            style={{
              backgroundColor: COLORS.crimson,
              padding: '3px 10px',
              borderRadius: 6,
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 17,
              color: '#FFFFFF',
              letterSpacing: 0.8,
              whiteSpace: 'nowrap',
            }}
          >
            EP.62
          </div>
        </div>

        {/* Center/Right: Persistent Claim Attribution Badge + Timecode */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              backgroundColor: 'rgba(255, 209, 102, 0.14)',
              border: `1.5px solid ${COLORS.gold}`,
              padding: '4px 12px',
              borderRadius: 999,
              fontFamily: FONT_KANIT_600,
              fontSize: 19,
              color: COLORS.goldBright,
              whiteSpace: 'nowrap',
            }}
          >
            📌 ตามที่เจ้าของโพสต์เล่า
          </div>
          <span
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 16,
              color: COLORS.silver,
              letterSpacing: 1,
              whiteSpace: 'nowrap',
            }}
          >
            {timecode}
          </span>
        </div>

        {/* Bottom progress bar inside header */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            bottom: 0,
            height: 4,
            width: `${Math.min(100, progress * 100)}%`,
            background: `linear-gradient(90deg, ${COLORS.crimson}, ${COLORS.gold})`,
          }}
        />
      </div>

      {/* HARD RULE 2: Persistent Legal Label on screen for the whole 10s (frames 0..299)
          Positioned at y: 1428..1480, x: 48..936 (strictly above y=1500 and left of x=960) */}
      <div
        style={{
          position: 'absolute',
          left: SAFE_LEFT,
          top: 1428,
          width: SAFE_WIDTH,
          height: 52,
          borderRadius: 12,
          backgroundColor: 'rgba(6, 7, 11, 0.94)',
          border: '1.5px solid rgba(255, 255, 255, 0.24)',
          borderLeft: `6px solid ${COLORS.gold}`,
          boxShadow: '0 8px 28px rgba(0, 0, 0, 0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 16px',
        }}
      >
        <span
          style={{
            fontFamily: FONT_KANIT_600,
            fontSize: 20.5,
            color: '#F3F4F6',
            letterSpacing: 0.2,
            whiteSpace: 'nowrap',
          }}
        >
          เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง
        </span>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Deterministic floating ember/data particles in background
 */
export const AmbientParticles: React.FC<{ frame: number; color?: string }> = ({
  frame,
  color = COLORS.crimsonBright,
}) => {
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', overflow: 'hidden' }}>
      {Array.from({ length: 14 }).map((_, i) => {
        const baseX = seeded(i * 19 + 3) * 900 + 40;
        const baseY = seeded(i * 37 + 11) * 1400 + 80;
        const speedY = 1.8 + seeded(i * 53) * 2.6;
        const driftX = Math.sin(frame * 0.06 + i) * 22;
        const y = ((baseY - frame * speedY) % 1450 + 1450) % 1450 + 60;
        const size = 4 + Math.round(seeded(i * 71) * 6);
        const opacity = 0.18 + 0.25 * Math.abs(Math.sin(frame * 0.08 + i * 2));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: baseX + driftX,
              top: y,
              width: size,
              height: size,
              borderRadius: '50%',
              backgroundColor: i % 3 === 0 ? COLORS.gold : color,
              boxShadow: `0 0 12px ${i % 3 === 0 ? COLORS.gold : color}`,
              opacity,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
