import React from 'react';
import { Img, OffthreadVideo, staticFile } from 'remotion';
import { FONT_ARCHIVO_800, FONT_KANIT_600, FONT_KANIT_800 } from '../fonts';
import { BL, clamp01, expoProgress, lerp, power1Out, sineOut, wipeClip } from '../theme';

// 1. Standing Kit Background (#bg) with subtle animated neon wash, grid, and scanlines
export const KitBackground: React.FC<{ frame: number }> = ({ frame }) => {
  const pulse = 0.18 + 0.05 * Math.sin((frame / 30) * Math.PI * 2);
  const gridShift = (frame * 0.8) % 60;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundColor: BL.ink,
        overflow: 'hidden',
        zIndex: 0,
      }}
    >
      {/* Top & bottom neon red ambient wash */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `
            radial-gradient(ellipse 90% 42% at 50% 10%, rgba(255, 45, 64, ${pulse.toFixed(3)}), transparent 70%),
            radial-gradient(ellipse 80% 38% at 35% 78%, rgba(224, 32, 47, 0.14), transparent 72%)
          `,
        }}
      />
      {/* Subtle tactical grid */}
      <div
        style={{
          position: 'absolute',
          inset: -60,
          transform: `translateY(${gridShift.toFixed(1)}px)`,
          backgroundImage: `
            linear-gradient(to right, rgba(255, 45, 64, 0.055) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 45, 64, 0.055) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />
      {/* Scanlines */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'repeating-linear-gradient(to bottom, rgba(255, 255, 255, 0.018) 0px, rgba(255, 255, 255, 0.018) 2px, transparent 2px, transparent 6px)',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};

// 2. Standing Brand Bug (SKILL.md §6a: right: 150px; top: 310px; logo height: 60px; neon rule + date)
export const BrandBug: React.FC = () => {
  return (
    <div
      id="bug"
      style={{
        position: 'absolute',
        right: 150,
        top: 310,
        zIndex: 88,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        pointerEvents: 'none',
      }}
    >
      <Img
        src={staticFile('bl-logo.png')}
        style={{
          height: 60,
          width: 'auto',
          display: 'block',
          filter: 'drop-shadow(0 4px 12px rgba(0, 0, 0, 0.85))',
        }}
      />
      <div
        style={{
          width: '100%',
          height: 3,
          backgroundColor: BL.neon,
          boxShadow: BL.glowM,
          marginTop: 7,
          marginBottom: 5,
          borderRadius: 2,
        }}
      />
      <div
        style={{
          backgroundColor: 'rgba(7, 8, 10, 0.84)',
          padding: '2px 10px',
          borderRadius: 5,
          border: '1px solid rgba(255, 45, 64, 0.28)',
          fontFamily: FONT_KANIT_600,
          fontSize: 18,
          fontWeight: 600,
          color: BL.white,
          lineHeight: 1.25,
          whiteSpace: 'nowrap',
          letterSpacing: '0.02em',
        }}
      >
        15 ต.ค. 69
      </div>
    </div>
  );
};

// 3. Standing Legal Label (SKILL.md §6b & Hard Line 2: y = 1430, whole 10s, readable on dark pill)
export const LegalLabel: React.FC = () => {
  return (
    <div
      className="bl-legal"
      style={{
        position: 'absolute',
        left: BL.safeLeft,
        width: 720,
        top: 1430,
        zIndex: 95,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          width: '100%',
          backgroundColor: BL.legalBg,
          border: '1px solid rgba(255, 45, 64, 0.26)',
          borderRadius: 10,
          padding: '7px 14px',
          boxShadow: '0 6px 20px rgba(0, 0, 0, 0.82)',
          fontFamily: FONT_KANIT_600,
          fontSize: 18,
          fontWeight: 600,
          color: BL.white,
          textAlign: 'center',
          whiteSpace: 'nowrap',
          lineHeight: 1.3,
        }}
      >
        เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง
      </div>
    </div>
  );
};

// 4. Unified Spoken-Line Caption Band (SKILL.md §6f: single .cap look at top: 1295px, safe width 720px)
export const CaptionBand: React.FC<{ frame: number }> = ({ frame }) => {
  // Spoken beats from BRIEF.md:
  // 1.0–3.6 s (30..108): "ถือออเดอร์สองชั่วโมง แต่โดนข้อหาเทรดเร็วเกินไป?"
  // 3.6–6.4 s (108..192): "เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไรเกือบหกล้านบาท"
  // 6.4–9.3 s (192..279): "ซีเอ็กซ์เอ็มแจ้งในอีเมลว่าเป็นท็อกซิกเทรดดิ้ง"
  // 9.3–10.0 s (279..300): hold final summary caption so plate/overlay never dips empty
  let lineContent: React.ReactNode = null;
  let beatStart = 30;

  if (frame >= 30 && frame < 108) {
    beatStart = 30;
    lineContent = (
      <>
        <span style={{ whiteSpace: 'nowrap' }}>ถือออเดอร์ </span>
        <span style={{ color: BL.yellow, fontWeight: 800, whiteSpace: 'nowrap' }}>2 ชั่วโมง </span>
        <span style={{ whiteSpace: 'nowrap' }}>แต่โดนข้อหา</span>
        <span style={{ color: BL.neon, fontWeight: 800, whiteSpace: 'nowrap' }}>เทรดเร็วเกินไป?</span>
      </>
    );
  } else if (frame >= 108 && frame < 192) {
    beatStart = 108;
    lineContent = (
      <>
        <span style={{ whiteSpace: 'nowrap' }}>เธอเล่าว่า </span>
        <span style={{ color: BL.neon, fontWeight: 800, whiteSpace: 'nowrap' }}>CXM </span>
        <span style={{ whiteSpace: 'nowrap' }}>ไม่จ่ายกำไร</span>
        <span style={{ color: BL.yellow, fontWeight: 800, whiteSpace: 'nowrap' }}>เกือบ 6 ล้านบาท</span>
      </>
    );
  } else if (frame >= 192 && frame < 279) {
    beatStart = 192;
    lineContent = (
      <>
        <span style={{ color: BL.neon, fontWeight: 800, whiteSpace: 'nowrap' }}>CXM </span>
        <span style={{ whiteSpace: 'nowrap' }}>แจ้งในอีเมลว่าเป็น </span>
        <span style={{ color: BL.yellow, fontWeight: 800, whiteSpace: 'nowrap' }}>
          &ldquo;Toxic Trading&rdquo;
        </span>
      </>
    );
  } else if (frame >= 279) {
    beatStart = 279;
    lineContent = (
      <>
        <span style={{ color: BL.yellow, fontWeight: 800, whiteSpace: 'nowrap' }}>
          ตามที่เจ้าของโพสต์เล่า
        </span>
        <span style={{ whiteSpace: 'nowrap' }}> · ถือ 2 ชม. แต่ถูกอ้าง </span>
        <span style={{ color: BL.neon, fontWeight: 800, whiteSpace: 'nowrap' }}>Toxic Trading</span>
      </>
    );
  }

  if (!lineContent) {
    return null;
  }

  const wipe = wipeClip(frame, beatStart, 7);

  return (
    <div
      className="caplayer"
      style={{
        position: 'absolute',
        left: BL.safeLeft,
        width: 720,
        top: 1295,
        zIndex: 82,
        display: 'flex',
        justifyContent: 'center',
        pointerEvents: 'none',
      }}
    >
      <div
        className="cap"
        style={{
          width: '100%',
          backgroundColor: BL.capBg,
          padding: '18px 26px',
          borderRadius: 18,
          border: '1px solid rgba(255, 45, 64, 0.34)',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.82)',
          fontFamily: FONT_KANIT_600,
          fontSize: 34,
          fontWeight: 600,
          color: BL.white,
          textAlign: 'center',
          lineHeight: 1.32,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
        }}
      >
        <div style={{ clipPath: wipe }}>{lineContent}</div>
      </div>
    </div>
  );
};

// 5. Continuous Time-Synced Presenter (SKILL.md §6d hook slide + sine.out composite shrink + hard-cut return)
export const AvatarPresenter: React.FC<{ frame: number }> = ({ frame }) => {
  // Always synced to timeline t = frame / 30 by rendering a single root-level OffthreadVideo
  // Mode choreography (SKILL.md §6d):
  // - Frames 0..32 (0.0–1.07s): Full-frame hook mode, sliding down with power1.out to open top headline space
  // - Frames 32..54 (1.07–1.80s): Animated sine.out shrink (22 frames) into lower-left composite frame
  // - Frames 54..192 (1.80–6.40s): Lower-left composite cut-out frame (x: 120..432, y: 850..1270)
  // - Frames 192..222 (6.40–7.40s): Hard cut back to full-frame on new spoken sentence ("CXM แจ้งในอีเมลว่า...")
  // - Frames 222..242 (7.40–8.07s): Animated sine.out shrink (20 frames) into lower-left composite frame for "TOXIC TRADING"
  // - Frames 242..300 (8.07–10.00s): Lower-left composite cut-out frame

  // Full-frame box geometry (leaves y=252..585 above head for hook/email header, and y=1040..1270 at chest)
  const ffBox = {
    left: 60,
    top: 475,
    width: 960,
    height: 1445,
    borderRadius: 28,
    videoScale: 1.05,
    videoOffsetY: 28,
  };

  // Lower-left composite cut-out box geometry (x: 120..432, y: 850..1270, clears upper evidence & bottom caption)
  const compBox = {
    left: 120,
    top: 850,
    width: 312,
    height: 420,
    borderRadius: 22,
    videoScale: 1.24,
    videoOffsetY: 42,
  };

  let tComp = 0; // 0 = full-frame, 1 = composite cut-out
  let hookSlideY = 0;

  if (frame < 32) {
    tComp = 0;
    // Hook opening downward slide (power1.out over frames 0..28)
    const pHook = power1Out(clamp01(frame / 28));
    hookSlideY = lerp(-36, 20, pHook);
  } else if (frame < 54) {
    tComp = sineOut((frame - 32) / 22);
    hookSlideY = lerp(20, 0, tComp);
  } else if (frame < 192) {
    tComp = 1;
  } else if (frame < 222) {
    // Hard cut back to full-frame at frame 192 (6.4s)
    tComp = 0;
    const pPush = sineOut((frame - 192) / 30);
    hookSlideY = lerp(24, 8, pPush);
  } else if (frame < 242) {
    tComp = sineOut((frame - 222) / 20);
  } else {
    tComp = 1;
  }

  const left = lerp(ffBox.left, compBox.left, tComp);
  const top = lerp(ffBox.top + hookSlideY, compBox.top, tComp);
  const width = lerp(ffBox.width, compBox.width, tComp);
  const height = lerp(ffBox.height, compBox.height, tComp);
  const borderRadius = lerp(ffBox.borderRadius, compBox.borderRadius, tComp);
  const videoScale = lerp(ffBox.videoScale, compBox.videoScale, tComp);
  const videoOffsetY = lerp(ffBox.videoOffsetY, compBox.videoOffsetY, tComp);

  // Subtle camera breathing
  const breath = 1 + 0.012 * Math.sin((frame / 30) * Math.PI * 1.5);

  return (
    <div
      style={{
        position: 'absolute',
        left,
        top,
        width,
        height,
        borderRadius,
        overflow: 'hidden',
        zIndex: tComp > 0.05 ? 45 : 22,
        border:
          tComp > 0.15
            ? `2px solid rgba(255, 45, 64, ${(0.45 + 0.45 * tComp).toFixed(2)})`
            : '1px solid rgba(255, 45, 64, 0.25)',
        boxShadow:
          tComp > 0.15
            ? '0 16px 38px rgba(0, 0, 0, 0.88), 0 0 22px rgba(255, 45, 64, 0.45)'
            : '0 12px 40px rgba(0, 0, 0, 0.85)',
        backgroundColor: '#0A0B0D',
      }}
    >
      <OffthreadVideo
        src={staticFile('avatar-lipsync-0-10s.mp4')}
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: '50% 18%',
          transform: `scale(${(videoScale * breath).toFixed(4)}) translateY(${videoOffsetY.toFixed(1)}px)`,
          filter: 'contrast(1.12) saturate(1.16) brightness(0.98)',
        }}
      />

      {/* Feathered contact-shadow ring & dark bottom gradient per SKILL.md §6d */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            tComp > 0.5
              ? 'radial-gradient(circle at 50% 42%, transparent 52%, rgba(7, 8, 10, 0.72) 100%), linear-gradient(to bottom, rgba(7, 8, 10, 0.25) 0%, transparent 18%, transparent 72%, rgba(7, 8, 10, 0.88) 100%)'
              : 'linear-gradient(to bottom, rgba(7, 8, 10, 0.72) 0%, transparent 18%, transparent 65%, rgba(7, 8, 10, 0.92) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Live voice indicator badge on composite cutout */}
      {tComp > 0.65 && (
        <div
          style={{
            position: 'absolute',
            left: 12,
            bottom: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            backgroundColor: 'rgba(7, 8, 10, 0.86)',
            border: '1px solid rgba(255, 45, 64, 0.55)',
            borderRadius: 8,
            padding: '4px 10px',
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: BL.neon,
              boxShadow: BL.glowS,
            }}
          />
          <span
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 13,
              fontWeight: 800,
              color: BL.white,
              letterSpacing: '0.06em',
              whiteSpace: 'nowrap',
            }}
          >
            BLACK LIQUIDITY · EP.62
          </span>
        </div>
      )}
    </div>
  );
};

// 6. Top-Left Claim Status Header (sits at x: 120..730, y: 262..410 — strictly left of Brand Bug at x: 766..930)
export const TopClaimBanner: React.FC<{
  frame: number;
  tag: string;
  headline: string;
  accentWord?: string;
  beatStart: number;
}> = ({ frame, tag, headline, accentWord, beatStart }) => {
  const p = expoProgress(frame, beatStart, 9);
  const wipe = wipeClip(frame, beatStart + 2, 10);

  return (
    <div
      style={{
        position: 'absolute',
        left: BL.safeLeft,
        top: 264,
        width: 610, // ends at x=730, well clear of Brand Bug at x=766..930
        zIndex: 75,
        pointerEvents: 'none',
      }}
    >
      {/* Claim disclaimer pill */}
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 10,
          backgroundColor: 'rgba(7, 8, 10, 0.90)',
          border: `1.5px solid ${BL.neon}`,
          boxShadow: BL.glowS,
          borderRadius: 9,
          padding: '6px 14px',
          transform: `scaleX(${p.toFixed(3)})`,
          transformOrigin: 'left center',
          marginBottom: 10,
        }}
      >
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            backgroundColor: BL.neon,
            boxShadow: BL.glowS,
          }}
        />
        <span
          style={{
            fontFamily: FONT_KANIT_800,
            fontSize: 20,
            fontWeight: 800,
            color: BL.yellow,
            whiteSpace: 'nowrap',
            letterSpacing: '0.02em',
          }}
        >
          {tag}
        </span>
      </div>

      {/* Main section micro-headline */}
      <div
        style={{
          clipPath: wipe,
          fontFamily: FONT_KANIT_800,
          fontSize: 38,
          fontWeight: 800,
          color: BL.white,
          textShadow: BL.textOutline,
          lineHeight: 1.28,
          whiteSpace: 'nowrap',
        }}
      >
        {headline}{' '}
        {accentWord && (
          <span
            style={{
              color: BL.neon,
              textShadow: BL.textGlowNeon,
              whiteSpace: 'nowrap',
            }}
          >
            {accentWord}
          </span>
        )}
      </div>

      {/* Emissive neon rule */}
      <div
        style={{
          width: 460,
          height: 4,
          backgroundColor: BL.neon,
          boxShadow: BL.glowM,
          marginTop: 8,
          borderRadius: 2,
          transform: `scaleX(${p.toFixed(3)})`,
          transformOrigin: 'left center',
        }}
      />
    </div>
  );
};
