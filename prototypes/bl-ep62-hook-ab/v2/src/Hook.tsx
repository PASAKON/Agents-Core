import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {
  BrandBug,
  CaptionPill,
  Headline,
  HighlightBox,
  LegalLabel,
} from './components/Overlays';
import { ARCHIVO_FONT, fitFontSize, KANIT_FONT, useLoadFonts } from './fonts';

/**
 * Beat 1: OPEN (0.00s - 1.00s, frames 0..29, duration 30)
 * cxm-post-claim.png full-bleed, darkened to ~55% brightness, slow push-in (scale 1.00 -> 1.06).
 */
const OpenBeat: React.FC = () => {
  const localFrame = useCurrentFrame();
  const scale = interpolate(localFrame, [0, 30], [1.0, 1.06], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <Img
        src={staticFile('cxm-post-claim.png')}
        style={{
          width: 1080,
          height: 1920,
          objectFit: 'cover',
          filter: 'brightness(0.55)',
          transformOrigin: '540px 880px',
          transform: `scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * Beat 2: HOOK-1 (1.00s - 3.57s, frames 30..106, duration 77)
 * broll-12.mp4 full-bleed, darkened ~50%.
 * Centre (y ~850..1050): big clock counting up 0:00 -> 2:00 with unit ชม. (Archivo/Kanit 800, ~150px),
 * finishing by 2.6s (localFrame 48) and holding.
 * Caption below (y ~1150): ถือ 2 ชม. → โดนข้อหา "เร็วเกิน" + credit ตามที่เจ้าของโพสต์เล่า.
 */
const Hook1Beat: React.FC = () => {
  const localFrame = useCurrentFrame();

  // 1.00s to 2.60s = 1.60s = 48 frames
  const totalMinutes = Math.round(
    interpolate(localFrame, [0, 48], [0, 120], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.quad),
    })
  );
  const hours = Math.floor(totalMinutes / 60);
  const minutes = String(totalMinutes % 60).padStart(2, '0');
  const clockDigits = `${hours}:${minutes}`;

  const clockPop = interpolate(localFrame, [0, 6, 46, 50, 56], [0.92, 1.0, 1.0, 1.05, 1.0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const captionFullText = 'ถือ 2 ชม. → โดนข้อหา "เร็วเกิน"';
  const captionSize = fitFontSize({
    text: captionFullText,
    targetSize: 58,
    maxWidth: 668,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <OffthreadVideo
        src={staticFile('broll-12.mp4')}
        muted
        style={{
          width: 1080,
          height: 1920,
          objectFit: 'cover',
          filter: 'brightness(0.5)',
        }}
      />

      {/* Big Centre Clock at y ~850..1050 inside safe area x 120..840 */}
      <div
        style={{
          position: 'absolute',
          left: 120,
          top: 850,
          width: 720,
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 25,
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.54)',
            borderRadius: 28,
            padding: '10px 36px',
            border: '2px solid rgba(255, 255, 255, 0.16)',
            boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'center',
            gap: 16,
            maxWidth: 720,
            boxSizing: 'border-box',
            transform: `scale(${clockPop})`,
            whiteSpace: 'nowrap',
          }}
        >
          <span
            style={{
              fontFamily: ARCHIVO_FONT,
              fontWeight: 800,
              fontSize: 146,
              lineHeight: 1,
              color: '#FFFFFF',
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-2px',
              textShadow: '0 6px 24px rgba(0, 0, 0, 0.9)',
            }}
          >
            {clockDigits}
          </span>
          <span
            style={{
              fontFamily: KANIT_FONT,
              fontWeight: 800,
              fontSize: 92,
              lineHeight: 1,
              color: '#FFFFFF',
              textShadow: '0 6px 24px rgba(0, 0, 0, 0.9)',
            }}
          >
            ชม.
          </span>
        </div>
      </div>

      {/* Caption at y ~1150 */}
      <CaptionPill top={1120} credit="ตามที่เจ้าของโพสต์เล่า">
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 800,
            fontSize: captionSize,
            lineHeight: 1.15,
            whiteSpace: 'nowrap',
          }}
        >
          <span style={{ color: '#FFFFFF' }}>ถือ 2 ชม. → โดนข้อหา </span>
          <span style={{ color: '#FFD60A' }}>&ldquo;เร็วเกิน&rdquo;</span>
        </div>
      </CaptionPill>
    </AbsoluteFill>
  );
};

/**
 * Beat 3: HOOK-2 (3.57s - 6.43s, frames 107..192, duration 86)
 * cxm-post-claim.png full-bleed (~80% brightness), slow zoom toward claim line (centre ~x 480, y 880).
 * Yellow highlight box draws around x 120, y 850, w 720, h 60 (still coords, moves with zoom) between 3.8 and 4.3s.
 * Caption (y ~1150): เธอเล่าว่า CXM ไม่จ่ายกำไร + count up 0 -> 6 ล้านบาท prefixed by เกือบ (~96px yellow) by 5.2s.
 */
const Hook2Beat: React.FC = () => {
  const localFrame = useCurrentFrame();

  const zoomScale = interpolate(localFrame, [0, 86], [1.0, 1.06], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // 3.8s = frame 114 -> localFrame 7; 4.3s = frame 129 -> localFrame 22
  // 5.2s = frame 156 -> localFrame 49
  const countVal = Math.round(
    interpolate(localFrame, [3, 49], [0, 6], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.quad),
    })
  );

  const line1Text = 'เธอเล่าว่า CXM ไม่จ่ายกำไร';
  const line2Text = `เกือบ ${countVal} ล้านบาท`;

  const line1Size = fitFontSize({
    text: line1Text,
    targetSize: 48,
    maxWidth: 668,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });
  const line2Size = fitFontSize({
    text: line2Text,
    targetSize: 96,
    maxWidth: 668,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1080,
          height: 1920,
          transformOrigin: '480px 880px',
          transform: `scale(${zoomScale})`,
        }}
      >
        <Img
          src={staticFile('cxm-post-claim.png')}
          style={{
            width: 1080,
            height: 1920,
            objectFit: 'cover',
            filter: 'brightness(0.8)',
          }}
        />
        <HighlightBox
          x={120}
          y={850}
          w={720}
          h={60}
          startFrame={7}
          endFrame={22}
        />
      </div>

      {/* Caption at y ~1150 */}
      <CaptionPill top={1110}>
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 800,
            fontSize: line1Size,
            lineHeight: 1.15,
            color: '#FFFFFF',
            whiteSpace: 'nowrap',
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
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {line2Text}
        </div>
      </CaptionPill>
    </AbsoluteFill>
  );
};

/**
 * Beat 4: HOOK-3 (6.43s - 9.27s, frames 193..277, duration 85)
 * cxm-post-account.png full-bleed (~80%), slight zoom toward CXM Direct line;
 * yellow highlight box draws around x 120, y 818, w 720, h 55 (still coords) by 6.9s.
 * Red stamp TOXIC TRADING? slams in at 7.0s (scale 1.4 -> 1.0, rotation -4 deg, #E5202E, Archivo 800 ~64px) at y ~1100.
 * Under it (Kanit 600, ~36px): ตามที่เธอเล่า: CXM แจ้งในอีเมล
 */
const Hook3Beat: React.FC = () => {
  const localFrame = useCurrentFrame();

  const zoomScale = interpolate(localFrame, [0, 85], [1.0, 1.06], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // 7.0s = frame 210 -> localFrame = 210 - 193 = 17
  const stampOpacity = interpolate(localFrame, [16, 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const stampScale = interpolate(localFrame, [17, 23], [1.4, 1.0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const stampText = 'TOXIC TRADING?';
  const stampSize = fitFontSize({
    text: stampText,
    targetSize: 64,
    maxWidth: 640,
    fontFamily: 'Archivo',
    fontWeight: 800,
  });

  const subText = 'ตามที่เธอเล่า: CXM แจ้งในอีเมล';
  const subSize = fitFontSize({
    text: subText,
    targetSize: 36,
    maxWidth: 668,
    fontFamily: 'Kanit',
    fontWeight: 600,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1080,
          height: 1920,
          transformOrigin: '480px 845px',
          transform: `scale(${zoomScale})`,
        }}
      >
        <Img
          src={staticFile('cxm-post-account.png')}
          style={{
            width: 1080,
            height: 1920,
            objectFit: 'cover',
            filter: 'brightness(0.8)',
          }}
        />
        {/* 6.9s = frame 207 -> localFrame 14 */}
        <HighlightBox
          x={120}
          y={818}
          w={720}
          h={55}
          startFrame={2}
          endFrame={14}
        />
      </div>

      {/* Red stamp-style label centred at y ~1100 inside safe area x 120..840 */}
      <div
        style={{
          position: 'absolute',
          left: 120,
          top: 1045,
          width: 720,
          height: 110,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 32,
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            opacity: stampOpacity,
            transform: `rotate(-4deg) scale(${stampScale})`,
            backgroundColor: 'rgba(18, 2, 4, 0.88)',
            border: '6px solid #E5202E',
            outline: '2px solid rgba(229, 32, 46, 0.55)',
            borderRadius: 12,
            padding: '10px 28px',
            boxShadow: '0 14px 36px rgba(0, 0, 0, 0.7)',
            maxWidth: 690,
            boxSizing: 'border-box',
          }}
        >
          <span
            style={{
              fontFamily: ARCHIVO_FONT,
              fontWeight: 800,
              fontSize: stampSize,
              lineHeight: 1.05,
              color: '#E5202E',
              letterSpacing: '2px',
              whiteSpace: 'nowrap',
              display: 'block',
            }}
          >
            {stampText}
          </span>
        </div>
      </div>

      {/* Caption under the stamp */}
      <CaptionPill top={1188}>
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 600,
            fontSize: subSize,
            lineHeight: 1.2,
            color: '#FFFFFF',
            whiteSpace: 'nowrap',
          }}
        >
          {subText}
        </div>
      </CaptionPill>
    </AbsoluteFill>
  );
};

/**
 * Beat 5: HOOK-4 (9.27s - 11.67s, frames 278..349, duration 72)
 * avatar30.mp4 (640x1024 lipsync, media time = timeline time -> trimBefore = 9.27s in frames = 278)
 * scaled to COVER full 1080x1920 frame, centred. No headline.
 * Caption low (y ~1250..1400): เธอเลยถาม + big yellow 3 that pops (scale 0 -> 1.15 -> 1.0) + ข้อที่ยังไร้คำตอบ.
 */
const Hook4Beat: React.FC = () => {
  const localFrame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const threePopScale = interpolate(
    localFrame,
    [1, 9, 15],
    [0, 1.15, 1.0],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }
  );

  const fullCaptionSample = 'เธอเลยถาม 3 ข้อที่ยังไร้คำตอบ';
  const textSize = fitFontSize({
    text: fullCaptionSample,
    targetSize: 54,
    maxWidth: 640,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <OffthreadVideo
        src={staticFile('avatar30.mp4')}
        trimBefore={Math.round(9.27 * fps)}
        muted
        style={{
          width: 1080,
          height: 1920,
          objectFit: 'cover',
          objectPosition: 'center center',
        }}
      />

      {/* Caption low at y ~1250..1400 */}
      <CaptionPill top={1268}>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'center',
            gap: 14,
            whiteSpace: 'nowrap',
          }}
        >
          <span
            style={{
              fontFamily: KANIT_FONT,
              fontWeight: 800,
              fontSize: textSize,
              lineHeight: 1.1,
              color: '#FFFFFF',
            }}
          >
            เธอเลยถาม
          </span>
          <span
            style={{
              display: 'inline-block',
              fontFamily: ARCHIVO_FONT,
              fontWeight: 800,
              fontSize: Math.round(textSize * 1.85),
              lineHeight: 0.95,
              color: '#FFD60A',
              transform: `scale(${threePopScale})`,
              transformOrigin: 'center bottom',
              textShadow: '0 4px 18px rgba(0, 0, 0, 0.85)',
            }}
          >
            3
          </span>
          <span
            style={{
              fontFamily: KANIT_FONT,
              fontWeight: 800,
              fontSize: textSize,
              lineHeight: 1.1,
              color: '#FFFFFF',
            }}
          >
            ข้อที่ยังไร้คำตอบ
          </span>
        </div>
      </CaptionPill>
    </AbsoluteFill>
  );
};

/**
 * Beat 6: PATTERN-1 (11.67s - 13.97s, frames 350..418, duration 69)
 * broll-29.mp4 full-bleed, brightness ~60%.
 * On top: cxm-post-account.png cropped to post band (y 763..1156) in an 860x313 card at x 110, y 600,
 * rounded corners 24px, 2px white/20% border, soft shadow, enters by sliding up 80px + fade in 0.35s (~11 frames).
 * Caption (y ~1330): เธอเล่าว่า เปิดบัญชีเซนต์ กับ CXM.
 */
const Pattern1Beat: React.FC = () => {
  const localFrame = useCurrentFrame();

  // 0.35s * 30fps = 10.5 frames
  const cardTranslateY = interpolate(localFrame, [0, 11], [80, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const cardOpacity = interpolate(localFrame, [0, 11], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Card box: left 110 px, top 600 px, width 860 px, height 313 px
  const cardLeft = 110;
  const cardTop = 600;
  const cardWidth = 860;
  const cardHeight = 313;
  // Scaled by 860 / 1080 = 0.7963, shifted up by 763 * (860 / 1080) = 607.6 px
  const scaledImgHeight = Math.round(1920 * (860 / 1080));

  const captionText = 'เธอเล่าว่า เปิดบัญชีเซนต์ กับ CXM';
  const captionSize = fitFontSize({
    text: captionText,
    targetSize: 54,
    maxWidth: 668,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <OffthreadVideo
        src={staticFile('broll-29.mp4')}
        muted
        style={{
          width: 1080,
          height: 1920,
          objectFit: 'cover',
          filter: 'brightness(0.6)',
        }}
      />

      {/* Card centred at x 110, y 600 */}
      <div
        style={{
          position: 'absolute',
          left: cardLeft,
          top: cardTop,
          width: cardWidth,
          height: cardHeight,
          borderRadius: 24,
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.75)',
          border: '2px solid rgba(255, 255, 255, 0.2)',
          backgroundColor: '#111111',
          opacity: cardOpacity,
          transform: `translateY(${cardTranslateY}px)`,
          zIndex: 25,
        }}
      >
        <Img
          src={staticFile('cxm-post-account.png')}
          style={{
            position: 'absolute',
            left: 0,
            top: -607.6,
            width: cardWidth,
            height: scaledImgHeight,
          }}
        />
      </div>

      {/* Caption at y ~1330 */}
      <CaptionPill top={1295}>
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 800,
            fontSize: captionSize,
            lineHeight: 1.15,
            whiteSpace: 'nowrap',
          }}
        >
          <span style={{ color: '#FFFFFF' }}>เธอเล่าว่า </span>
          <span style={{ color: '#FFD60A' }}>เปิดบัญชีเซนต์</span>
          <span style={{ color: '#FFFFFF' }}> กับ CXM</span>
        </div>
      </CaptionPill>
    </AbsoluteFill>
  );
};

/**
 * Beat 7: PATTERN-2 (13.97s - 15.00s, frames 419..449, duration 31)
 * cxm-post-full.png full-bleed (~80%), slow zoom toward x 540, y 1100.
 * Caption (y ~1300): 22 กันยายน · เธอว่า "ไม่ใช้บอทเลย" + credit ตามที่เจ้าของโพสต์เล่า.
 */
const Pattern2Beat: React.FC = () => {
  const localFrame = useCurrentFrame();

  const zoomScale = interpolate(localFrame, [0, 31], [1.04, 1.11], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const captionText = '22 กันยายน · เธอว่า "ไม่ใช้บอทเลย"';
  const captionSize = fitFontSize({
    text: captionText,
    targetSize: 54,
    maxWidth: 668,
    fontFamily: 'Kanit',
    fontWeight: 800,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      <Img
        src={staticFile('cxm-post-full.png')}
        style={{
          width: 1080,
          height: 1920,
          objectFit: 'cover',
          filter: 'brightness(0.8)',
          transformOrigin: '540px 1100px',
          transform: `scale(${zoomScale})`,
        }}
      />

      {/* Caption at y ~1300 */}
      <CaptionPill top={1265} credit="ตามที่เจ้าของโพสต์เล่า">
        <div
          style={{
            fontFamily: KANIT_FONT,
            fontWeight: 800,
            fontSize: captionSize,
            lineHeight: 1.15,
            whiteSpace: 'nowrap',
          }}
        >
          <span style={{ color: '#FFFFFF' }}>22 กันยายน · เธอว่า </span>
          <span style={{ color: '#FFD60A' }}>&ldquo;ไม่ใช้บอทเลย&rdquo;</span>
        </div>
      </CaptionPill>
    </AbsoluteFill>
  );
};

export const Hook: React.FC = () => {
  useLoadFonts();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', overflow: 'hidden' }}>
      {/* Narration audio starting at frame 0, never re-timed */}
      <Audio src={staticFile('audio-0-15.wav')} />

      {/* OPEN: 0.00s .. 1.00s (frames 0..29) */}
      <Sequence from={0} durationInFrames={30} premountFor={fps} name="OPEN">
        <OpenBeat />
      </Sequence>

      {/* HOOK-1: 1.00s .. 3.57s (frames 30..106) */}
      <Sequence from={30} durationInFrames={77} premountFor={fps} name="HOOK-1">
        <Hook1Beat />
      </Sequence>

      {/* HOOK-2: 3.57s .. 6.43s (frames 107..192) */}
      <Sequence from={107} durationInFrames={86} premountFor={fps} name="HOOK-2">
        <Hook2Beat />
      </Sequence>

      {/* HOOK-3: 6.43s .. 9.27s (frames 193..277) */}
      <Sequence from={193} durationInFrames={85} premountFor={fps} name="HOOK-3">
        <Hook3Beat />
      </Sequence>

      {/* HOOK-4: 9.27s .. 11.67s (frames 278..349) */}
      <Sequence from={278} durationInFrames={72} premountFor={fps} name="HOOK-4">
        <Hook4Beat />
      </Sequence>

      {/* PATTERN-1: 11.67s .. 13.97s (frames 350..418) */}
      <Sequence
        from={350}
        durationInFrames={69}
        premountFor={fps}
        name="PATTERN-1"
      >
        <Pattern1Beat />
      </Sequence>

      {/* PATTERN-2: 13.97s .. 15.00s (frames 419..449) */}
      <Sequence
        from={419}
        durationInFrames={31}
        premountFor={fps}
        name="PATTERN-2"
      >
        <Pattern2Beat />
      </Sequence>

      {/* Top viral headline (0..9.27s full, hidden 9.27..11.67s, 11.67..15.00s compact) */}
      <Headline />

      {/* Always-on persistent overlays on every frame */}
      <BrandBug />
      <LegalLabel />
    </AbsoluteFill>
  );
};
