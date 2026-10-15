import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { FONT_ARCHIVO_800, FONT_KANIT_600, FONT_KANIT_800 } from '../fonts';

const CUT_FRAMES = [30, 66, 108, 150, 192, 234, 279] as const;

export const HudChrome: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progressPct = interpolate(frame, [0, durationInFrames - 1], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Deterministic pulse for LIVE indicator
  const pulseOpacity = 0.55 + 0.45 * Math.sin(frame * 0.35);

  // Calculate flash intensity at cut points
  let cutFlash = 0;
  for (const cutFrame of CUT_FRAMES) {
    const dist = Math.abs(frame - cutFrame);
    if (dist <= 2) {
      const localFlash = interpolate(dist, [0, 2], [0.42, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });
      if (localFlash > cutFlash) {
        cutFlash = localFlash;
      }
    }
  }

  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {/* Subtle CRT scanline & editorial grid texture */}
      <AbsoluteFill
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, rgba(255,255,255,0.018) 0px, rgba(255,255,255,0.018) 1px, transparent 1px, transparent 4px)',
          opacity: 0.7,
        }}
      />

      {/* Cut Flash Whip Overlay */}
      {cutFlash > 0 && (
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(circle at 50% 45%, rgba(255, 184, 0, 0.45) 0%, rgba(255, 30, 39, 0.78) 60%, rgba(5, 5, 7, 0.9) 100%)',
            opacity: cutFlash,
          }}
        />
      )}

      {/* Top Broadcast Header Bar (y: 44..122, x: 48..1032) */}
      <div
        style={{
          position: 'absolute',
          top: 44,
          left: 48,
          width: 984,
          height: 76,
          borderRadius: 18,
          backgroundColor: 'rgba(7, 7, 11, 0.86)',
          border: '1.5px solid rgba(255, 30, 39, 0.55)',
          boxShadow: '0 14px 36px rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 22px',
          overflow: 'hidden',
        }}
      >
        {/* Left: BLACK LIQUIDITY Channel Logo + EP.62 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Img
            src={staticFile('bl-logo.png')}
            style={{
              height: 44,
              width: 'auto',
              objectFit: 'contain',
            }}
          />
          <div
            style={{
              width: 2,
              height: 32,
              backgroundColor: 'rgba(255, 255, 255, 0.22)',
            }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                width: 11,
                height: 11,
                borderRadius: '50%',
                backgroundColor: '#FF1E27',
                opacity: pulseOpacity,
                boxShadow: '0 0 12px #FF1E27',
              }}
            />
            <span
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 20,
                color: '#F8FAFC',
                letterSpacing: 1.4,
                whiteSpace: 'nowrap',
              }}
            >
              EP.62 · SPECIAL DOSSIER
            </span>
          </div>
        </div>

        {/* Right: Persistent Claim Attribution Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            backgroundColor: 'rgba(255, 184, 0, 0.14)',
            border: '1.5px solid #FFB800',
            borderRadius: 999,
            padding: '6px 18px',
          }}
        >
          <span
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 21,
              color: '#FFB800',
              whiteSpace: 'nowrap',
            }}
          >
            ตามที่เจ้าของโพสต์เล่า
          </span>
        </div>

        {/* Bottom Progress Hairline inside Header */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            height: 4,
            width: `${progressPct}%`,
            background: 'linear-gradient(90deg, #FF1E27 0%, #FFB800 100%)',
          }}
        />
      </div>

      {/* HARD LINE #2: Persistent 10s Legal Label (Whole 10s, readable, clear of TikTok right x>960 & bottom y>1500) */}
      <div
        style={{
          position: 'absolute',
          top: 1428,
          left: 48,
          width: 896,
          height: 54,
          borderRadius: 12,
          backgroundColor: 'rgba(6, 6, 10, 0.94)',
          border: '1.5px solid rgba(255, 184, 0, 0.65)',
          borderLeft: '6px solid #FF1E27',
          boxShadow: '0 10px 28px rgba(0, 0, 0, 0.85)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 18px',
        }}
      >
        <span
          style={{
            fontFamily: FONT_KANIT_600,
            fontSize: 21.5,
            color: '#F8FAFC',
            letterSpacing: 0.2,
            whiteSpace: 'nowrap',
            lineHeight: 1,
          }}
        >
          เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง
        </span>
      </div>
    </AbsoluteFill>
  );
};
