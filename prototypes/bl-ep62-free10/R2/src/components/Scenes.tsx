import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { FONT_ARCHIVO_800, FONT_KANIT_600, FONT_KANIT_800 } from '../fonts';
import {
  BrollBackground,
  PostEvidenceCard,
  SyncedPresenter,
} from './MediaElements';

/**
 * SHOT 1 (0.0s - 1.0s | Frames 0 - 30):
 * Immediate scroll-stopping hook. Frame 0 is already fully composed and high-impact.
 */
export const Shot1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Frame 0 is already visible (starts at 0.96 scale -> 1.0) so thumbnail / frame 0 stops the scroll
  const punch = spring({
    frame: frame + 3,
    fps,
    config: { damping: 12, stiffness: 220, mass: 0.6 },
  });

  const scaleHero = interpolate(punch, [0, 1], [0.94, 1]);
  const shakeX = frame < 8 ? Math.sin(frame * 2.4) * 5 : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      {/* Presenter full-frame synced to 0.0s - 1.0s */}
      <SyncedPresenter
        startFrame={0}
        durationInFrames={30}
        mode="full-frame"
        zoomFrom={1.04}
        zoomTo={1.12}
      />

      {/* Crimson danger B-roll blend */}
      <AbsoluteFill style={{ opacity: 0.28 }}>
        <BrollBackground
          file="broll/red-forbidden-icon-glow.mp4"
          durationInFrames={30}
          playbackRate={1.5}
          zoomFrom={1.05}
          zoomTo={1.18}
          opacity={0.75}
          tint="crimson"
        />
      </AbsoluteFill>

      {/* Cropped Facebook Post Claim Card (y: 556..942) */}
      <PostEvidenceCard
        variant="claim"
        top={556}
        left={48}
        width={884}
        rotateDeg={-1.4}
        highlightTop={14}
        highlightHeight={98}
        highlightDelay={0}
        badgeText="ดราม่าเทรดเดอร์สาว · ตามที่เจ้าของโพสต์เล่า"
      />

      {/* Scroll-Stopper Headline Block (Safe zone: x 48..932, y 962..1395) */}
      <div
        style={{
          position: 'absolute',
          top: 962,
          left: 48,
          width: 884,
          transform: `translateX(${shakeX}px) scale(${scaleHero})`,
          transformOrigin: '0% 50%',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {/* Top Kicker */}
        <div
          style={{
            alignSelf: 'flex-start',
            backgroundColor: '#FFB800',
            color: '#050507',
            borderRadius: 10,
            padding: '6px 18px',
            boxShadow: '0 8px 24px rgba(255, 184, 0, 0.4)',
          }}
        >
          <span
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 28,
              whiteSpace: 'nowrap',
              display: 'block',
              lineHeight: 1.15,
            }}
          >
            เรื่องเล่าจากผู้โพสต์ · เทรดทองบัญชี Cent
          </span>
        </div>

        {/* Main Number Hook */}
        <div
          style={{
            backgroundColor: 'rgba(8, 8, 12, 0.92)',
            border: '2.5px solid #FFB800',
            borderLeft: '12px solid #FFB800',
            borderRadius: 18,
            padding: '14px 24px',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.9)',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 74,
              color: '#FFB800',
              whiteSpace: 'nowrap',
              lineHeight: 1.05,
              textShadow: '0 6px 24px rgba(255, 184, 0, 0.45)',
            }}
          >
            กำไรเกือบ 6 ล้านบาท!
          </div>
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 56,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              lineHeight: 1.12,
              marginTop: 6,
            }}
          >
            ถือ 2 ชม. แต่ <span style={{ color: '#FF1E27' }}>CXM</span> ไม่จ่าย?!
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 2 (1.0s - 2.2s | Frames 30 - 66):
 * Voice: "ถือออเดอร์สองชั่วโมง..."
 */
export const Shot2HoldTwoHours: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slam = spring({
    frame,
    fps,
    config: { damping: 13, stiffness: 200, mass: 0.65 },
  });

  // Stopwatch counts from 00:00:00 to 02:00:00 in the first 22 frames
  const totalMinutes = Math.round(
    interpolate(frame, [0, 22], [0, 120], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    })
  );
  const hoursStr = String(Math.floor(totalMinutes / 60)).padStart(2, '0');
  const minsStr = String(totalMinutes % 60).padStart(2, '0');
  const ringProgress = interpolate(frame, [0, 24], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      <BrollBackground
        file="broll/hourglass-red-sand.mp4"
        durationInFrames={36}
        playbackRate={1.35}
        zoomFrom={1.03}
        zoomTo={1.16}
        tint="gold"
      />

      {/* Left HUD: 2-Hour Order Hold Timer */}
      <div
        style={{
          position: 'absolute',
          top: 156,
          left: 48,
          width: 476,
          height: 670,
          borderRadius: 24,
          backgroundColor: 'rgba(8, 8, 13, 0.88)',
          border: '2px solid rgba(255, 184, 0, 0.7)',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.85)',
          padding: 26,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          transform: `translateY(${interpolate(slam, [0, 1], [40, 0])}px)`,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255, 184, 0, 0.3)',
            paddingBottom: 14,
          }}
        >
          <span
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 20,
              color: '#FFB800',
              letterSpacing: 1.5,
              whiteSpace: 'nowrap',
            }}
          >
            ORDER HOLD TIMER
          </span>
          <span
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 18,
              color: '#94A3B8',
              whiteSpace: 'nowrap',
            }}
          >
            XAUUSD · GOLD
          </span>
        </div>

        {/* Circular Progress Dial */}
        <div
          style={{
            alignSelf: 'center',
            width: 310,
            height: 310,
            borderRadius: '50%',
            background: `conic-gradient(#FFB800 ${ringProgress}%, rgba(255, 255, 255, 0.08) ${ringProgress}%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 40px rgba(255, 184, 0, 0.25)',
          }}
        >
          <div
            style={{
              width: 266,
              height: 266,
              borderRadius: '50%',
              backgroundColor: '#07070B',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 58,
                color: '#FFFFFF',
                letterSpacing: 1,
                whiteSpace: 'nowrap',
              }}
            >
              {hoursStr}:{minsStr}:00
            </span>
            <span
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 32,
                color: '#FFB800',
                whiteSpace: 'nowrap',
                marginTop: 4,
              }}
            >
              2 ชั่วโมงเต็ม
            </span>
          </div>
        </div>

        <div
          style={{
            backgroundColor: 'rgba(255, 184, 0, 0.14)',
            border: '1px solid rgba(255, 184, 0, 0.5)',
            borderRadius: 14,
            padding: '12px 16px',
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 22,
              color: '#F8FAFC',
              whiteSpace: 'nowrap',
            }}
          >
            เทรดทองผ่านมือถือ (ตามโพสต์)
          </span>
        </div>
      </div>

      {/* Right Presenter Card Synced to Frame 30..66 (1.0s - 2.2s) */}
      <SyncedPresenter
        startFrame={30}
        durationInFrames={36}
        mode="card-right"
        label="ตามที่เจ้าของโพสต์เล่า"
      />

      {/* Spoken Beat Kinetic Typography (y: 860..1390, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 862,
          left: 48,
          width: 884,
          transform: `scale(${interpolate(slam, [0, 1], [0.88, 1])})`,
          transformOrigin: '0% 50%',
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(7, 7, 11, 0.94)',
            border: '3px solid #FFB800',
            borderRadius: 22,
            padding: '22px 28px',
            boxShadow: '0 24px 60px rgba(0, 0, 0, 0.92)',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 34,
              color: '#CBD5E1',
              whiteSpace: 'nowrap',
            }}
          >
            เธอเล่าว่าเทรดทองด้วยตัวเอง...
          </div>
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 88,
              color: '#FFB800',
              whiteSpace: 'nowrap',
              lineHeight: 1.05,
              marginTop: 6,
              textShadow: '0 6px 28px rgba(255, 184, 0, 0.4)',
            }}
          >
            “ถือออเดอร์ 2 ชั่วโมง”
          </div>
          <div
            style={{
              marginTop: 14,
              display: 'inline-block',
              backgroundColor: 'rgba(255, 30, 39, 0.2)',
              border: '1.5px solid #FF1E27',
              borderRadius: 10,
              padding: '6px 18px',
            }}
          >
            <span
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 28,
                color: '#F8FAFC',
                whiteSpace: 'nowrap',
              }}
            >
              ไม่ใช่การสแกลปปิ้งระดับเสี้ยววินาที!
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 3 (2.2s - 3.6s | Frames 66 - 108):
 * Voice: "...แต่โดนข้อหาเทรดเร็วเกินไป?"
 */
export const Shot3TooFastAccusation: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titlePop = spring({
    frame,
    fps,
    config: { damping: 11, stiffness: 230, mass: 0.6 },
  });

  const slamSecondLine = spring({
    frame: Math.max(0, frame - 6),
    fps,
    config: { damping: 10, stiffness: 260, mass: 0.55 },
  });

  const shakeX =
    frame >= 6 && frame <= 18 ? Math.sin(frame * 2.8) * 8 : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      {/* Rapid B-roll whip cut inside Shot 3 */}
      <Sequence from={0} durationInFrames={21}>
        <BrollBackground
          file="broll/red-digital-countdown.mp4"
          durationInFrames={21}
          playbackRate={1.55}
          zoomFrom={1.04}
          zoomTo={1.18}
          tint="crimson"
        />
      </Sequence>
      <Sequence from={21} durationInFrames={21}>
        <BrollBackground
          file="broll/finger-taps-red-lock.mp4"
          durationInFrames={21}
          playbackRate={1.45}
          zoomFrom={1.06}
          zoomTo={1.18}
          tint="crimson"
        />
      </Sequence>

      {/* Post Evidence Card highlighting the 2-hour & rule violation claim */}
      <PostEvidenceCard
        variant="claim"
        top={152}
        left={48}
        width={936}
        rotateDeg={1.1}
        highlightTop={146}
        highlightHeight={122}
        highlightDelay={2}
        badgeText="โพสต์ต้นทาง: ถือออเดอร์ 2 ชั่วโมง แต่ถูกกล่าวหาว่าเทรดผิดกฎ"
      />

      {/* Paradox Comparison Strip (y: 550..710, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 554,
          left: 48,
          width: 884,
          display: 'flex',
          gap: 18,
          transform: `scale(${interpolate(titlePop, [0, 1], [0.9, 1])})`,
        }}
      >
        <div
          style={{
            flex: 1,
            backgroundColor: 'rgba(10, 10, 16, 0.92)',
            border: '2px solid #FFB800',
            borderRadius: 18,
            padding: '16px 20px',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 22,
              color: '#94A3B8',
              whiteSpace: 'nowrap',
            }}
          >
            ระยะเวลาถือออเดอร์ (ตามโพสต์)
          </div>
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 48,
              color: '#FFB800',
              whiteSpace: 'nowrap',
              marginTop: 4,
            }}
          >
            2 ชั่วโมง
          </div>
        </div>

        <div
          style={{
            flex: 1,
            backgroundColor: 'rgba(35, 6, 10, 0.94)',
            border: '2px solid #FF1E27',
            borderRadius: 18,
            padding: '16px 20px',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 22,
              color: '#FCA5A5',
              whiteSpace: 'nowrap',
            }}
          >
            ข้อหาที่เธอระบุว่าถูกแจ้ง
          </div>
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 48,
              color: '#FF1E27',
              whiteSpace: 'nowrap',
              marginTop: 4,
            }}
          >
            เทรดเร็วเกินไป?!
          </div>
        </div>
      </div>

      {/* Main Kinetic Beat Text (y: 748..1385, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 756,
          left: 48,
          width: 884,
          transform: `translateX(${shakeX}px)`,
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(8, 8, 12, 0.94)',
            border: '2.5px solid rgba(255, 255, 255, 0.25)',
            borderRadius: 22,
            padding: '22px 28px',
            boxShadow: '0 26px 64px rgba(0, 0, 0, 0.92)',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 58,
              color: '#F8FAFC',
              whiteSpace: 'nowrap',
              lineHeight: 1.1,
            }}
          >
            แต่โดนข้อหา...
          </div>

          <div
            style={{
              marginTop: 14,
              backgroundColor: '#FF1E27',
              borderRadius: 16,
              padding: '16px 24px',
              transform: `scale(${interpolate(slamSecondLine, [0, 1], [0.75, 1])})`,
              transformOrigin: '50% 50%',
              boxShadow: '0 14px 40px rgba(255, 30, 39, 0.55)',
            }}
          >
            <div
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 82,
                color: '#FFFFFF',
                whiteSpace: 'nowrap',
                lineHeight: 1.05,
                textAlign: 'center',
              }}
            >
              “เทรดเร็วเกินไป?!”
            </div>
          </div>

          <div
            style={{
              marginTop: 18,
              fontFamily: FONT_KANIT_600,
              fontSize: 32,
              color: '#FFB800',
              whiteSpace: 'nowrap',
              textAlign: 'center',
            }}
          >
            ถือออเดอร์ตั้ง 2 ชั่วโมง... เร็วเกินไปตรงไหน?!
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 4 (3.6s - 5.0s | Frames 108 - 150):
 * Voice: "เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไร..."
 */
export const Shot4CxmRefused: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardEnter = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 210, mass: 0.65 },
  });

  const stampSlam = spring({
    frame: Math.max(0, frame - 8),
    fps,
    config: { damping: 11, stiffness: 260, mass: 0.5 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      {/* Full-bleed Presenter Shot Synced to Frame 108..150 (3.6s - 5.0s) */}
      <SyncedPresenter
        startFrame={108}
        durationInFrames={42}
        mode="full-frame"
        zoomFrom={1.06}
        zoomTo={1.15}
      />

      {/* Post Evidence Card: stills/cxm-post-account.png */}
      <PostEvidenceCard
        variant="account"
        top={536}
        left={48}
        width={884}
        rotateDeg={-1.1}
        highlightTop={22}
        highlightHeight={102}
        highlightDelay={2}
        badgeText="โพสต์ต้นทาง: เปิดบัญชี Cent กับโบรกเกอร์ CXM Direct"
      />

      {/* Spoken Beat Headline (y: 942..1390, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 942,
          left: 48,
          width: 884,
          transform: `translateY(${interpolate(cardEnter, [0, 1], [36, 0])}px)`,
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(7, 7, 12, 0.94)',
            border: '3px solid #FF1E27',
            borderRadius: 22,
            padding: '22px 28px',
            boxShadow: '0 26px 65px rgba(0, 0, 0, 0.92)',
            position: 'relative',
          }}
        >
          <div
            style={{
              display: 'inline-block',
              backgroundColor: 'rgba(255, 184, 0, 0.16)',
              border: '1px solid #FFB800',
              borderRadius: 8,
              padding: '4px 14px',
              marginBottom: 10,
            }}
          >
            <span
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 24,
                color: '#FFB800',
                whiteSpace: 'nowrap',
              }}
            >
              ตามที่เจ้าของโพสต์เล่า
            </span>
          </div>

          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 64,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              lineHeight: 1.08,
            }}
          >
            เธอเล่าว่า <span style={{ color: '#FFB800' }}>CXM</span>
          </div>

          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 86,
              color: '#FF1E27',
              whiteSpace: 'nowrap',
              lineHeight: 1.06,
              marginTop: 4,
              textShadow: '0 6px 26px rgba(255, 30, 39, 0.5)',
            }}
          >
            “ไม่จ่ายกำไร!”
          </div>

          <div
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 28,
              color: '#CBD5E1',
              whiteSpace: 'nowrap',
              marginTop: 10,
            }}
          >
            ขาดทุนรับผิดชอบเอง แต่พอได้กำไรกลับต้องมาทวงถาม!
          </div>

          {/* Stamped PAYOUT REFUSED Seal */}
          <div
            style={{
              position: 'absolute',
              top: 24,
              right: 24,
              border: '4px solid #FF1E27',
              backgroundColor: 'rgba(255, 30, 39, 0.18)',
              borderRadius: 12,
              padding: '8px 18px',
              transform: `rotate(-8deg) scale(${interpolate(
                stampSlam,
                [0, 1],
                [1.8, 1]
              )})`,
              opacity: interpolate(stampSlam, [0, 0.3, 1], [0, 1, 1]),
            }}
          >
            <span
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 28,
                color: '#FF1E27',
                letterSpacing: 2,
                whiteSpace: 'nowrap',
              }}
            >
              REFUSED // CXM
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 5 (5.0s - 6.4s | Frames 150 - 192):
 * Voice: "...เกือบหกล้านบาท"
 */
export const Shot5SixMillionBaht: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pop = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 220, mass: 0.6 },
  });

  // Animated baht counter from 1,500,000 to 5,999,999
  const rawBaht = Math.round(
    interpolate(frame, [0, 20], [1500000, 5999999], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    })
  );
  const formattedBaht = rawBaht.toLocaleString('en-US');

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      <BrollBackground
        file="broll/gold-bar-in-glass-cube.mp4"
        durationInFrames={42}
        playbackRate={1.3}
        zoomFrom={1.02}
        zoomTo={1.18}
        tint="gold"
      />

      {/* Left Presenter Card Synced to Frame 150..192 (5.0s - 6.4s) */}
      <SyncedPresenter
        startFrame={150}
        durationInFrames={42}
        mode="card-left"
        label="ตามโพสต์ · บัญชี Cent"
      />

      {/* Right Vault Payout Dossier Card */}
      <div
        style={{
          position: 'absolute',
          top: 156,
          left: 552,
          width: 480,
          height: 670,
          borderRadius: 24,
          backgroundColor: 'rgba(8, 8, 12, 0.9)',
          border: '2px solid #FFB800',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.88)',
          padding: 24,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <span
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 19,
              color: '#FFB800',
              letterSpacing: 1.5,
              whiteSpace: 'nowrap',
            }}
          >
            CLAIMED PROFIT // CENT ACCOUNT
          </span>
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 34,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              marginTop: 8,
            }}
          >
            ยอดกำไรที่ผู้โพสต์ระบุ
          </div>
        </div>

        <div
          style={{
            backgroundColor: 'rgba(255, 184, 0, 0.12)',
            border: '2px solid #FFB800',
            borderRadius: 18,
            padding: '22px 18px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 52,
              color: '#FFB800',
              whiteSpace: 'nowrap',
            }}
          >
            ฿{formattedBaht}
          </div>
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 40,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              marginTop: 6,
            }}
          >
            เกือบ 6,000,000 บาท
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#FF1E27',
            borderRadius: 14,
            padding: '14px 16px',
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 28,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
            }}
          >
            สถานะตามโพสต์: CXM ปฏิเสธจ่าย!
          </span>
        </div>
      </div>

      {/* Colossal Hero Number Banner (y: 855..1390, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 858,
          left: 48,
          width: 884,
          transform: `scale(${interpolate(pop, [0, 1], [0.86, 1])})`,
          transformOrigin: '0% 50%',
        }}
      >
        <div
          style={{
            background:
              'linear-gradient(135deg, rgba(16, 12, 6, 0.96) 0%, rgba(8, 8, 12, 0.96) 100%)',
            border: '3.5px solid #FFB800',
            borderRadius: 24,
            padding: '22px 30px',
            boxShadow:
              '0 28px 70px rgba(0, 0, 0, 0.95), 0 0 45px rgba(255, 184, 0, 0.3)',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 34,
              color: '#F8FAFC',
              whiteSpace: 'nowrap',
            }}
          >
            CXM ปฏิเสธจ่ายกำไรบัญชี Cent (ตามโพสต์)
          </div>

          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 98,
              color: '#FFB800',
              whiteSpace: 'nowrap',
              lineHeight: 1.04,
              marginTop: 6,
              textShadow: '0 8px 30px rgba(255, 184, 0, 0.5)',
            }}
          >
            “เกือบ 6 ล้านบาท!”
          </div>

          <div
            style={{
              marginTop: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 14,
            }}
          >
            <div
              style={{
                backgroundColor: '#FF1E27',
                borderRadius: 8,
                padding: '4px 14px',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 24,
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                }}
              >
                ALMOST 6,000,000 THB
              </span>
            </div>
            <span
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 28,
                color: '#E2E8F0',
                whiteSpace: 'nowrap',
              }}
            >
              เงินทุนตัวเอง · กำไรก้อนใหญ่ที่เธออ้างว่าไม่ได้รับ
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 6 (6.4s - 7.8s | Frames 192 - 234):
 * Voice: "ซีเอ็กซ์เอ็มแจ้งในอีเมลว่า..."
 */
export const Shot6EmailNotice: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slideUp = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 210, mass: 0.65 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      <BrollBackground
        file="broll/typewriter-red-neon-ticker-tape.mp4"
        durationInFrames={42}
        playbackRate={1.35}
        zoomFrom={1.04}
        zoomTo={1.16}
        tint="crimson"
      />

      {/* Top Split Presenter Synced to Frame 192..234 (6.4s - 7.8s) */}
      <SyncedPresenter
        startFrame={192}
        durationInFrames={42}
        mode="split-top"
        label="LIVE REPORT · ตามที่เจ้าของโพสต์เล่า"
      />

      {/* Incoming Email Dossier Modal (y: 785..1390, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 786,
          left: 48,
          width: 884,
          transform: `translateY(${interpolate(slideUp, [0, 1], [48, 0])}px)`,
          borderRadius: 22,
          overflow: 'hidden',
          border: '3px solid #FF1E27',
          backgroundColor: 'rgba(8, 8, 13, 0.95)',
          boxShadow: '0 28px 65px rgba(0, 0, 0, 0.92), 0 0 40px rgba(255, 30, 39, 0.3)',
        }}
      >
        {/* Email Window Top Bar */}
        <div
          style={{
            backgroundColor: '#16070A',
            borderBottom: '2px solid #FF1E27',
            padding: '14px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                backgroundColor: '#FF1E27',
              }}
            />
            <span
              style={{
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 22,
                color: '#FFB800',
                letterSpacing: 1.2,
                whiteSpace: 'nowrap',
              }}
            >
              INCOMING EMAIL // BROKER NOTICE
            </span>
          </div>
          <span
            style={{
              fontFamily: FONT_KANIT_600,
              fontSize: 20,
              color: '#F8FAFC',
              whiteSpace: 'nowrap',
            }}
          >
            ข้อมูลตามโพสต์
          </span>
        </div>

        {/* Email Body & Spoken Thai Line */}
        <div style={{ padding: '24px 28px' }}>
          <div
            style={{
              fontFamily: FONT_ARCHIVO_800,
              fontSize: 22,
              color: '#94A3B8',
              whiteSpace: 'nowrap',
            }}
          >
            FROM: CXM BROKER &nbsp;|&nbsp; STATUS: PROFIT WITHHELD
          </div>

          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 76,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              lineHeight: 1.08,
              marginTop: 12,
            }}
          >
            <span style={{ color: '#FF1E27' }}>CXM</span> แจ้งในอีเมลว่า...
          </div>

          <div
            style={{
              marginTop: 14,
              backgroundColor: 'rgba(255, 30, 39, 0.16)',
              borderLeft: '8px solid #FF1E27',
              borderRadius: 10,
              padding: '12px 20px',
            }}
          >
            <span
              style={{
                fontFamily: FONT_KANIT_600,
                fontSize: 34,
                color: '#FFB800',
                whiteSpace: 'nowrap',
              }}
            >
              อ้างว่าตรวจพบรูปแบบการเทรดที่เข้าข่าย...
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 7 (7.8s - 9.3s | Frames 234 - 279):
 * Voice: "...เป็นท็อกซิกเทรดดิ้ง"
 */
export const Shot7ToxicTrading: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const toxicSlam = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 250, mass: 0.55 },
  });

  // Deterministic RGB glitch offset on the impact frames
  const glitchOffset =
    frame < 14 || (frame > 22 && frame < 29)
      ? Math.sin(frame * 3.1) * 7
      : 2;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      {/* Rapid B-roll whip cut */}
      <Sequence from={0} durationInFrames={24}>
        <BrollBackground
          file="broll/red-forbidden-icon-glow.mp4"
          durationInFrames={24}
          playbackRate={1.5}
          zoomFrom={1.06}
          zoomTo={1.22}
          tint="crimson"
        />
      </Sequence>
      <Sequence from={24} durationInFrames={21}>
        <BrollBackground
          file="broll/contract-signature-wax-seal.mp4"
          durationInFrames={21}
          playbackRate={1.45}
          zoomFrom={1.04}
          zoomTo={1.16}
          tint="crimson"
        />
      </Sequence>

      {/* Main TOXIC TRADING Slam Block (y: 165..760, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 168,
          left: 48,
          width: 884,
          transform: `scale(${interpolate(toxicSlam, [0, 1], [0.8, 1])})`,
          transformOrigin: '50% 30%',
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(8, 8, 12, 0.94)',
            border: '3.5px solid #FF1E27',
            borderRadius: 24,
            padding: '26px 28px',
            boxShadow:
              '0 30px 70px rgba(0, 0, 0, 0.95), 0 0 50px rgba(255, 30, 39, 0.45)',
          }}
        >
          <div
            style={{
              display: 'inline-block',
              backgroundColor: '#FFB800',
              borderRadius: 8,
              padding: '4px 16px',
              marginBottom: 14,
            }}
          >
            <span
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 26,
                color: '#050507',
                whiteSpace: 'nowrap',
              }}
            >
              ข้อกล่าวหาในอีเมล CXM · ตามที่เจ้าของโพสต์เล่า
            </span>
          </div>

          {/* Chromatic RGB Glitch "TOXIC TRADING" */}
          <div style={{ position: 'relative', height: 112 }}>
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: -glitchOffset,
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 94,
                color: '#00F0FF',
                opacity: 0.7,
                whiteSpace: 'nowrap',
                lineHeight: 1,
              }}
            >
              “TOXIC TRADING”
            </div>
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: glitchOffset,
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 94,
                color: '#FF1E27',
                opacity: 0.85,
                whiteSpace: 'nowrap',
                lineHeight: 1,
              }}
            >
              “TOXIC TRADING”
            </div>
            <div
              style={{
                position: 'relative',
                fontFamily: FONT_ARCHIVO_800,
                fontSize: 94,
                color: '#FFFFFF',
                whiteSpace: 'nowrap',
                lineHeight: 1,
              }}
            >
              “TOXIC TRADING”
            </div>
          </div>

          {/* Thai Spoken Line */}
          <div
            style={{
              marginTop: 8,
              backgroundColor: '#FF1E27',
              borderRadius: 16,
              padding: '14px 24px',
              textAlign: 'center',
            }}
          >
            <span
              style={{
                fontFamily: FONT_KANIT_800,
                fontSize: 74,
                color: '#FFFFFF',
                whiteSpace: 'nowrap',
                lineHeight: 1.05,
              }}
            >
              “เป็นท็อกซิกเทรดดิ้ง!”
            </span>
          </div>
        </div>
      </div>

      {/* 3-Fact Summary Stack (y: 780..1385, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 785,
          left: 48,
          width: 884,
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        {[
          {
            num: '01',
            label: 'เวลาถือออเดอร์ (ตามโพสต์):',
            val: 'ถือออเดอร์นานถึง 2 ชั่วโมง',
            accent: '#FFB800',
          },
          {
            num: '02',
            label: 'ยอดกำไรบัญชี Cent:',
            val: 'เกือบ 6 ล้านบาท (CXM ปฏิเสธจ่าย)',
            accent: '#FF1E27',
          },
          {
            num: '03',
            label: 'เหตุผลที่แจ้งในอีเมล:',
            val: 'หาว่าเทรดเร็วเกินไป / "Toxic Trading"',
            accent: '#FFB800',
          },
        ].map((item, idx) => {
          const rowSpring = spring({
            frame: Math.max(0, frame - idx * 4),
            fps,
            config: { damping: 14, stiffness: 220, mass: 0.6 },
          });
          return (
            <div
              key={item.num}
              style={{
                backgroundColor: 'rgba(9, 9, 14, 0.92)',
                border: `2px solid ${item.accent}`,
                borderLeft: `10px solid ${item.accent}`,
                borderRadius: 16,
                padding: '16px 22px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transform: `translateX(${interpolate(rowSpring, [0, 1], [-50, 0])}px)`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <span
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 30,
                    color: item.accent,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {item.num}
                </span>
                <span
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 28,
                    color: '#CBD5E1',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {item.label}
                </span>
              </div>
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 32,
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                }}
              >
                {item.val}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/**
 * SHOT 8 (9.3s - 10.0s | Frames 279 - 300):
 * Silent Final Verdict & Cliffhanger (0.7s).
 * Presenter locked to timeline 9.3s - 10.0s + key numbers + attribution.
 */
export const Shot8VerdictEndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pop = spring({
    frame,
    fps,
    config: { damping: 13, stiffness: 240, mass: 0.55 },
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#050507' }}>
      {/* Presenter full-frame synced to Frame 279..300 (9.3s - 10.0s) */}
      <SyncedPresenter
        startFrame={279}
        durationInFrames={21}
        mode="full-frame"
        zoomFrom={1.08}
        zoomTo={1.13}
      />

      {/* Evidence Still Card in Mid-Frame so Presenter is clear at top */}
      <PostEvidenceCard
        variant="claim"
        top={536}
        left={48}
        width={884}
        rotateDeg={-0.8}
        highlightTop={18}
        highlightHeight={96}
        highlightDelay={0}
        badgeText="สรุปดราม่า EP.62 · ตามที่เจ้าของโพสต์เล่า"
      />

      {/* Final Verdict Card (y: 940..1395, x: 48..932) */}
      <div
        style={{
          position: 'absolute',
          top: 940,
          left: 48,
          width: 884,
          transform: `scale(${interpolate(pop, [0, 1], [0.92, 1])})`,
          transformOrigin: '0% 50%',
        }}
      >
        {/* 3 Key Numbers Row */}
        <div style={{ display: 'flex', gap: 14, marginBottom: 14 }}>
          {[
            { text: '2 ชั่วโมง', bg: '#FFB800', fg: '#050507' },
            { text: 'เกือบ 6 ล้านบาท', bg: '#FF1E27', fg: '#FFFFFF' },
            { text: '“TOXIC TRADING”', bg: '#0F172A', fg: '#FFB800' },
          ].map((pill) => (
            <div
              key={pill.text}
              style={{
                flex: 1,
                backgroundColor: pill.bg,
                border: '2px solid #FFB800',
                borderRadius: 14,
                padding: '10px 10px',
                textAlign: 'center',
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 30,
                  color: pill.fg,
                  whiteSpace: 'nowrap',
                }}
              >
                {pill.text}
              </span>
            </div>
          ))}
        </div>

        {/* Main Cliffhanger Question Box */}
        <div
          style={{
            backgroundColor: 'rgba(7, 7, 12, 0.95)',
            border: '3px solid #FF1E27',
            borderRadius: 24,
            padding: '22px 28px',
            boxShadow: '0 28px 65px rgba(0, 0, 0, 0.95)',
          }}
        >
          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 58,
              color: '#FFFFFF',
              whiteSpace: 'nowrap',
              lineHeight: 1.1,
            }}
          >
            ถือ 2 ชม. แต่ <span style={{ color: '#FF1E27' }}>CXM</span> หาว่าเทรดเร็ว?
          </div>

          <div
            style={{
              fontFamily: FONT_KANIT_800,
              fontSize: 68,
              color: '#FFB800',
              whiteSpace: 'nowrap',
              lineHeight: 1.08,
              marginTop: 8,
            }}
          >
            คุณคิดเห็นยังไงกับเรื่องนี้?!
          </div>

          <div
            style={{
              marginTop: 12,
              paddingTop: 12,
              borderTop: '1px solid rgba(255, 255, 255, 0.18)',
              fontFamily: FONT_KANIT_600,
              fontSize: 27,
              color: '#CBD5E1',
              whiteSpace: 'nowrap',
            }}
          >
            * เรื่องราวทั้งหมดเป็นข้อมูลตามที่เจ้าของโพสต์เล่า
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
