import React from 'react';
import {
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import { fitFontSize, KANIT_FONT } from '../fonts';

/**
 * Always-on legal disclaimer at bottom of safe area (y 1440..1490, x 120..840).
 * Never animated.
 */
export const LegalLabel: React.FC = () => {
  const text =
    'เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง';
  const fontSize = fitFontSize({
    text,
    targetSize: 22,
    maxWidth: 688,
    fontFamily: 'Kanit',
    fontWeight: 600,
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 120,
        top: 1442,
        width: 720,
        height: 46,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.72)',
          borderRadius: 10,
          padding: '6px 16px',
          maxWidth: 720,
          boxSizing: 'border-box',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(255, 255, 255, 0.12)',
        }}
      >
        <span
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 600,
            fontSize,
            lineHeight: 1.15,
            color: 'rgba(255, 255, 255, 0.94)',
            whiteSpace: 'nowrap',
          }}
        >
          {text}
        </span>
      </div>
    </div>
  );
};

/**
 * Always-on brand bug at top right (x 700..840, y 180..260).
 * Logo image bl-logo.png (~150px wide), short red rule under it, and date "14 ต.ค. 69".
 * Never animated.
 */
export const BrandBug: React.FC = () => {
  return (
    <div
      style={{
        position: 'absolute',
        left: 690,
        top: 180,
        width: 150,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        zIndex: 50,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.48)',
          borderRadius: 10,
          padding: '6px 8px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
        }}
      >
        <Img
          src={staticFile('bl-logo.png')}
          style={{
            width: 142,
            height: 'auto',
            display: 'block',
          }}
        />
        <div
          style={{
            width: 92,
            height: 3,
            backgroundColor: '#E5202E',
            borderRadius: 2,
            marginTop: 5,
            marginBottom: 4,
          }}
        />
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 600,
            fontSize: 20,
            lineHeight: 1.05,
            color: '#FFFFFF',
            whiteSpace: 'nowrap',
            textShadow: '0 2px 6px rgba(0, 0, 0, 0.9)',
          }}
        >
          14 ต.ค. 69
        </div>
      </div>
    </div>
  );
};

/**
 * Top viral headline:
 * - 0.00..9.27s (frames 0..277): 2-line headline + credit at x=120, y~300..560
 *   with 0.4s (12 frames) slide-up + scale (1.08 -> 1.0) landing motion.
 * - 9.27..11.67s (frames 278..349): hidden during avatar.
 * - 11.67..15.00s (frames 350..449): smaller 1-line version ("CXM ไม่จ่ายกำไร เกือบ 6 ล้าน", ~52px).
 */
export const Headline: React.FC = () => {
  const frame = useCurrentFrame();

  // Hidden during HOOK-4 avatar (9.27s..11.67s => frames 278..349)
  if (frame >= 278 && frame < 350) {
    return null;
  }

  // Smaller 1-line headline from 11.67s to 15.00s (frames 350..449)
  if (frame >= 350) {
    const localFrame = frame - 350;
    const translateY = interpolate(localFrame, [0, 8], [18, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });
    const scale = interpolate(localFrame, [0, 8], [1.06, 1.0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });

    const fullOneLine = 'CXM ไม่จ่ายกำไร เกือบ 6 ล้าน';
    const oneLineFontSize = fitFontSize({
      text: fullOneLine,
      targetSize: 52,
      maxWidth: 696,
      fontFamily: 'Kanit',
      fontWeight: 800,
    });

    return (
      <>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: 1080,
            height: 470,
            background:
              'linear-gradient(180deg, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.72) 62%, rgba(0,0,0,0) 100%)',
            zIndex: 35,
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 120,
            top: 300,
            width: 720,
            zIndex: 40,
            transformOrigin: 'left top',
            transform: `translateY(${translateY}px) scale(${scale})`,
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              display: 'inline-block',
              backgroundColor: 'rgba(0, 0, 0, 0.58)',
              borderRadius: 16,
              padding: '10px 20px',
              borderLeft: '6px solid #FFD60A',
              maxWidth: 720,
              boxSizing: 'border-box',
            }}
          >
            <div
              style={{
                fontFamily: KANIT_FONT,
                fontWeight: 800,
                fontSize: oneLineFontSize,
                lineHeight: 1.15,
                whiteSpace: 'nowrap',
                textShadow: '0 4px 14px rgba(0, 0, 0, 0.9)',
              }}
            >
              <span style={{ color: '#FFFFFF' }}>CXM ไม่จ่ายกำไร </span>
              <span style={{ color: '#FFD60A' }}>เกือบ 6 ล้าน</span>
            </div>
          </div>
        </div>
      </>
    );
  }

  // Full 2-line headline from 0.00s to 9.27s (frames 0..277)
  // First 0.4s (12 frames): quick, strong motion (slide up + scale 1.08 -> 1.0).
  const translateY = interpolate(frame, [0, 12], [28, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const scale = interpolate(frame, [0, 12], [1.08, 1.0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const line1Text = 'CXM ไม่จ่ายกำไร';
  const line2Text = 'เกือบ 6 ล้านบาท';
  const creditText = 'ตามที่เจ้าของโพสต์เล่า';

  const line1Size = fitFontSize({
    text: line1Text,
    targetSize: 76,
    maxWidth: 720,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });
  const line2Size = fitFontSize({
    text: line2Text,
    targetSize: 92,
    maxWidth: 720,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });
  const creditSize = fitFontSize({
    text: creditText,
    targetSize: 30,
    maxWidth: 720,
    fontFamily: 'Kanit',
    fontWeight: 600,
  });

  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1080,
          height: 640,
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.90) 0%, rgba(0,0,0,0.82) 58%, rgba(0,0,0,0.38) 84%, rgba(0,0,0,0) 100%)',
          zIndex: 35,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 120,
          top: 300,
          width: 720,
          zIndex: 40,
          transformOrigin: 'left top',
          transform: `translateY(${translateY}px) scale(${scale})`,
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 800,
            fontSize: line1Size,
            lineHeight: 1.08,
            color: '#FFFFFF',
            whiteSpace: 'nowrap',
            textShadow: '0 4px 18px rgba(0, 0, 0, 0.9)',
          }}
        >
          {line1Text}
        </div>
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 800,
            fontSize: line2Size,
            lineHeight: 1.08,
            color: '#FFD60A',
            whiteSpace: 'nowrap',
            marginTop: 2,
            textShadow: '0 4px 20px rgba(0, 0, 0, 0.92)',
          }}
        >
          {line2Text}
        </div>
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 600,
            fontSize: creditSize,
            lineHeight: 1.2,
            color: 'rgba(255, 255, 255, 0.85)',
            whiteSpace: 'nowrap',
            marginTop: 10,
            textShadow: '0 2px 10px rgba(0, 0, 0, 0.85)',
          }}
        >
          {creditText}
        </div>
      </div>
    </>
  );
};

/**
 * Reusable dark rounded pill for beat captions.
 * Appears within 0.25s (7 frames) via left-to-right wipe + pop and stays until beat ends.
 * Strictly inside safe area x 120..840.
 */
export const CaptionPill: React.FC<{
  top: number;
  children: React.ReactNode;
  credit?: string;
}> = ({ top, children, credit }) => {
  const localFrame = useCurrentFrame();

  // 0.25s at 30fps = 7.5 frames -> complete wipe/pop by frame 7
  const wipeRightPct = interpolate(localFrame, [0, 7], [100, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const scale = interpolate(localFrame, [0, 7], [0.94, 1.0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const creditFontSize = credit
    ? fitFontSize({
        text: credit,
        targetSize: 28,
        maxWidth: 668,
        fontFamily: 'Kanit',
        fontWeight: 600,
      })
    : 28;

  return (
    <div
      style={{
        position: 'absolute',
        left: 120,
        top,
        width: 720,
        display: 'flex',
        justifyContent: 'center',
        zIndex: 30,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.64)',
          borderRadius: 22,
          padding: '14px 24px',
          maxWidth: 720,
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          boxShadow: '0 12px 32px rgba(0, 0, 0, 0.5)',
          transform: `scale(${scale})`,
          clipPath: `inset(0 ${wipeRightPct}% 0 0 round 22px)`,
        }}
      >
        {children}
        {credit ? (
          <div
            style={{
              fontFamily: KANIT_FONT,
              fontWeight: 600,
              fontSize: creditFontSize,
              lineHeight: 1.2,
              color: 'rgba(255, 255, 255, 0.85)',
              whiteSpace: 'nowrap',
              marginTop: 6,
            }}
          >
            {credit}
          </div>
        ) : null}
      </div>
    </div>
  );
};

/**
 * Animated yellow highlight box that draws itself around (x, y, w, h) in still coordinates.
 */
export const HighlightBox: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  startFrame: number;
  endFrame: number;
}> = ({ x, y, w, h, startFrame, endFrame }) => {
  const localFrame = useCurrentFrame();
  const progress = interpolate(localFrame, [startFrame, endFrame], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  if (progress <= 0) {
    return null;
  }

  const perimeter = 2 * (w + h);
  const dashOffset = perimeter * (1 - progress);

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: w,
        height: h,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: w * progress,
          height: h,
          backgroundColor: 'rgba(255, 214, 10, 0.24)',
          borderRadius: 8,
        }}
      />
      <svg
        width={w}
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          overflow: 'visible',
        }}
      >
        <rect
          x={2.5}
          y={2.5}
          width={w - 5}
          height={h - 5}
          rx={8}
          ry={8}
          fill="none"
          stroke="#FFD60A"
          strokeWidth={5}
          strokeDasharray={perimeter}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
};
