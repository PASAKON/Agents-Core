import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile } from 'remotion';
import { HudChrome } from './components/HudChrome';
import {
  Shot1Hook,
  Shot2HoldTwoHours,
  Shot3TooFastAccusation,
  Shot4CxmRefused,
  Shot5SixMillionBaht,
  Shot6EmailNotice,
  Shot7ToxicTrading,
  Shot8VerdictEndCard,
} from './components/Scenes';
import { FONT_FACE_CSS, useLoadLocalFonts } from './fonts';

export const Clip: React.FC = () => {
  useLoadLocalFonts();

  return (
    <AbsoluteFill
      style={{
        width: 1080,
        height: 1920,
        backgroundColor: '#050507',
        overflow: 'hidden',
      }}
    >
      <style>{FONT_FACE_CSS}</style>

      {/* Main 10.0s Thai Voiceover (starts at 0, untouched timing) */}
      <Audio src={staticFile('voice-10s.wav')} />

      {/* 0.0s - 1.0s (Frames 0 - 30): Scroll-Stopper Hook */}
      <Sequence from={0} durationInFrames={30}>
        <Shot1Hook />
      </Sequence>

      {/* 1.0s - 2.2s (Frames 30 - 66): "ถือออเดอร์สองชั่วโมง..." */}
      <Sequence from={30} durationInFrames={36}>
        <Shot2HoldTwoHours />
      </Sequence>

      {/* 2.2s - 3.6s (Frames 66 - 108): "...แต่โดนข้อหาเทรดเร็วเกินไป?" */}
      <Sequence from={66} durationInFrames={42}>
        <Shot3TooFastAccusation />
      </Sequence>

      {/* 3.6s - 5.0s (Frames 108 - 150): "เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไร..." */}
      <Sequence from={108} durationInFrames={42}>
        <Shot4CxmRefused />
      </Sequence>

      {/* 5.0s - 6.4s (Frames 150 - 192): "...เกือบหกล้านบาท" */}
      <Sequence from={150} durationInFrames={42}>
        <Shot5SixMillionBaht />
      </Sequence>

      {/* 6.4s - 7.8s (Frames 192 - 234): "ซีเอ็กซ์เอ็มแจ้งในอีเมลว่า..." */}
      <Sequence from={192} durationInFrames={42}>
        <Shot6EmailNotice />
      </Sequence>

      {/* 7.8s - 9.3s (Frames 234 - 279): "...เป็นท็อกซิกเทรดดิ้ง" */}
      <Sequence from={234} durationInFrames={45}>
        <Shot7ToxicTrading />
      </Sequence>

      {/* 9.3s - 10.0s (Frames 279 - 300): Silent Verdict & Cliffhanger */}
      <Sequence from={279} durationInFrames={21}>
        <Shot8VerdictEndCard />
      </Sequence>

      {/* Persistent 10.0s Broadcast Chrome & Legal Disclaimer */}
      <HudChrome />
    </AbsoluteFill>
  );
};
