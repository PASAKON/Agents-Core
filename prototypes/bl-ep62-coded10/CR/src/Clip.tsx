import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
   staticFile,
  useCurrentFrame,
} from "remotion";
import { FONT_FACE_CSS, FONTS, useLoadFonts } from "./fonts";

const COLORS = {
  bg: "#0C1016",
  cardBg: "#161B22",
  cardBorder: "#2A313C",
  cardTopBar: "#1C222B",
  white: "#F2F4F7",
  grey: "#8B949E",
  yellow: "#FED100",
  red: "#F0444B",
  green: "#3FB950",
} as const;

const clamp01 = (v: number): number => Math.min(1, Math.max(0, v));

const easeOutCubic = (t: number): number => {
  const c = clamp01(t);
  return 1 - Math.pow(1 - c, 3);
};

const easeProgress = (frame: number, startFrame: number, durationFrames: number): number => {
  if (durationFrames <= 0) return frame >= startFrame ? 1 : 0;
  return easeOutCubic((frame - startFrame) / durationFrames);
};

const parseHex = (hex: string): [number, number, number] => {
  const clean = hex.replace("#", "");
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ];
};

const lerpColor = (hexA: string, hexB: string, t: number): string => {
  const c = clamp01(t);
  const [r1, g1, b1] = parseHex(hexA);
  const [r2, g2, b2] = parseHex(hexB);
  const r = Math.round(r1 + (r2 - r1) * c);
  const g = Math.round(g1 + (g2 - g1) * c);
  const b = Math.round(b1 + (b2 - b1) * c);
  return `rgb(${r}, ${g}, ${b})`;
};

const formatDurationHMS = (totalSeconds: number): string => {
  const sec = Math.max(0, Math.min(7200, Math.round(totalSeconds)));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

interface CaptionSegment {
  startFrame: number;
  endFrame: number;
  isIntroGrey?: boolean;
  parts: { text: string; yellow?: boolean }[];
}

const CAPTION_SEGMENTS: CaptionSegment[] = [
  // 0.00 - 1.00: ตามที่เจ้าของโพสต์เล่า (grey, Kanit 600 44 px)
  {
    startFrame: 0,
    endFrame: 30,
    isIntroGrey: true,
    parts: [{ text: "ตามที่เจ้าของโพสต์เล่า" }],
  },
  // 1.00 - 1.80: ถือออเดอร์
  {
    startFrame: 30,
    endFrame: 54,
    parts: [{ text: "ถือออเดอร์" }],
  },
  // 1.80 - 2.50: *สองชั่วโมง*
  {
    startFrame: 54,
    endFrame: 75,
    parts: [{ text: "สองชั่วโมง", yellow: true }],
  },
  // 2.50 - 3.05: แต่โดนข้อหา
  {
    startFrame: 75,
    endFrame: 91,
    parts: [{ text: "แต่โดนข้อหา" }],
  },
  // 3.05 - 3.60: เทรด*เร็วเกินไป?*
  {
    startFrame: 91,
    endFrame: 108,
    parts: [
      { text: "เทรด" },
      { text: "เร็วเกินไป?", yellow: true },
    ],
  },
  // 3.60 - 4.30: เธอเล่าว่า
  {
    startFrame: 108,
    endFrame: 129,
    parts: [{ text: "เธอเล่าว่า" }],
  },
  // 4.30 - 5.20: CXM *ไม่จ่ายกำไร*
  {
    startFrame: 129,
    endFrame: 156,
    parts: [
      { text: "CXM " },
      { text: "ไม่จ่ายกำไร", yellow: true },
    ],
  },
  // 5.20 - 6.40: *เกือบ 6 ล้านบาท*
  {
    startFrame: 156,
    endFrame: 192,
    parts: [{ text: "เกือบ 6 ล้านบาท", yellow: true }],
  },
  // 6.40 - 7.30: CXM แจ้งใน*อีเมล*
  {
    startFrame: 192,
    endFrame: 219,
    parts: [
      { text: "CXM แจ้งใน" },
      { text: "อีเมล", yellow: true },
    ],
  },
  // 7.30 - 8.10: ว่าเป็น
  {
    startFrame: 219,
    endFrame: 243,
    parts: [{ text: "ว่าเป็น" }],
  },
  // 8.10 - 9.30: *ท็อกซิกเทรดดิ้ง*
  {
    startFrame: 243,
    endFrame: 279,
    parts: [{ text: "ท็อกซิกเทรดดิ้ง", yellow: true }],
  },
  // 9.30 - 10.00: *3 คำถาม*ที่ยังไร้คำตอบ
  {
    startFrame: 279,
    endFrame: 300,
    parts: [
      { text: "3 คำถาม", yellow: true },
      { text: "ที่ยังไร้คำตอบ" },
    ],
  },
];

const Headline: React.FC<{
  line1: string;
  line2: string;
  enterProgress: number;
}> = ({ line1, line2, enterProgress }) => {
  const translateY = (1 - enterProgress) * 24;
  const scale = 0.96 + 0.04 * enterProgress;

  return (
    <div
      style={{
        position: "absolute",
        left: 120,
        top: 300,
        width: 840,
        height: 220,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        transform: `translateY(${translateY.toFixed(2)}px) scale(${scale.toFixed(4)})`,
      }}
    >
      <div
        style={{
          fontFamily: FONTS.kanit800,
          fontSize: 76,
          lineHeight: 1.15,
          color: COLORS.white,
          whiteSpace: "nowrap",
          textAlign: "center",
        }}
      >
        {line1}
      </div>
      <div
        style={{
          fontFamily: FONTS.kanit800,
          fontSize: 76,
          lineHeight: 1.15,
          color: COLORS.yellow,
          whiteSpace: "nowrap",
          textAlign: "center",
          marginTop: 6,
        }}
      >
        {line2}
      </div>
    </div>
  );
};

const WindowDots: React.FC = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
    <div
      style={{
        width: 12,
        height: 12,
        borderRadius: "50%",
        backgroundColor: COLORS.grey,
        opacity: 0.65,
      }}
    />
    <div
      style={{
        width: 12,
        height: 12,
        borderRadius: "50%",
        backgroundColor: COLORS.grey,
        opacity: 0.65,
      }}
    />
    <div
      style={{
        width: 12,
        height: 12,
        borderRadius: "50%",
        backgroundColor: COLORS.grey,
        opacity: 0.65,
      }}
    />
  </div>
);

const SceneA: React.FC<{ frame: number }> = ({ frame }) => {
  // Frame 0 already shows the headline and the card (no empty first frame).
  // Timer counts 0:00:00 -> 2:00:00 from 1.00 (frame 30) to 2.40 s (frame 72)
  const timerProgress =
    frame <= 30 ? 0 : frame >= 72 ? 1 : easeOutCubic((frame - 30) / (72 - 30));
  const currentSeconds = Math.round(timerProgress * 7200);
  const timerText = formatDurationHMS(currentSeconds);

  // Green status appears at 2.40 s (frame 72)
  const greenEnter = frame < 72 ? 0 : easeProgress(frame, 72, 8);

  // At 3.05 s (frame 91): Card A border turns red (6 frames), red pill appears at top-right
  const redTransition = frame < 91 ? 0 : easeProgress(frame, 91, 6);
  const borderColor = lerpColor(COLORS.cardBorder, COLORS.red, redTransition);
  const pillScale = 0.96 + 0.04 * redTransition;

  return (
    <>
      <Headline
        line1="ถือออเดอร์ 2 ชั่วโมง"
        line2="แต่โดนหาว่าเร็วเกิน?"
        enterProgress={1}
      />

      {/* Card A: 760 x 300 in IDEA band */}
      <div
        style={{
          position: "absolute",
          left: (1080 - 760) / 2,
          top: 660,
          width: 760,
          height: 300,
          backgroundColor: COLORS.cardBg,
          border: `2px solid ${borderColor}`,
          borderRadius: 18,
          boxSizing: "border-box",
          padding: "24px 36px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        {/* Top row: mono label + red pill at 3.05s */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            height: 40,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 24,
              color: COLORS.grey,
              whiteSpace: "nowrap",
            }}
          >
            ระยะเวลาที่ถือออเดอร์
          </div>

          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 26,
              color: COLORS.red,
              border: `2px solid ${COLORS.red}`,
              backgroundColor: "transparent",
              borderRadius: 999,
              padding: "3px 16px",
              lineHeight: 1.15,
              whiteSpace: "nowrap",
              opacity: redTransition,
              transform: `scale(${pillScale.toFixed(4)})`,
            }}
          >
            &quot;เร็วเกินไป?&quot;
          </div>
        </div>

        {/* Big timer: Archivo 800, 150 px, white */}
        <div
          style={{
            fontFamily: FONTS.archivo800,
            fontSize: 150,
            lineHeight: 0.92,
            color: COLORS.white,
            letterSpacing: "-0.02em",
            fontVariantNumeric: "tabular-nums",
            whiteSpace: "nowrap",
            textAlign: "center",
          }}
        >
          {timerText}
        </div>

        {/* Bottom group: 8px progress bar + green mono line */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div
            style={{
              width: "100%",
              height: 8,
              backgroundColor: COLORS.cardBorder,
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(timerProgress * 100).toFixed(2)}%`,
                height: "100%",
                backgroundColor: COLORS.yellow,
                borderRadius: 4,
              }}
            />
          </div>

          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 24,
              lineHeight: 1.1,
              color: COLORS.green,
              whiteSpace: "nowrap",
              opacity: greenEnter,
              transform: `translateY(${((1 - greenEnter) * 10).toFixed(2)}px)`,
            }}
          >
            ● ถือไว้ 2 ชม.
          </div>
        </div>
      </div>
    </>
  );
};

const SceneB: React.FC<{ frame: number }> = ({ frame }) => {
  // Scene B starts at 3.60 s (frame 108)
  const sceneEnter = easeProgress(frame, 108, 8);
  const cardBScale = 0.96 + 0.04 * sceneEnter;
  const cardBTranslateY = (1 - sceneEnter) * 24;

  // 3.80 - 4.30 s (frames 114..129): yellow highlighter sweeps left-to-right
  // Still coordinates: x 120, y 850, w 720, h 60; crop band is y 760..1160, full width 1080 -> scaled to card inner width (836)
  const innerWidth = 836;
  const scaleFactor = innerWidth / 1080;
  const croppedHeight = 400 * scaleFactor;
  const hlSweep =
    frame <= 114 ? 0 : frame >= 129 ? 1 : easeOutCubic((frame - 114) / (129 - 114));
  const hlLeft = 120 * scaleFactor;
  const hlTop = (850 - 760) * scaleFactor;
  const hlWidth = 720 * scaleFactor * hlSweep;
  const hlHeight = 60 * scaleFactor;

  // 5.20 s (frame 156): Card B blurs (8 px) and dims to 35%; Card C enters on top
  const cardCTransition = frame < 156 ? 0 : easeProgress(frame, 156, 8);
  const cardBBlur = cardCTransition * 8;
  const cardBOpacity = 1 - cardCTransition * (1 - 0.35);

  // Card C number counts ฿0 -> ฿6,000,000 from 5.20 (frame 156) to 5.90 s (frame 177)
  const countProgress =
    frame <= 156 ? 0 : frame >= 177 ? 1 : easeOutCubic((frame - 156) / (177 - 156));
  const currentBaht = Math.round(countProgress * 6000000);
  const formattedBaht = `฿${currentBaht.toLocaleString("en-US")}`;

  const cardCScale = 0.96 + 0.04 * cardCTransition;
  const cardCTranslateY = (1 - cardCTransition) * 24;

  return (
    <>
      <Headline
        line1="เธอเล่าว่า CXM"
        line2="ไม่จ่ายกำไร"
        enterProgress={sceneEnter}
      />

      {/* Card B: 840 wide post card */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 632,
          width: 840,
          backgroundColor: COLORS.cardBg,
          border: `2px solid ${COLORS.cardBorder}`,
          borderRadius: 18,
          overflow: "hidden",
          boxSizing: "border-box",
          opacity: cardBOpacity,
          filter: cardBBlur > 0.01 ? `blur(${cardBBlur.toFixed(2)}px)` : "none",
          transform: `translateY(${cardBTranslateY.toFixed(2)}px) scale(${cardBScale.toFixed(4)})`,
        }}
      >
        {/* Top bar: 56 px (#1C222B) with three grey dots and mono grey label */}
        <div
          style={{
            height: 56,
            backgroundColor: COLORS.cardTopBar,
            borderBottom: `1px solid ${COLORS.cardBorder}`,
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            gap: 16,
            boxSizing: "border-box",
          }}
        >
          <WindowDots />
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 24,
              color: COLORS.grey,
              whiteSpace: "nowrap",
            }}
          >
            โพสต์ของเธอ · ชื่อเบลอแล้ว
          </div>
        </div>

        {/* Cropped still: y 760..1160 of 1080x1920 image, scaled to card width */}
        <div
          style={{
            position: "relative",
            width: innerWidth,
            height: croppedHeight,
            overflow: "hidden",
            backgroundColor: "#FFFFFF",
          }}
        >
          <Img
            src={staticFile("stills/cxm-post-claim.png")}
            style={{
              position: "absolute",
              left: 0,
              top: -760 * scaleFactor,
              width: innerWidth,
              height: 1920 * scaleFactor,
              display: "block",
            }}
          />

          {/* Yellow highlighter (35%, multiply-like look, radius 6) */}
          {hlSweep > 0 && (
            <div
              style={{
                position: "absolute",
                left: hlLeft,
                top: hlTop,
                width: hlWidth,
                height: hlHeight,
                backgroundColor: "rgba(254, 209, 0, 0.35)",
                mixBlendMode: "multiply",
                borderRadius: 6,
              }}
            />
          )}
        </div>
      </div>

      {/* Card C: 640 x 260, border yellow 2 px, centred on top at 5.20 s */}
      {frame >= 156 && (
        <div
          style={{
            position: "absolute",
            left: (1080 - 640) / 2,
            top: 686,
            width: 640,
            height: 260,
            backgroundColor: COLORS.cardBg,
            border: `2px solid ${COLORS.yellow}`,
            borderRadius: 18,
            boxSizing: "border-box",
            padding: "22px 24px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "space-between",
            opacity: cardCTransition,
            transform: `translateY(${cardCTranslateY.toFixed(2)}px) scale(${cardCScale.toFixed(4)})`,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 24,
              color: COLORS.grey,
              whiteSpace: "nowrap",
            }}
          >
            กำไรที่เธอบอกว่าไม่ได้รับ
          </div>

          <div
            style={{
              fontFamily: FONTS.archivo800,
              fontSize: 120,
              lineHeight: 0.95,
              color: COLORS.yellow,
              letterSpacing: "-0.04em",
              fontVariantNumeric: "tabular-nums",
              whiteSpace: "nowrap",
              transform: "scale(0.92)",
              transformOrigin: "center center",
            }}
          >
            {formattedBaht}
          </div>

          <div
            style={{
              fontFamily: FONTS.kanit600,
              fontSize: 34,
              lineHeight: 1.1,
              color: COLORS.white,
              whiteSpace: "nowrap",
            }}
          >
            เกือบ 6 ล้านบาท (ตามที่เธอเล่า)
          </div>
        </div>
      )}
    </>
  );
};

const SceneC: React.FC<{ frame: number }> = ({ frame }) => {
  // Scene C starts at 6.40 s (frame 192)
  const sceneEnter = easeProgress(frame, 192, 8);
  const cardDScale = 0.96 + 0.04 * sceneEnter;
  const cardDTranslateY = (1 - sceneEnter) * 24;

  // Typing "Toxic Trading" (13 chars) at 1 char per 2 frames starting at 7.30 s (frame 219)
  // Finishes at frame 219 + 12 * 2 = 243 (8.10 s)
  const targetText = "Toxic Trading";
  const charsTyped =
    frame < 219
      ? 0
      : Math.min(targetText.length, Math.floor((frame - 219) / 2) + 1);
  const typedSlice = targetText.slice(0, charsTyped);
  const typingEnded = frame >= 243;

  // When typing ends (frame 243), Card D's border turns red over 6 frames
  const redBorderProgress = typingEnded ? easeProgress(frame, 243, 6) : 0;
  const borderColor = lerpColor(COLORS.cardBorder, COLORS.red, redBorderProgress);

  // 8.10 s (frame 243): under Card D, red mono line 26 px fades in
  const jokeEnter = frame < 243 ? 0 : easeProgress(frame, 243, 8);

  return (
    <>
      <Headline
        line1="CXM แจ้งในอีเมลว่า"
        line2='"Toxic Trading"'
        enterProgress={sceneEnter}
      />

      {/* Card D: 840 x 420 email mock */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 600,
          width: 840,
          height: 420,
          backgroundColor: COLORS.cardBg,
          border: `2px solid ${borderColor}`,
          borderRadius: 18,
          overflow: "hidden",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          transform: `translateY(${cardDTranslateY.toFixed(2)}px) scale(${cardDScale.toFixed(4)})`,
        }}
      >
        {/* Top bar like Card B with mono label อีเมล · ตามที่เธอเล่า */}
        <div
          style={{
            height: 56,
            backgroundColor: COLORS.cardTopBar,
            borderBottom: `1px solid ${COLORS.cardBorder}`,
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            gap: 16,
            boxSizing: "border-box",
            flexShrink: 0,
          }}
        >
          <WindowDots />
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 24,
              color: COLORS.grey,
              whiteSpace: "nowrap",
            }}
          >
            อีเมล · ตามที่เธอเล่า
          </div>
        </div>

        {/* Email rows in mono 30 px */}
        <div
          style={{
            flex: 1,
            padding: "36px 40px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            boxSizing: "border-box",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
            {/* Row 1: From: CXM */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                fontFamily: FONTS.mono,
                fontSize: 30,
                paddingBottom: 24,
                borderBottom: `1px solid ${COLORS.cardBorder}`,
                whiteSpace: "nowrap",
              }}
            >
              <span style={{ color: COLORS.grey, width: 170, flexShrink: 0 }}>
                From:
              </span>
              <span style={{ color: COLORS.white }}>CXM</span>
            </div>

            {/* Row 2: เหตุผล: Toxic Trading (types on from 7.30s in red with block cursor) */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                fontFamily: FONTS.mono,
                fontSize: 30,
                paddingBottom: 24,
                borderBottom: `1px solid ${COLORS.cardBorder}`,
                whiteSpace: "nowrap",
              }}
            >
              <span style={{ color: COLORS.grey, width: 170, flexShrink: 0 }}>
                เหตุผล:
              </span>
              <span
                style={{
                  color: COLORS.red,
                  fontFamily: FONTS.monoBold,
                  display: "inline-flex",
                  alignItems: "center",
                }}
              >
                <span>{typedSlice}</span>
                {frame >= 219 && (
                  <span
                    style={{
                      display: "inline-block",
                      width: 16,
                      height: 32,
                      backgroundColor: COLORS.red,
                      marginLeft: 6,
                    }}
                  />
                )}
              </span>
            </div>
          </div>

          {/* Visible note keeping ตามที่เธอเล่า clear */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontFamily: FONTS.mono,
              fontSize: 22,
              color: COLORS.grey,
              whiteSpace: "nowrap",
            }}
          >
            <span>ตามที่เธอเล่า</span>
            <span>REF: ACCOUNT CLAIM</span>
          </div>
        </div>
      </div>

      {/* 8.10 s: under Card D, red mono line 26 px fades in */}
      {frame >= 243 && (
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 1036,
            width: 840,
            textAlign: "center",
            fontFamily: FONTS.mono,
            fontSize: 26,
            color: COLORS.red,
            whiteSpace: "nowrap",
            opacity: jokeEnter,
            transform: `translateY(${((1 - jokeEnter) * 12).toFixed(2)}px)`,
          }}
        >
          TypeError: กำไร is undefined
        </div>
      )}
    </>
  );
};

const SceneD: React.FC<{ frame: number }> = ({ frame }) => {
  // Scene D: 9.30 - 10.00 s (frames 279..299)
  // No headline. Three square chips (120 x 120, card style) in a row, centred at y ~820,
  // with Archivo 800 digits 1 2 3; pop in at 9.30 (279), 9.40 (282), 9.50 (285) (scale 0.9 -> 1, 6 frames).
  // Chip 3 gets a yellow border and yellow digit at 9.70 (frame 291).
  // Above them three short grey bars (like a progress step indicator).
  const popFrames = [279, 282, 285];
  const yellowProgress = frame < 291 ? 0 : easeProgress(frame, 291, 4);

  return (
    <div
      style={{
        position: "absolute",
        left: 120,
        top: 720,
        width: 840,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 28,
      }}
    >
      {/* Three short grey bars above the chips */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 36,
        }}
      >
        {[0, 1, 2].map((idx) => (
          <div
            key={idx}
            style={{
              width: 120,
              display: "flex",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: 76,
                height: 8,
                borderRadius: 4,
                backgroundColor: COLORS.grey,
                opacity: 0.65,
              }}
            />
          </div>
        ))}
      </div>

      {/* Three square chips (120 x 120, centred at y ~820: top 720 + 8 + 28 = 756, center = 756 + 60 = 816) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 36,
        }}
      >
        {[1, 2, 3].map((num, idx) => {
          const startF = popFrames[idx];
          const isStarted = frame >= startF;
          const p = isStarted ? easeProgress(frame, startF, 6) : 0;
          const scale = 0.9 + 0.1 * p;
          // Chip 1 is already visible at the cut frame 279; chips 2 & 3 pop in at 282, 285
          const opacity = idx === 0 ? 1 : isStarted ? p : 0;

          const isChip3 = num === 3;
          const borderColor = isChip3
            ? lerpColor(COLORS.cardBorder, COLORS.yellow, yellowProgress)
            : COLORS.cardBorder;
          const digitColor = isChip3
            ? lerpColor(COLORS.white, COLORS.yellow, yellowProgress)
            : COLORS.white;

          return (
            <div
              key={num}
              style={{
                width: 120,
                height: 120,
                backgroundColor: COLORS.cardBg,
                border: `2px solid ${borderColor}`,
                borderRadius: 18,
                boxSizing: "border-box",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity,
                transform: `scale(${scale.toFixed(4)})`,
              }}
            >
              <span
                style={{
                  fontFamily: FONTS.archivo800,
                  fontSize: 68,
                  lineHeight: 1,
                  color: digitColor,
                  whiteSpace: "nowrap",
                }}
              >
                {num}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const CaptionBand: React.FC<{ frame: number }> = ({ frame }) => {
  const activeSeg =
    CAPTION_SEGMENTS.find(
      (seg) => frame >= seg.startFrame && frame < seg.endFrame
    ) ?? CAPTION_SEGMENTS[CAPTION_SEGMENTS.length - 1];

  // 3-frame 12 px rise allowed on caption chunk swap (keep frame 0 settled)
  const riseProgress =
    activeSeg.startFrame === 0
      ? 1
      : easeProgress(frame, activeSeg.startFrame, 3);
  const translateY = (1 - riseProgress) * 12;

  const subLabel =
    frame < 108
      ? "ORDER DURATION · 02:00:00"
      : frame < 192
      ? "CLAIM · UNPAID PROFIT"
      : frame < 279
      ? "BROKER EMAIL · TOXIC TRADING"
      : "EP62 · 3 UNANSWERED QUESTIONS";

  return (
    <>
      {/* CAPTION band y ~1180 (centred) */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 1150,
          width: 840,
          height: 80,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `translateY(${translateY.toFixed(2)}px)`,
        }}
      >
        <div
          style={{
            fontFamily: activeSeg.isIntroGrey ? FONTS.kanit600 : FONTS.kanit800,
            fontSize: activeSeg.isIntroGrey ? 44 : 64,
            lineHeight: 1.15,
            color: activeSeg.isIntroGrey ? COLORS.grey : COLORS.white,
            whiteSpace: "nowrap",
            textAlign: "center",
          }}
        >
          {activeSeg.parts.map((part, idx) => (
            <span
              key={idx}
              style={{
                color: part.yellow
                  ? COLORS.yellow
                  : activeSeg.isIntroGrey
                  ? COLORS.grey
                  : COLORS.white,
              }}
            >
              {part.text}
            </span>
          ))}
        </div>
      </div>

      {/* Optional small mono grey sub-label 26 px at y ~1250 */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 1250,
          width: 840,
          textAlign: "center",
          fontFamily: FONTS.mono,
          fontSize: 26,
          color: COLORS.grey,
          whiteSpace: "nowrap",
        }}
      >
        {subLabel}
      </div>
    </>
  );
};

export const Clip: React.FC = () => {
  useLoadFonts();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bg,
        width: 1080,
        height: 1920,
        overflow: "hidden",
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: FONT_FACE_CSS }} />
      <Audio src={staticFile("voice-10s.wav")} />

      {/* Always on: Top-left small brand: bl-logo.png at 64 px high, x 120, y 150 + mono grey label */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 150,
          height: 64,
          display: "flex",
          alignItems: "center",
          gap: 18,
        }}
      >
        <Img
          src={staticFile("bl-logo.png")}
          style={{
            height: 64,
            width: "auto",
            display: "block",
          }}
        />
        <span
          style={{
            fontFamily: FONTS.mono,
            fontSize: 24,
            color: COLORS.grey,
            whiteSpace: "nowrap",
            letterSpacing: "0.02em",
          }}
        >
          BLACK LIQUIDITY · EP62
        </span>
      </div>

      {/* Scenes (hard cuts at 3.60s = 108, 6.40s = 192, 9.30s = 279) */}
      {frame < 108 && <SceneA frame={frame} />}
      {frame >= 108 && frame < 192 && <SceneB frame={frame} />}
      {frame >= 192 && frame < 279 && <SceneC frame={frame} />}
      {frame >= 279 && <SceneD frame={frame} />}

      {/* Synced karaoke-style Thai caption */}
      <CaptionBand frame={frame} />

      {/* Always on: Legal line, mono grey #8B949E, 22 px, centred, y ~1440 */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 1440,
          width: 840,
          textAlign: "center",
          fontFamily: FONTS.kanit600,
          fontSize: 22,
          color: COLORS.grey,
          whiteSpace: "nowrap",
        }}
      >
        เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง
      </div>
    </AbsoluteFill>
  );
};
