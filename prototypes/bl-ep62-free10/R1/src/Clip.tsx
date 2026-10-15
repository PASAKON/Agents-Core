import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {
  AvatarPresenter,
  BrandBug,
  CaptionBand,
  KitBackground,
  LegalLabel,
  TopClaimBanner,
} from './components/Overlays';
import {
  FONT_ARCHIVO_800,
  FONT_FACE_CSS,
  FONT_KANIT_600,
  FONT_KANIT_800,
  useLoadFonts,
} from './fonts';
import { BL, clamp01, expoProgress, lerp, wipeClip } from './theme';

// Helper for B-roll plate with continuous camera push-in and darkened neon grade (SKILL.md §6d)
const BrollPlate: React.FC<{
  file: string;
  localFrame: number;
  durationFrames: number;
  startFrom?: number;
  scaleFrom?: number;
  scaleTo?: number;
  brightness?: number;
}> = ({
  file,
  localFrame,
  durationFrames,
  startFrom = 0,
  scaleFrom = 1.02,
  scaleTo = 1.12,
  brightness = 0.44,
}) => {
  const t = clamp01(localFrame / Math.max(1, durationFrames));
  const scale = lerp(scaleFrom, scaleTo, t);

  return (
    <AbsoluteFill style={{ zIndex: 5, overflow: 'hidden' }}>
      <OffthreadVideo
        src={staticFile(file)}
        startFrom={startFrom}
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale.toFixed(4)})`,
          filter: `brightness(${brightness}) contrast(1.18) saturate(1.22)`,
        }}
      />
      {/* Dark top/bottom vignette to protect readability */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(to bottom, rgba(7, 8, 10, 0.78) 0%, rgba(7, 8, 10, 0.25) 28%, rgba(7, 8, 10, 0.30) 68%, rgba(7, 8, 10, 0.90) 100%)',
        }}
      />
    </AbsoluteFill>
  );
};

// Corner bracket decoration (.bl-bracket from BL-KIT.md)
const CornerBrackets: React.FC<{ color?: string; size?: number; thickness?: number }> = ({
  color = BL.neon,
  size = 18,
  thickness = 3,
}) => {
  const common: React.CSSProperties = {
    position: 'absolute',
    width: size,
    height: size,
    pointerEvents: 'none',
  };
  return (
    <>
      <div
        style={{
          ...common,
          top: -2,
          left: -2,
          borderTop: `${thickness}px solid ${color}`,
          borderLeft: `${thickness}px solid ${color}`,
        }}
      />
      <div
        style={{
          ...common,
          top: -2,
          right: -2,
          borderTop: `${thickness}px solid ${color}`,
          borderRight: `${thickness}px solid ${color}`,
        }}
      />
      <div
        style={{
          ...common,
          bottom: -2,
          left: -2,
          borderBottom: `${thickness}px solid ${color}`,
          borderLeft: `${thickness}px solid ${color}`,
        }}
      />
      <div
        style={{
          ...common,
          bottom: -2,
          right: -2,
          borderBottom: `${thickness}px solid ${color}`,
          borderRight: `${thickness}px solid ${color}`,
        }}
      />
    </>
  );
};

export const Clip: React.FC = () => {
  useLoadFonts();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        width: 1080,
        height: 1920,
        backgroundColor: BL.ink,
        overflow: 'hidden',
        fontFamily: FONT_KANIT_600,
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: FONT_FACE_CSS }} />

      {/* Master Audio Track: voice-10s.wav (0.0s to 10.0s untouched) */}
      <Audio src={staticFile('voice-10s.wav')} />

      {/* Standing Kit Background (#bg, z-index 0) */}
      <KitBackground frame={frame} />

      {/* =====================================================================
          BACKGROUND B-ROLL PLATES (8 seamless shots covering all 300 frames)
          ===================================================================== */}

      {/* Shot 1 (0.0–1.0s, frames 0..30): Red digital countdown tease behind full-frame hook */}
      <Sequence from={0} durationInFrames={30}>
        <BrollPlate
          file="broll/red-digital-countdown.mp4"
          localFrame={frame}
          durationFrames={30}
          scaleFrom={1.04}
          scaleTo={1.14}
          brightness={0.38}
        />
      </Sequence>

      {/* Shot 2 (1.0–2.3s, frames 30..69): Hourglass red sand for "ถือออเดอร์ 2 ชั่วโมง" */}
      <Sequence from={30} durationInFrames={39}>
        <BrollPlate
          file="broll/hourglass-red-sand.mp4"
          localFrame={frame - 30}
          durationFrames={39}
          scaleFrom={1.02}
          scaleTo={1.12}
          brightness={0.46}
        />
      </Sequence>

      {/* Shot 3 (2.3–3.6s, frames 69..108): Red digital countdown for "แต่โดนข้อหาเทรดเร็วเกินไป?" */}
      <Sequence from={69} durationInFrames={39}>
        <BrollPlate
          file="broll/red-digital-countdown.mp4"
          localFrame={frame - 69}
          durationFrames={39}
          startFrom={24}
          scaleFrom={1.06}
          scaleTo={1.18}
          brightness={0.44}
        />
      </Sequence>

      {/* Shot 4 (3.6–5.0s, frames 108..150): Gold bar in glass cube for "เธอเล่าว่า CXM ไม่จ่ายกำไร..." */}
      <Sequence from={108} durationInFrames={42}>
        <BrollPlate
          file="broll/gold-bar-in-glass-cube.mp4"
          localFrame={frame - 108}
          durationFrames={42}
          scaleFrom={1.02}
          scaleTo={1.12}
          brightness={0.46}
        />
      </Sequence>

      {/* Shot 5 (5.0–6.4s, frames 150..192): Finger taps red lock for "...เกือบ 6 ล้านบาท" */}
      <Sequence from={150} durationInFrames={42}>
        <BrollPlate
          file="broll/finger-taps-red-lock.mp4"
          localFrame={frame - 150}
          durationFrames={42}
          scaleFrom={1.03}
          scaleTo={1.15}
          brightness={0.44}
        />
      </Sequence>

      {/* Shot 6 (6.4–7.8s, frames 192..234): Typewriter neon ticker tape for "CXM แจ้งในอีเมลว่า..." */}
      <Sequence from={192} durationInFrames={42}>
        <BrollPlate
          file="broll/typewriter-red-neon-ticker-tape.mp4"
          localFrame={frame - 192}
          durationFrames={42}
          scaleFrom={1.02}
          scaleTo={1.12}
          brightness={0.40}
        />
      </Sequence>

      {/* Shot 7 (7.8–9.3s, frames 234..279): Red forbidden icon glow for "...เป็น Toxic Trading" */}
      <Sequence from={234} durationInFrames={45}>
        <BrollPlate
          file="broll/red-forbidden-icon-glow.mp4"
          localFrame={frame - 234}
          durationFrames={45}
          scaleFrom={1.04}
          scaleTo={1.16}
          brightness={0.45}
        />
      </Sequence>

      {/* Shot 8 (9.3–10.0s, frames 279..300): Contract signature wax seal for final verdict */}
      <Sequence from={279} durationInFrames={21}>
        <BrollPlate
          file="broll/contract-signature-wax-seal.mp4"
          localFrame={frame - 279}
          durationFrames={21}
          scaleFrom={1.03}
          scaleTo={1.10}
          brightness={0.42}
        />
      </Sequence>

      {/* =====================================================================
          CONTINUOUS TIME-LOCKED PRESENTER (avatar-lipsync-0-10s.mp4)
          ===================================================================== */}
      <AvatarPresenter frame={frame} />

      {/* =====================================================================
          SHOT-BY-SHOT KINETIC GRAPHICS & REAL-FOOTAGE EVIDENCE CARDS
          ===================================================================== */}

      {/* SHOT 1 (0.0–1.0s, frames 0..30): Scroll-Stopper Hook */}
      {frame >= 0 && frame < 30 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={0}
            tag="ตามที่เจ้าของโพสต์เล่า · EP.62"
            headline="เทรดทองได้กำไร"
            accentWord="เกือบ 6 ล้าน?!"
          />
          {/* Chest-level scroll-stopper hook card (y: 1030..1268, below avatar face y: 540..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              width: 720,
              top: 1030,
              zIndex: 65,
              backgroundColor: 'rgba(7, 8, 10, 0.92)',
              border: `2px solid ${BL.neon}`,
              boxShadow: BL.glowM,
              borderRadius: 18,
              padding: '20px 26px',
              transform: `scale(${lerp(0.92, 1, expoProgress(frame, 0, 8)).toFixed(4)})`,
              transformOrigin: 'center center',
            }}
          >
            <CornerBrackets color={BL.yellow} size={18} thickness={3} />
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 8,
              }}
            >
              <span
                style={{
                  backgroundColor: BL.neon,
                  color: BL.white,
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 22,
                  fontWeight: 800,
                  padding: '3px 12px',
                  borderRadius: 6,
                  boxShadow: BL.glowS,
                  whiteSpace: 'nowrap',
                }}
              >
                BROKER: CXM
              </span>
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 22,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                ถือออเดอร์ 2 ชั่วโมง · ถอนไม่ได้?!
              </span>
            </div>
            <div
              style={{
                clipPath: wipeClip(frame, 2, 9),
                fontFamily: FONT_KANIT_800,
                fontSize: 54,
                fontWeight: 800,
                color: BL.white,
                textShadow: BL.textOutline,
                lineHeight: 1.24,
                whiteSpace: 'nowrap',
              }}
            >
              อ้างโดนข้อหา{' '}
              <span style={{ color: BL.neon, textShadow: BL.textGlowNeon }}>
                &ldquo;TOXIC TRADING&rdquo;
              </span>
            </div>
          </div>
        </>
      )}

      {/* SHOT 2 (1.0–2.3s, frames 30..69): "ถือออเดอร์สองชั่วโมง..." */}
      {frame >= 30 && frame < 69 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={30}
            tag="โพสต์ผู้เสียหาย · ตามที่เจ้าของโพสต์เล่า"
            headline="ถือออเดอร์ทองคำ"
            accentWord="นานถึง 2 ชั่วโมง"
          />

          {/* Upper Real-Footage Post Plate: stills/cxm-post-claim.png (y: 438..810, x: 120..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              height: 368,
              borderRadius: 18,
              overflow: 'hidden',
              backgroundColor: '#0A0B0D',
              border: `2px solid ${BL.neon}`,
              boxShadow: '0 14px 36px rgba(0, 0, 0, 0.85), 0 0 22px rgba(255, 45, 64, 0.45)',
              zIndex: 55,
              transform: `scale(${lerp(0.96, 1.0, expoProgress(frame, 30, 8)).toFixed(4)})`,
            }}
          >
            {/* Dedicated dark credit/claim header bar (52px) so it never covers screenshot text */}
            <div
              style={{
                height: 52,
                backgroundColor: 'rgba(7, 8, 10, 0.96)',
                borderBottom: '1px solid rgba(255, 45, 64, 0.35)',
                padding: '0 18px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 18,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                หลักฐานโพสต์ต้นทาง · ตามที่เจ้าของโพสต์เล่า
              </span>
              <span
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 15,
                  color: BL.white,
                  backgroundColor: 'rgba(255, 45, 64, 0.25)',
                  border: `1px solid ${BL.neon}`,
                  borderRadius: 6,
                  padding: '2px 10px',
                  whiteSpace: 'nowrap',
                }}
              >
                CLAIM EVIDENCE #1
              </span>
            </div>

            {/* White screenshot viewport (316px tall, mapping y=758..1162 of 1080x1920 still) */}
            <div
              style={{
                position: 'relative',
                width: 840,
                height: 316,
                backgroundColor: '#FFFFFF',
                overflow: 'hidden',
              }}
            >
              <Img
                src={staticFile('stills/cxm-post-claim.png')}
                style={{
                  width: 840,
                  height: 1493,
                  marginTop: -590,
                  display: 'block',
                }}
              />
              {/* Yellow Highlighter Bar sweeping across "ถือออเดอร์นานถึง 2 ชั่วโมง" (Line 3: top 144px, left 448px) */}
              <div
                style={{
                  position: 'absolute',
                  left: 448,
                  top: 144,
                  width: 350,
                  height: 38,
                  backgroundColor: BL.yellow,
                  mixBlendMode: 'multiply',
                  borderRadius: 6,
                  transform: `scaleX(${expoProgress(frame, 34, 11).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
            </div>
          </div>

          {/* Lower-Right Stat Card (x: 452..840, y: 850..1270) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 850,
              width: 388,
              height: 420,
              backgroundColor: BL.scrim,
              borderLeft: `6px solid ${BL.yellow}`,
              borderTop: '1px solid rgba(244, 223, 20, 0.35)',
              borderRight: '1px solid rgba(244, 223, 20, 0.35)',
              borderBottom: '1px solid rgba(244, 223, 20, 0.35)',
              borderRadius: 18,
              padding: '22px 22px',
              boxShadow: '0 16px 36px rgba(0, 0, 0, 0.82)',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              clipPath: wipeClip(frame, 32, 10),
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 17,
                  color: BL.muted,
                  letterSpacing: '0.08em',
                  whiteSpace: 'nowrap',
                }}
              >
                ORDER HOLD DURATION
              </div>
              {/* Animated digital timer ramping up to 02:00:00 */}
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 54,
                  fontWeight: 800,
                  color: BL.white,
                  letterSpacing: '0.03em',
                  marginTop: 4,
                  whiteSpace: 'nowrap',
                }}
              >
                {(() => {
                  const p = expoProgress(frame, 32, 18);
                  const mins = Math.round(lerp(0, 120, p));
                  const hh = Math.floor(mins / 60)
                    .toString()
                    .padStart(2, '0');
                  const mm = (mins % 60).toString().padStart(2, '0');
                  return `${hh}:${mm}:00`;
                })()}
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'rgba(244, 223, 20, 0.14)',
                border: `1.5px solid ${BL.yellow}`,
                borderRadius: 12,
                padding: '10px 16px',
              }}
            >
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 60,
                  fontWeight: 800,
                  color: BL.yellow,
                  textShadow: BL.textGlowYellow,
                  lineHeight: 1.15,
                  whiteSpace: 'nowrap',
                }}
              >
                2 ชั่วโมง
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 21,
                  color: BL.white,
                  marginTop: 4,
                  whiteSpace: 'nowrap',
                }}
              >
                เทรดทองผ่านมือถือด้วยตัวเอง
              </div>
            </div>

            <div
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 18,
                color: BL.muted,
                whiteSpace: 'nowrap',
              }}
            >
              อ้างอิง: ตามที่เจ้าของโพสต์เล่า
            </div>
          </div>
        </>
      )}

      {/* SHOT 3 (2.3–3.6s, frames 69..108): "...แต่โดนข้อหาเทรดเร็วเกินไป?" */}
      {frame >= 69 && frame < 108 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={69}
            tag="ข้อกล่าวหาที่ขัดแย้ง · ตามที่เจ้าของโพสต์เล่า"
            headline="ถือ 120 นาทีเต็ม"
            accentWord="แต่หาว่าเร็ว?!"
          />

          {/* Upper Kinetic Contradiction Box (y: 438..820, x: 120..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              height: 382,
              backgroundColor: 'rgba(7, 8, 10, 0.92)',
              border: `2px solid ${BL.neon}`,
              boxShadow: BL.glowM,
              borderRadius: 18,
              padding: '20px 28px',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <CornerBrackets color={BL.neon} size={22} thickness={4} />

            {/* Top row: 2 hours vs strike */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                borderRadius: 12,
                padding: '10px 18px',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 32,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                ผู้โพสต์ยืนยัน: ถือออเดอร์ 2 ชั่วโมง
              </span>
              <span
                style={{
                  backgroundColor: 'rgba(244, 223, 20, 0.18)',
                  border: `1px solid ${BL.yellow}`,
                  color: BL.yellow,
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 20,
                  padding: '4px 12px',
                  borderRadius: 8,
                  whiteSpace: 'nowrap',
                }}
              >
                HOLD: 120 MIN
              </span>
            </div>

            {/* Center punchline: ข้อหา: เทรดเร็วเกินไป?! */}
            <div style={{ position: 'relative', padding: '2px 0' }}>
              <div
                style={{
                  clipPath: wipeClip(frame, 70, 9),
                  fontFamily: FONT_KANIT_800,
                  fontSize: 66,
                  fontWeight: 800,
                  color: BL.neon,
                  textShadow: BL.textGlowNeon,
                  lineHeight: 1.2,
                  whiteSpace: 'nowrap',
                }}
              >
                ข้อหา: เทรดเร็วเกินไป?!
              </div>
              {/* Animated neon underline sweep */}
              <div
                style={{
                  width: '100%',
                  height: 5,
                  backgroundColor: BL.neon,
                  boxShadow: BL.glowM,
                  borderRadius: 3,
                  marginTop: 6,
                  transform: `scaleX(${expoProgress(frame, 73, 12).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
            </div>

            {/* Bottom strip: cropped Line 5 of stills/cxm-post-claim.png with yellow highlight */}
            <div
              style={{
                position: 'relative',
                width: 784,
                height: 62,
                borderRadius: 10,
                overflow: 'hidden',
                backgroundColor: '#FFFFFF',
                border: '1px solid rgba(255, 255, 255, 0.35)',
              }}
            >
              <Img
                src={staticFile('stills/cxm-post-claim.png')}
                style={{
                  width: 784,
                  height: 1394,
                  marginTop: -756,
                  display: 'block',
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  left: 20,
                  top: 12,
                  width: 650,
                  height: 36,
                  backgroundColor: BL.yellow,
                  mixBlendMode: 'multiply',
                  borderRadius: 5,
                  transform: `scaleX(${expoProgress(frame, 74, 12).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
            </div>
          </div>

          {/* Lower-Right Contradiction Checklist Card (x: 452..840, y: 850..1270) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 850,
              width: 388,
              height: 420,
              backgroundColor: BL.scrim,
              borderLeft: `6px solid ${BL.neon}`,
              borderRadius: 18,
              padding: '22px 22px',
              boxShadow: '0 16px 36px rgba(0, 0, 0, 0.85)',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              clipPath: wipeClip(frame, 72, 10),
            }}
          >
            <div
              style={{
                backgroundColor: 'rgba(255, 45, 64, 0.18)',
                border: `1.5px solid ${BL.neon}`,
                borderRadius: 10,
                padding: '8px 14px',
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 20,
                color: BL.neon,
                textAlign: 'center',
                boxShadow: BL.glowS,
                whiteSpace: 'nowrap',
              }}
            >
              RULE VIOLATION CLAIM?
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  borderRadius: 12,
                  padding: '12px 14px',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 19,
                    color: BL.muted,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ฝั่งผู้โพสต์ระบุ
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 30,
                    color: BL.yellow,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ถือออเดอร์ 2 ชั่วโมง
                </div>
              </div>

              <div
                style={{
                  backgroundColor: 'rgba(255, 45, 64, 0.14)',
                  border: `1px solid ${BL.neon}`,
                  borderRadius: 12,
                  padding: '12px 14px',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 19,
                    color: BL.white,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ฝั่งโบรกเกอร์ CXM อ้าง
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 30,
                    color: BL.neon,
                    whiteSpace: 'nowrap',
                  }}
                >
                  เทรดเร็วเกินไป (ผิดกฎ)
                </div>
              </div>
            </div>

            <div
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 18,
                color: BL.muted,
                textAlign: 'right',
                whiteSpace: 'nowrap',
              }}
            >
              ข้อมูลตามที่เจ้าของโพสต์เล่า
            </div>
          </div>
        </>
      )}

      {/* SHOT 4 (3.6–5.0s, frames 108..150): "เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไร..." */}
      {frame >= 108 && frame < 150 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={108}
            tag="เปิดบัญชี Cent · ตามที่เจ้าของโพสต์เล่า"
            headline="เธอเล่าว่าโบรกเกอร์"
            accentWord="CXM ไม่จ่ายกำไร"
          />

          {/* Upper Real-Footage Post Plate: stills/cxm-post-account.png (y: 438..806, x: 120..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              height: 368,
              borderRadius: 18,
              overflow: 'hidden',
              backgroundColor: '#0A0B0D',
              border: `2px solid ${BL.yellow}`,
              boxShadow: '0 14px 36px rgba(0, 0, 0, 0.85)',
              zIndex: 55,
              transform: `scale(${lerp(0.96, 1.0, expoProgress(frame, 108, 8)).toFixed(4)})`,
            }}
          >
            {/* Dedicated dark credit/claim header bar (52px) */}
            <div
              style={{
                height: 52,
                backgroundColor: 'rgba(7, 8, 10, 0.96)',
                borderBottom: '1px solid rgba(244, 223, 20, 0.40)',
                padding: '0 18px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 18,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                โพสต์ต้นทาง · เปิดบัญชี Cent กับโบรกเกอร์ CXM Direct
              </span>
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 16,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                ตามที่เจ้าของโพสต์เล่า
              </span>
            </div>

            {/* White screenshot viewport (316px tall, mapping y=758..1162 of cxm-post-account.png) */}
            <div
              style={{
                position: 'relative',
                width: 840,
                height: 316,
                backgroundColor: '#FFFFFF',
                overflow: 'hidden',
              }}
            >
              <Img
                src={staticFile('stills/cxm-post-account.png')}
                style={{
                  width: 840,
                  height: 1493,
                  marginTop: -590,
                  display: 'block',
                }}
              />
              {/* Yellow Highlighter 1 on "โบรกเกอร์ CXM Direct" (Line 2: top 60px, left 22px) */}
              <div
                style={{
                  position: 'absolute',
                  left: 22,
                  top: 60,
                  width: 285,
                  height: 38,
                  backgroundColor: BL.yellow,
                  mixBlendMode: 'multiply',
                  borderRadius: 6,
                  transform: `scaleX(${expoProgress(frame, 111, 10).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
              {/* Yellow Highlighter 2 on "มาทวงถามกำไรจากโบรกเกอร์!" (Line 6: top 252px, left 22px) */}
              <div
                style={{
                  position: 'absolute',
                  left: 22,
                  top: 252,
                  width: 365,
                  height: 38,
                  backgroundColor: BL.yellow,
                  mixBlendMode: 'multiply',
                  borderRadius: 6,
                  transform: `scaleX(${expoProgress(frame, 120, 12).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
            </div>
          </div>

          {/* Lower-Right Broker Dossier Card (x: 452..840, y: 850..1270) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 850,
              width: 388,
              height: 420,
              backgroundColor: BL.scrim,
              borderLeft: `6px solid ${BL.neon}`,
              borderRadius: 18,
              padding: '22px 22px',
              boxShadow: '0 16px 36px rgba(0, 0, 0, 0.85)',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              clipPath: wipeClip(frame, 110, 10),
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 16,
                  color: BL.muted,
                  letterSpacing: '0.08em',
                  whiteSpace: 'nowrap',
                }}
              >
                NAMED BROKER IN POST
              </div>
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 72,
                  fontWeight: 800,
                  color: BL.neon,
                  textShadow: BL.textGlowNeon,
                  lineHeight: 1.05,
                  marginTop: 4,
                  whiteSpace: 'nowrap',
                }}
              >
                CXM
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 22,
                  color: BL.white,
                  marginTop: 4,
                  whiteSpace: 'nowrap',
                }}
              >
                บัญชี Cent · CXM Direct
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'rgba(255, 45, 64, 0.16)',
                border: `1.5px solid ${BL.neon}`,
                borderRadius: 12,
                padding: '12px 16px',
              }}
            >
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 32,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                ปฏิเสธจ่ายกำไร
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 20,
                  color: BL.yellow,
                  marginTop: 2,
                  whiteSpace: 'nowrap',
                }}
              >
                เงินทุนส่วนตัว (ย้ายจาก Prop Firm)
              </div>
            </div>

            <div
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 18,
                color: BL.muted,
                whiteSpace: 'nowrap',
              }}
            >
              สถานะ: คำบอกเล่าของผู้โพสต์
            </div>
          </div>
        </>
      )}

      {/* SHOT 5 (5.0–6.4s, frames 150..192): "...เกือบหกล้านบาท" */}
      {frame >= 150 && frame < 192 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={150}
            tag="ยอดกำไรที่มีปัญหา · ตามที่เจ้าของโพสต์เล่า"
            headline="CXM ปฏิเสธจ่ายกำไร"
            accentWord="เกือบ 6 ล้านบาท!"
          />

          {/* Upper Giant Profit Counter Card (y: 438..820, x: 120..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              height: 382,
              backgroundColor: 'rgba(7, 8, 10, 0.92)',
              border: `2.5px solid ${BL.yellow}`,
              boxShadow: '0 18px 44px rgba(0, 0, 0, 0.90), 0 0 32px rgba(244, 223, 20, 0.32)',
              borderRadius: 20,
              padding: '20px 30px',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <CornerBrackets color={BL.yellow} size={22} thickness={4} />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 26,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                ยอดกำไรบัญชี Cent ที่ผู้โพสต์อ้างว่าถูกปฏิเสธ
              </span>
              <span
                style={{
                  backgroundColor: BL.neon,
                  color: BL.white,
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 20,
                  padding: '4px 14px',
                  borderRadius: 8,
                  boxShadow: BL.glowS,
                  whiteSpace: 'nowrap',
                }}
              >
                PAYOUT REFUSED
              </span>
            </div>

            {/* Massive animated Baht counter + Thai headline */}
            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                justifyContent: 'space-between',
                clipPath: wipeClip(frame, 150, 8),
              }}
            >
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 76,
                  fontWeight: 800,
                  color: BL.yellow,
                  textShadow: BL.textGlowYellow,
                  lineHeight: 1.12,
                  whiteSpace: 'nowrap',
                }}
              >
                เกือบ 6 ล้านบาท
              </div>
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 44,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                {(() => {
                  const p = expoProgress(frame, 150, 20);
                  const val = Math.round(lerp(1200000, 6000000, p));
                  return `~฿${val.toLocaleString('en-US')}`;
                })()}
              </div>
            </div>

            {/* Cropped proof strip from stills/cxm-post-claim.png showing Line 1 & Line 2 */}
            <div
              style={{
                position: 'relative',
                width: 776,
                height: 106,
                borderRadius: 10,
                overflow: 'hidden',
                backgroundColor: '#FFFFFF',
                border: '1px solid rgba(255, 255, 255, 0.35)',
              }}
            >
              <Img
                src={staticFile('stills/cxm-post-claim.png')}
                style={{
                  width: 776,
                  height: 1380,
                  marginTop: -545,
                  display: 'block',
                }}
              />
              {/* Yellow highlight on "กำไรบัญชี Cent เกือบ 6 ล้านบาท!" */}
              <div
                style={{
                  position: 'absolute',
                  left: 22,
                  top: 64,
                  width: 365,
                  height: 34,
                  backgroundColor: BL.yellow,
                  mixBlendMode: 'multiply',
                  borderRadius: 5,
                  transform: `scaleX(${expoProgress(frame, 154, 12).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
            </div>
          </div>

          {/* Lower-Right Red Lock Status Card (x: 452..840, y: 850..1270) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 850,
              width: 388,
              height: 420,
              backgroundColor: BL.scrim,
              borderLeft: `6px solid ${BL.yellow}`,
              borderRadius: 18,
              padding: '22px 22px',
              boxShadow: '0 16px 36px rgba(0, 0, 0, 0.85)',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              clipPath: wipeClip(frame, 152, 10),
            }}
          >
            <div
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 18,
                color: BL.neon,
                letterSpacing: '0.06em',
                whiteSpace: 'nowrap',
              }}
            >
              WITHDRAWAL BLOCKED · CXM
            </div>

            <div>
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 22,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                เทรดได้กำไรก้อนใหญ่
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 52,
                  color: BL.neon,
                  textShadow: BL.textGlowNeon,
                  lineHeight: 1.2,
                  marginTop: 4,
                  whiteSpace: 'nowrap',
                }}
              >
                ไม่จ่ายกำไร!
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                borderRadius: 12,
                padding: '12px 14px',
              }}
            >
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 20,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                &ldquo;ถ้าขาดทุนรับผิดชอบเอง
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 20,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                แต่พอได้กำไรกลับต้องมาทวงถาม!&rdquo;
              </div>
            </div>
          </div>
        </>
      )}

      {/* SHOT 6 (6.4–7.8s, frames 192..234): "ซีเอ็กซ์เอ็มแจ้งในอีเมลว่า..." (Full-Frame Return -> Shrink) */}
      {frame >= 192 && frame < 234 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={192}
            tag="คำชี้แจงจากโบรกเกอร์ · ตามที่เจ้าของโพสต์เล่า"
            headline="CXM ส่งอีเมลแจ้ง"
            accentWord="เหตุผลที่ไม่จ่าย!"
          />

          {/* Incoming Email Alert Banner (sits at y: 438..595, above full-frame avatar beanie at y >= 615) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              backgroundColor: 'rgba(7, 8, 10, 0.92)',
              border: `2px solid ${BL.neon}`,
              boxShadow: BL.glowM,
              borderRadius: 18,
              padding: '16px 26px',
              zIndex: 65,
              clipPath: wipeClip(frame, 192, 9),
            }}
          >
            <CornerBrackets color={BL.neon} size={18} thickness={3} />
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid rgba(255, 45, 64, 0.32)',
                paddingBottom: 8,
                marginBottom: 8,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span
                  style={{
                    backgroundColor: BL.neon,
                    color: BL.white,
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 18,
                    padding: '3px 10px',
                    borderRadius: 6,
                    whiteSpace: 'nowrap',
                  }}
                >
                  EMAIL NOTICE
                </span>
                <span
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 22,
                    color: BL.white,
                    whiteSpace: 'nowrap',
                  }}
                >
                  FROM: CXM BROKER COMPLIANCE
                </span>
              </div>
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 18,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                ตามที่เจ้าของโพสต์เล่า
              </span>
            </div>

            <div
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 42,
                color: BL.white,
                lineHeight: 1.24,
                whiteSpace: 'nowrap',
              }}
            >
              แจ้งในอีเมลว่าออเดอร์นี้เข้าข่าย{' '}
              <span style={{ color: BL.neon, textShadow: BL.textGlowNeon }}>
                &ldquo;เทรดผิดกฎ&rdquo;
              </span>
            </div>
          </div>

          {/* Chest-level Email Dossier Stamp (y: 1055..1268, below avatar face y: 615..960) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 1045,
              width: 388,
              backgroundColor: 'rgba(7, 8, 10, 0.90)',
              borderLeft: `6px solid ${BL.yellow}`,
              borderTop: '1px solid rgba(244, 223, 20, 0.35)',
              borderRight: '1px solid rgba(244, 223, 20, 0.35)',
              borderBottom: '1px solid rgba(244, 223, 20, 0.35)',
              borderRadius: 16,
              padding: '16px 20px',
              boxShadow: '0 14px 32px rgba(0, 0, 0, 0.85)',
              zIndex: 65,
              clipPath: wipeClip(frame, 196, 10),
            }}
          >
            <div
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 16,
                color: BL.yellow,
                letterSpacing: '0.06em',
                whiteSpace: 'nowrap',
              }}
            >
              SUBJECT: ACCOUNT CENT REVIEW
            </div>
            <div
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 32,
                color: BL.white,
                marginTop: 4,
                whiteSpace: 'nowrap',
              }}
            >
              ระบุข้อหาในอีเมลชัดเจน
            </div>
            <div
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 20,
                color: BL.neon,
                marginTop: 2,
                whiteSpace: 'nowrap',
              }}
            >
              ปฏิเสธจ่ายกำไรเกือบ 6 ล้านบาท
            </div>
          </div>
        </>
      )}

      {/* SHOT 7 (7.8–9.3s, frames 234..279): "...เป็นท็อกซิกเทรดดิ้ง" */}
      {frame >= 234 && frame < 279 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={234}
            tag="ข้อหาในอีเมล CXM · ตามที่เจ้าของโพสต์เล่า"
            headline="ตราหน้าออเดอร์ว่าเป็น"
            accentWord="TOXIC TRADING!"
          />

          {/* Upper Giant Accusation Box (y: 438..820, x: 120..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              height: 382,
              backgroundColor: 'rgba(7, 8, 10, 0.92)',
              border: `3px solid ${BL.neon}`,
              boxShadow: BL.glowL,
              borderRadius: 20,
              padding: '22px 32px',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              transform: `scale(${lerp(0.94, 1.0, expoProgress(frame, 234, 7)).toFixed(4)})`,
            }}
          >
            <CornerBrackets color={BL.yellow} size={24} thickness={4} />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span
                style={{
                  backgroundColor: 'rgba(255, 45, 64, 0.22)',
                  border: `1.5px solid ${BL.neon}`,
                  color: BL.neon,
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 20,
                  padding: '4px 14px',
                  borderRadius: 8,
                  whiteSpace: 'nowrap',
                }}
              >
                EMAIL VERDICT · CXM
              </span>
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 22,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                ข้อหาที่แจ้งในอีเมล (ตามโพสต์)
              </span>
            </div>

            <div
              style={{
                clipPath: wipeClip(frame, 234, 8),
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 82,
                fontWeight: 800,
                color: BL.neon,
                textShadow: BL.textGlowNeon,
                letterSpacing: '0.02em',
                lineHeight: 1.08,
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              &ldquo;TOXIC TRADING&rdquo;
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                borderRadius: 12,
                padding: '12px 20px',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 28,
                  color: BL.white,
                  whiteSpace: 'nowrap',
                }}
              >
                อ้างว่าเทรดเร็วเกินไป
              </span>
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 28,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                ทั้งที่ถือออเดอร์นาน 2 ชั่วโมง!
              </span>
            </div>
          </div>

          {/* Lower-Right Post Evidence from stills/cxm-post-full.png (scaled down to 388px width, showing only lower text y: 650..1820) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 850,
              width: 388,
              height: 420,
              borderRadius: 18,
              overflow: 'hidden',
              backgroundColor: '#0A0B0D',
              border: `2px solid ${BL.neon}`,
              boxShadow: '0 16px 36px rgba(0, 0, 0, 0.85)',
              zIndex: 55,
              clipPath: wipeClip(frame, 236, 10),
            }}
          >
            <div
              style={{
                height: 44,
                backgroundColor: 'rgba(7, 8, 10, 0.96)',
                borderBottom: '1px solid rgba(255, 45, 64, 0.40)',
                padding: '0 14px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 16,
                  color: BL.yellow,
                  whiteSpace: 'nowrap',
                }}
              >
                ลำดับเหตุการณ์ · ตามที่เจ้าของโพสต์เล่า
              </span>
            </div>
            <div
              style={{
                position: 'relative',
                width: 388,
                height: 376,
                backgroundColor: '#FFFFFF',
                overflow: 'hidden',
              }}
            >
              <Img
                src={staticFile('stills/cxm-post-full.png')}
                style={{
                  width: 388,
                  height: 690,
                  marginTop: -238,
                  display: 'block',
                }}
              />
              {/* Yellow highlight on "22 กันยายน 2026 วันที่เรื่องทั้งหมดเริ่มต้น" */}
              <div
                style={{
                  position: 'absolute',
                  left: 12,
                  top: 325,
                  width: 265,
                  height: 26,
                  backgroundColor: BL.yellow,
                  mixBlendMode: 'multiply',
                  borderRadius: 4,
                  transform: `scaleX(${expoProgress(frame, 240, 12).toFixed(3)})`,
                  transformOrigin: 'left center',
                }}
              />
            </div>
          </div>
        </>
      )}

      {/* SHOT 8 (9.3–10.0s, frames 279..300): Silence / Final Dossier Summary Board */}
      {frame >= 279 && (
        <>
          <TopClaimBanner
            frame={frame}
            beatStart={279}
            tag="สรุปประเด็นดราม่า · ตามที่เจ้าของโพสต์เล่า"
            headline="เคสโบรกเกอร์ CXM"
            accentWord="ไม่จ่ายกำไร 6 ล้าน?"
          />

          {/* Upper 3-Row Summary Board (y: 438..820, x: 120..960) */}
          <div
            style={{
              position: 'absolute',
              left: BL.safeLeft,
              top: 438,
              width: 840,
              height: 382,
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            {[
              {
                idx: '01',
                label: 'เวลาถือออเดอร์ (ตามโพสต์)',
                val: '2 ชั่วโมง',
                color: BL.yellow,
                delay: 0,
              },
              {
                idx: '02',
                label: 'ยอดกำไรบัญชี Cent ที่ CXM ปฏิเสธ',
                val: 'เกือบ 6 ล้านบาท',
                color: BL.yellow,
                delay: 3,
              },
              {
                idx: '03',
                label: 'ข้อหาที่ CXM แจ้งในอีเมล',
                val: '"TOXIC TRADING"',
                color: BL.neon,
                delay: 6,
              },
            ].map((row) => (
              <div
                key={row.idx}
                style={{
                  clipPath: wipeClip(frame, 279 + row.delay, 7),
                  backgroundColor: 'rgba(7, 8, 10, 0.92)',
                  borderLeft: `6px solid ${row.color}`,
                  borderTop: '1px solid rgba(255, 255, 255, 0.14)',
                  borderRight: '1px solid rgba(255, 255, 255, 0.14)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.14)',
                  borderRadius: 14,
                  padding: '16px 24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  boxShadow: '0 10px 26px rgba(0, 0, 0, 0.80)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span
                    style={{
                      fontFamily: FONT_ARCHIVO_800,
                      fontSize: 24,
                      color: BL.ink,
                      backgroundColor: row.color,
                      padding: '2px 10px',
                      borderRadius: 6,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {row.idx}
                  </span>
                  <span
                    style={{
                      fontFamily: FONT_KANIT_600,
                      fontSize: 28,
                      color: BL.white,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {row.label}
                  </span>
                </div>
                <span
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 42,
                    fontWeight: 800,
                    color: row.color,
                    textShadow: row.color === BL.neon ? BL.textGlowNeon : BL.textGlowYellow,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {row.val}
                </span>
              </div>
            ))}
          </div>

          {/* Lower-Right Final Stamp Card (x: 452..840, y: 850..1270) */}
          <div
            style={{
              position: 'absolute',
              left: 452,
              top: 850,
              width: 388,
              height: 420,
              backgroundColor: BL.scrim,
              border: `2px solid ${BL.neon}`,
              boxShadow: BL.glowM,
              borderRadius: 18,
              padding: '22px 22px',
              zIndex: 55,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              clipPath: wipeClip(frame, 280, 8),
            }}
          >
            <CornerBrackets color={BL.yellow} size={18} thickness={3} />
            <div
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 18,
                color: BL.yellow,
                letterSpacing: '0.06em',
                whiteSpace: 'nowrap',
              }}
            >
              BLACK LIQUIDITY · EP.62
            </div>

            <div>
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 64,
                  color: BL.neon,
                  textShadow: BL.textGlowNeon,
                  lineHeight: 1.05,
                  whiteSpace: 'nowrap',
                }}
              >
                CXM
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 32,
                  color: BL.white,
                  marginTop: 6,
                  whiteSpace: 'nowrap',
                }}
              >
                ดราม่าปฏิเสธจ่ายกำไร
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'rgba(244, 223, 20, 0.14)',
                border: `1px solid ${BL.yellow}`,
                borderRadius: 10,
                padding: '10px 14px',
                fontFamily: FONT_KANIT_600,
                fontSize: 20,
                color: BL.yellow,
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              ตามที่เจ้าของโพสต์เล่า
            </div>
          </div>
        </>
      )}

      {/* =====================================================================
          STANDING CHANNEL OVERLAYS (CaptionBand, BrandBug, LegalLabel)
          ===================================================================== */}
      <CaptionBand frame={frame} />
      <BrandBug />
      <LegalLabel />
    </AbsoluteFill>
  );
};
