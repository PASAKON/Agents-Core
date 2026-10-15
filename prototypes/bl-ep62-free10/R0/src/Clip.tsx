import React, { useEffect } from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {
  AmbientParticles,
  BroadcastHUD,
  EvidenceStillBand,
  SyncedAvatar,
} from './components/Overlays';
import {
  FONT_ARCHIVO_800,
  FONT_FACE_CSS,
  FONT_KANIT_600,
  FONT_KANIT_800,
  ensureFontsLoaded,
} from './fonts';
import {
  COLORS,
  SAFE_LEFT,
  SAFE_WIDTH,
  fadeIn,
  formatNumber,
  getImpactShake,
  popScale,
  slamScale,
  slideOffset,
} from './helpers';

export const Clip: React.FC = () => {
  const frame = useCurrentFrame();

  useEffect(() => {
    ensureFontsLoaded();
  }, []);

  // Impact camera shakes on major beat hits
  const shake0 = getImpactShake(frame, 0, 10, 6);
  const shake30 = getImpactShake(frame, 30, 16, 8);
  const shake74 = getImpactShake(frame, 74, 22, 10);
  const shake108 = getImpactShake(frame, 108, 16, 8);
  const shake147 = getImpactShake(frame, 147, 22, 10);
  const shake192 = getImpactShake(frame, 192, 16, 8);
  const shake234 = getImpactShake(frame, 234, 26, 12);
  const shake279 = getImpactShake(frame, 279, 14, 7);

  const totalShakeX =
    shake0.x +
    shake30.x +
    shake74.x +
    shake108.x +
    shake147.x +
    shake192.x +
    shake234.x +
    shake279.x;
  const totalShakeY =
    shake0.y +
    shake30.y +
    shake74.y +
    shake108.y +
    shake147.y +
    shake192.y +
    shake234.y +
    shake279.y;
  const totalShakeRot =
    shake0.rotate +
    shake30.rotate +
    shake74.rotate +
    shake108.rotate +
    shake147.rotate +
    shake192.rotate +
    shake234.rotate +
    shake279.rotate;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: COLORS.bgDark,
        overflow: 'hidden',
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: FONT_FACE_CSS }} />

      {/* Master Narration Track (0.0s - 10.0s, untouched timing) */}
      <Audio src={staticFile('voice-10s.wav')} />

      {/* Main animated stage with beat-reactive camera shake */}
      <AbsoluteFill
        style={{
          transform: `translate3d(${totalShakeX}px, ${totalShakeY}px, 0) rotate(${totalShakeRot}deg)`,
        }}
      >
        {/* =================================================================
            SHOT 1 (0.0s – 1.0s | Frames 0..29): SCROLL-STOPPER HOOK
            Lead-in: ฿6M profit refused by CXM? Held 2 hrs = fast trading?
           ================================================================= */}
        {frame >= 0 && frame < 30 && (
          <AbsoluteFill>
            <Sequence from={0} durationInFrames={30} layout="none">
              <OffthreadVideo
                src={staticFile('broll/red-forbidden-icon-glow.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(frame, [0, 29], [1.06, 1.18])})`,
                  filter: 'brightness(0.55) contrast(1.2)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.crimsonBright} />

            {/* Left: Lip-synced presenter starting at 0.0s */}
            <SyncedAvatar
              shotStartFrame={0}
              shotDuration={30}
              frame={frame}
              borderColor={COLORS.crimsonBright}
              label="LIVE · EP.62"
              style={{
                left: SAFE_LEFT,
                top: 144,
                width: 430,
                height: 548,
              }}
            />

            {/* Right: Instant Scroll-Stopper Hero Card */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT + 446,
                top: 144,
                width: SAFE_WIDTH - 446,
                height: 548,
                borderRadius: 20,
                background:
                  'linear-gradient(165deg, rgba(22, 10, 14, 0.95) 0%, rgba(10, 10, 16, 0.96) 100%)',
                border: `2.5px solid ${COLORS.gold}`,
                boxShadow: '0 18px 45px rgba(0,0,0,0.85)',
                padding: '22px 20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transform: `scale(${slamScale(frame, 0, 1.12)})`,
              }}
            >
              <div
                style={{
                  alignSelf: 'flex-start',
                  backgroundColor: COLORS.crimson,
                  padding: '6px 14px',
                  borderRadius: 8,
                  fontFamily: FONT_KANIT_800,
                  fontSize: 24,
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                }}
              >
                🚨 ดราม่าวงการเทรดทอง
              </div>

              <div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 28,
                    color: COLORS.silver,
                    whiteSpace: 'nowrap',
                  }}
                >
                  เทรดเดอร์สาวอ้างพอร์ตแตกหัก
                </div>
                <div
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 64,
                    color: COLORS.goldBright,
                    lineHeight: 1.05,
                    textShadow: '0 0 24px rgba(255, 209, 102, 0.55)',
                    whiteSpace: 'nowrap',
                    marginTop: 6,
                  }}
                >
                  ฿6,000,000
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 44,
                    color: '#FFFFFF',
                    lineHeight: 1.15,
                    whiteSpace: 'nowrap',
                  }}
                >
                  กำไรเกือบ 6 ล้าน!
                </div>
              </div>

              <div
                style={{
                  backgroundColor: COLORS.crimsonBright,
                  padding: '10px 16px',
                  borderRadius: 12,
                  textAlign: 'center',
                  boxShadow: '0 0 24px rgba(255, 36, 59, 0.6)',
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 38,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  โบรก CXM ไม่จ่าย?!
                </span>
              </div>

              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 21,
                  color: COLORS.gold,
                  textAlign: 'center',
                  whiteSpace: 'nowrap',
                }}
              >
                *เรื่องราวตามที่เจ้าของโพสต์เล่า
              </div>
            </div>

            {/* Evidence Post Strip (cxm-post-claim.png) */}
            <EvidenceStillBand
              stillFile="stills/cxm-post-claim.png"
              highlightProgress={interpolate(frame, [0, 18], [0.35, 1], {
                extrapolateRight: 'clamp',
              })}
              highlightTopPx={40}
              highlightHeightPx={88}
              style={{
                left: SAFE_LEFT + 10,
                top: 716,
                transform: `rotate(-1.2deg) scale(${interpolate(
                  frame,
                  [0, 29],
                  [0.98, 1.01]
                )})`,
              }}
            />

            {/* Bottom Hook Headline Bar */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 1118,
                width: SAFE_WIDTH,
                padding: '22px 28px',
                borderRadius: 18,
                background:
                  'linear-gradient(90deg, #E6192E 0%, #990817 100%)',
                border: '2.5px solid #FFE484',
                boxShadow: '0 16px 40px rgba(0,0,0,0.9)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 46,
                  color: '#FFFFFF',
                  textShadow: '0 4px 12px rgba(0,0,0,0.65)',
                  whiteSpace: 'nowrap',
                }}
              >
                ถือออเดอร์ 2 ชม. แต่ถูกหาว่าเทรดเร็ว?!
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 27,
                  color: COLORS.goldBright,
                  whiteSpace: 'nowrap',
                }}
              >
                สรุปดราม่า CXM ปฏิเสธจ่ายกำไร · ตามที่เจ้าของโพสต์เล่า
              </div>
            </div>
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 2 (1.0s – 2.2s | Frames 30..65): BEAT 1A
            Voice: "ถือออเดอร์สองชั่วโมง..."
           ================================================================= */}
        {frame >= 30 && frame < 66 && (
          <AbsoluteFill>
            <Sequence from={30} durationInFrames={36} layout="none">
              <OffthreadVideo
                src={staticFile('broll/hourglass-red-sand.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(frame, [30, 65], [1.08, 1.24])})`,
                  filter: 'brightness(0.58) contrast(1.18)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.gold} />

            {/* Left: Animated 2-Hour Hold Stopwatch Card */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 146,
                width: 440,
                height: 536,
                borderRadius: 20,
                backgroundColor: 'rgba(10, 11, 16, 0.92)',
                border: `2.5px solid ${COLORS.gold}`,
                boxShadow: '0 18px 45px rgba(0,0,0,0.85)',
                padding: '24px 22px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transform: `translateY(${slideOffset(frame, 30, 45, 7)}px)`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                }}
              >
                <div
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: '50%',
                    backgroundColor: COLORS.gold,
                    boxShadow: `0 0 12px ${COLORS.gold}`,
                  }}
                />
                <span
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 22,
                    color: COLORS.gold,
                    letterSpacing: 1,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ORDER HOLD DURATION
                </span>
              </div>

              {/* Digital Stopwatch Counter reaching 02:00:00 */}
              <div
                style={{
                  backgroundColor: '#050608',
                  border: '2px solid rgba(255, 209, 102, 0.4)',
                  borderRadius: 14,
                  padding: '18px 12px',
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 68,
                    color: COLORS.goldBright,
                    letterSpacing: 2,
                    textShadow: '0 0 22px rgba(255, 209, 102, 0.6)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {frame < 44
                    ? `01:${Math.floor(
                        interpolate(frame, [30, 44], [12, 59], {
                          extrapolateRight: 'clamp',
                        })
                      )
                        .toString()
                        .padStart(2, '0')}:${Math.floor(
                        interpolate(frame, [30, 44], [10, 59], {
                          extrapolateRight: 'clamp',
                        })
                      )
                        .toString()
                        .padStart(2, '0')}`
                    : '02:00:00'}
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 24,
                    color: COLORS.silver,
                    whiteSpace: 'nowrap',
                    marginTop: 4,
                  }}
                >
                  120 นาทีเต็ม · เทรดทองด้วยตัวเอง
                </div>
              </div>

              <div
                style={{
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 64,
                    color: '#FFFFFF',
                    lineHeight: 1.05,
                    whiteSpace: 'nowrap',
                  }}
                >
                  2 ชั่วโมง
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 25,
                    color: COLORS.gold,
                    whiteSpace: 'nowrap',
                    marginTop: 6,
                  }}
                >
                  ถือออเดอร์ผ่านมือถือ (ตามโพสต์)
                </div>
              </div>
            </div>

            {/* Right: Lip-synced Presenter at 1.0s – 2.2s */}
            <SyncedAvatar
              shotStartFrame={30}
              shotDuration={36}
              frame={frame}
              borderColor={COLORS.gold}
              label="HOLD · 2 HOURS"
              style={{
                left: SAFE_LEFT + 456,
                top: 146,
                width: SAFE_WIDTH - 456,
                height: 536,
              }}
            />

            {/* Main Spoken Beat Headline ("ถือออเดอร์สองชั่วโมง") */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 706,
                width: SAFE_WIDTH,
                padding: '18px 26px',
                borderRadius: 18,
                backgroundColor: 'rgba(12, 12, 18, 0.95)',
                border: `3px solid ${COLORS.goldBright}`,
                boxShadow: '0 16px 40px rgba(0,0,0,0.9)',
                textAlign: 'center',
                transform: `scale(${slamScale(frame, 30, 1.45)})`,
              }}
            >
              <span
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 64,
                  color: COLORS.goldBright,
                  textShadow: '0 4px 18px rgba(255, 209, 102, 0.45)',
                  whiteSpace: 'nowrap',
                }}
              >
                “ถือออเดอร์นาน 2 ชั่วโมง”
              </span>
            </div>

            {/* Evidence Still Highlighting "ถือออเดอร์นานถึง 2 ชั่วโมง" */}
            <EvidenceStillBand
              stillFile="stills/cxm-post-claim.png"
              highlightProgress={interpolate(frame, [33, 52], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              })}
              highlightTopPx={148}
              highlightHeightPx={50}
              highlightColor="rgba(255, 209, 102, 0.34)"
              tagText="หลักฐานคำบอกเล่า · ถือออเดอร์นานถึง 2 ชั่วโมง"
              style={{
                left: SAFE_LEFT + 10,
                top: 866,
              }}
            />
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 3 (2.2s – 3.6s | Frames 66..107): BEAT 1B
            Voice: "...แต่โดนข้อหาเทรดเร็วเกินไป?"
           ================================================================= */}
        {frame >= 66 && frame < 108 && (
          <AbsoluteFill>
            <Sequence from={66} durationInFrames={42} layout="none">
              <OffthreadVideo
                src={staticFile('broll/red-digital-countdown.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(frame, [66, 107], [1.22, 1.05])})`,
                  filter: 'brightness(0.55) contrast(1.25)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.crimsonBright} />

            {/* Left: Synced Presenter at 2.2s – 3.6s */}
            <SyncedAvatar
              shotStartFrame={66}
              shotDuration={42}
              frame={frame}
              borderColor={COLORS.crimsonBright}
              label="ACCUSED · TOO FAST?!"
              style={{
                left: SAFE_LEFT,
                top: 146,
                width: 416,
                height: 536,
              }}
            />

            {/* Right: Contradiction Comparison Card (2 Hours vs Too Fast) */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT + 434,
                top: 146,
                width: SAFE_WIDTH - 434,
                height: 536,
                borderRadius: 20,
                backgroundColor: 'rgba(10, 10, 16, 0.94)',
                border: `2.5px solid ${COLORS.crimsonBright}`,
                padding: '22px 20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transform: `translateX(${slideOffset(frame, 66, 60, 7)}px)`,
              }}
            >
              <div
                style={{
                  backgroundColor: 'rgba(255, 209, 102, 0.14)',
                  border: `2px solid ${COLORS.gold}`,
                  borderRadius: 14,
                  padding: '14px 16px',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 22,
                    color: COLORS.gold,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ⏱️ สิ่งที่เทรดเดอร์ระบุในโพสต์:
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 42,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                    marginTop: 4,
                  }}
                >
                  ถือออเดอร์ 2 ชั่วโมง
                </div>
              </div>

              <div
                style={{
                  textAlign: 'center',
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 34,
                  color: COLORS.warningYellow,
                  letterSpacing: 2,
                  whiteSpace: 'nowrap',
                }}
              >
                ⚡ VS ⚡
              </div>

              <div
                style={{
                  backgroundColor: 'rgba(230, 25, 46, 0.25)',
                  border: `2px solid ${COLORS.crimsonBright}`,
                  borderRadius: 14,
                  padding: '14px 16px',
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 22,
                    color: '#FF99A4',
                    whiteSpace: 'nowrap',
                  }}
                >
                  🚫 ข้อกล่าวหาที่เธอได้รับ:
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 42,
                    color: COLORS.warningYellow,
                    whiteSpace: 'nowrap',
                    marginTop: 4,
                  }}
                >
                  เทรดเร็วเกินไป?!
                </div>
              </div>
            </div>

            {/* Lower Kinetic Typography Stack */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 716,
                width: SAFE_WIDTH,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 18,
              }}
            >
              {/* Line 1: แต่โดนข้อหา */}
              <div
                style={{
                  backgroundColor: 'rgba(12, 13, 19, 0.94)',
                  border: '2px solid rgba(255,255,255,0.28)',
                  padding: '12px 36px',
                  borderRadius: 14,
                  transform: `scale(${slamScale(frame, 66, 1.35)})`,
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 54,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  แต่กลับโดนข้อหา...
                </span>
              </div>

              {/* Line 2: เทรดเร็วเกินไป?! (Slams at frame 73) */}
              {frame >= 72 && (
                <div
                  style={{
                    width: SAFE_WIDTH,
                    background:
                      'linear-gradient(95deg, #E6192E 0%, #B8091B 100%)',
                    border: `4px solid ${COLORS.warningYellow}`,
                    borderRadius: 22,
                    padding: '24px 20px',
                    textAlign: 'center',
                    boxShadow:
                      '0 22px 55px rgba(230, 25, 46, 0.65), 0 0 35px rgba(255, 230, 0, 0.45)',
                    transform: `rotate(-1.6deg) scale(${slamScale(
                      frame,
                      72,
                      1.75
                    )})`,
                  }}
                >
                  <span
                    style={{
                      fontFamily: FONT_KANIT_800,
                      fontSize: 88,
                      color: COLORS.warningYellow,
                      textShadow: '0 6px 18px rgba(0,0,0,0.8)',
                      lineHeight: 1.05,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    เทรดเร็วเกินไป?!
                  </span>
                </div>
              )}

              {/* Line 3: Question callout */}
              {frame >= 80 && (
                <div
                  style={{
                    backgroundColor: 'rgba(8, 8, 12, 0.92)',
                    border: `2px solid ${COLORS.gold}`,
                    borderRadius: 999,
                    padding: '12px 34px',
                    opacity: fadeIn(frame, 80, 5),
                    transform: `translateY(${slideOffset(frame, 80, 30, 6)}px)`,
                  }}
                >
                  <span
                    style={{
                      fontFamily: FONT_KANIT_600,
                      fontSize: 34,
                      color: COLORS.goldBright,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    ❓ ถือออเดอร์ตั้ง 2 ชั่วโมง เรียกว่าเทรดเร็วได้ยังไง?
                  </span>
                </div>
              )}
            </div>
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 4 (3.6s – 4.9s | Frames 108..146): BEAT 2A
            Voice: "เธอเล่าว่าซีเอ็กซ์เอ็มไม่จ่ายกำไร..."
           ================================================================= */}
        {frame >= 108 && frame < 147 && (
          <AbsoluteFill>
            <Sequence from={108} durationInFrames={39} layout="none">
              <OffthreadVideo
                src={staticFile('broll/contract-signature-wax-seal.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(
                    frame,
                    [108, 146],
                    [1.06, 1.18]
                  )})`,
                  filter: 'brightness(0.48) contrast(1.2)',
                }}
              />
            </Sequence>

            {/* Upper Widescreen Hero Presenter (3.6s – 4.9s) */}
            <SyncedAvatar
              shotStartFrame={108}
              shotDuration={39}
              frame={frame}
              videoScale={1.14}
              videoOffsetY={25}
              borderColor={COLORS.gold}
              label="ACCORDING TO HER POST · ตามที่เจ้าของโพสต์เล่า"
              style={{
                left: SAFE_LEFT,
                top: 144,
                width: SAFE_WIDTH,
                height: 520,
              }}
            />

            {/* Center Spoken Beat Card: เธอเล่าว่า CXM ไม่จ่ายกำไร */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 686,
                width: SAFE_WIDTH,
                borderRadius: 20,
                background:
                  'linear-gradient(180deg, rgba(16, 16, 24, 0.96) 0%, rgba(10, 10, 15, 0.98) 100%)',
                border: `3px solid ${COLORS.crimsonBright}`,
                boxShadow: '0 20px 50px rgba(0,0,0,0.9)',
                padding: '18px 26px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 6,
                transform: `scale(${slamScale(frame, 108, 1.38)})`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 34,
                    color: COLORS.goldBright,
                    whiteSpace: 'nowrap',
                  }}
                >
                  🗣️ เธอเล่าว่า โบรกเกอร์
                </span>
                <span
                  style={{
                    backgroundColor: COLORS.crimson,
                    padding: '2px 16px',
                    borderRadius: 8,
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 38,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  CXM
                </span>
              </div>

              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 74,
                  color: '#FFFFFF',
                  lineHeight: 1.08,
                  textShadow: '0 0 26px rgba(230, 25, 46, 0.7)',
                  whiteSpace: 'nowrap',
                }}
              >
                ปฏิเสธไม่จ่ายกำไร!
              </div>
            </div>

            {/* Lower Evidence Card: stills/cxm-post-account.png */}
            <EvidenceStillBand
              stillFile="stills/cxm-post-account.png"
              highlightProgress={interpolate(frame, [112, 134], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              })}
              highlightTopPx={42}
              highlightHeightPx={84}
              tagText="โพสต์ต้นทาง · เปิดบัญชี Cent กับโบรกเกอร์ CXM Direct"
              style={{
                left: SAFE_LEFT + 10,
                top: 940,
              }}
            />
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 5 (4.9s – 6.4s | Frames 147..191): BEAT 2B
            Voice: "...เกือบหกล้านบาท"
           ================================================================= */}
        {frame >= 147 && frame < 192 && (
          <AbsoluteFill>
            <Sequence from={147} durationInFrames={45} layout="none">
              <OffthreadVideo
                src={staticFile('broll/gold-bar-in-glass-cube.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(
                    frame,
                    [147, 191],
                    [1.06, 1.24]
                  )})`,
                  filter: 'brightness(0.62) contrast(1.22)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.goldBright} />

            {/* Top Left: Lip-synced Presenter at 4.9s – 6.4s */}
            <SyncedAvatar
              shotStartFrame={147}
              shotDuration={45}
              frame={frame}
              borderColor={COLORS.goldBright}
              label="PROFIT · ~6M THB"
              style={{
                left: SAFE_LEFT,
                top: 146,
                width: 432,
                height: 486,
              }}
            />

            {/* Top Right: Red Lock B-roll Inset */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT + 450,
                top: 146,
                width: SAFE_WIDTH - 450,
                height: 486,
                borderRadius: 20,
                overflow: 'hidden',
                border: `3px solid ${COLORS.crimsonBright}`,
                boxShadow: '0 18px 45px rgba(0,0,0,0.85)',
              }}
            >
              <Sequence from={147} durationInFrames={45} layout="none">
                <OffthreadVideo
                  src={staticFile('broll/finger-taps-red-lock.mp4')}
                  muted
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    transform: `scale(${interpolate(
                      frame,
                      [147, 191],
                      [1.05, 1.2]
                    )})`,
                  }}
                />
              </Sequence>
              <div
                style={{
                  position: 'absolute',
                  left: 16,
                  right: 16,
                  bottom: 16,
                  backgroundColor: 'rgba(230, 25, 46, 0.92)',
                  padding: '8px 14px',
                  borderRadius: 10,
                  textAlign: 'center',
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 26,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  🔒 ถูกปฏิเสธจ่ายกำไร
                </span>
              </div>
            </div>

            {/* Center/Lower: MASSIVE 6 MILLION BAHT NUMBER HIT */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 656,
                width: SAFE_WIDTH,
                borderRadius: 24,
                background:
                  'linear-gradient(165deg, rgba(20, 16, 8, 0.96) 0%, rgba(10, 10, 14, 0.98) 100%)',
                border: `3.5px solid ${COLORS.goldBright}`,
                boxShadow:
                  '0 24px 60px rgba(0,0,0,0.92), 0 0 40px rgba(255, 209, 102, 0.35)',
                padding: '28px 26px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 14,
                transform: `scale(${slamScale(frame, 147, 1.55)})`,
              }}
            >
              <div
                style={{
                  backgroundColor: 'rgba(255, 209, 102, 0.16)',
                  border: `1.5px solid ${COLORS.gold}`,
                  padding: '6px 22px',
                  borderRadius: 999,
                  fontFamily: FONT_KANIT_600,
                  fontSize: 26,
                  color: COLORS.goldBright,
                  whiteSpace: 'nowrap',
                }}
              >
                💰 ยอดกำไรที่เจ้าของโพสต์ระบุว่าไม่ได้รับจาก CXM
              </div>

              {/* Rolling Odometer Number up to ฿6,000,000 */}
              <div
                style={{
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 106,
                  color: COLORS.goldBright,
                  lineHeight: 1,
                  letterSpacing: 1,
                  textShadow:
                    '0 0 35px rgba(255, 209, 102, 0.7), 0 6px 16px rgba(0,0,0,0.9)',
                  whiteSpace: 'nowrap',
                }}
              >
                ~฿
                {formatNumber(
                  interpolate(frame, [147, 162], [1450000, 6000000], {
                    extrapolateLeft: 'clamp',
                    extrapolateRight: 'clamp',
                  })
                )}
              </div>

              {/* Spoken Thai Number Punch: เกือบ 6 ล้านบาท! */}
              <div
                style={{
                  width: '100%',
                  background:
                    'linear-gradient(90deg, #E6192E 0%, #B00B1C 100%)',
                  border: '3px solid #FFFFFF',
                  borderRadius: 18,
                  padding: '16px 20px',
                  textAlign: 'center',
                  boxShadow: '0 12px 32px rgba(230, 25, 46, 0.6)',
                }}
              >
                <span
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 82,
                    color: '#FFFFFF',
                    lineHeight: 1.05,
                    whiteSpace: 'nowrap',
                  }}
                >
                  เกือบ 6 ล้านบาท!
                </span>
              </div>

              {/* Supporting line from post */}
              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 29,
                  color: COLORS.silver,
                  whiteSpace: 'nowrap',
                  marginTop: 4,
                }}
              >
                เทรดขาดทุนรับผิดชอบเอง · แต่พอกำไรเกือบ 6 ล้านกลับถูกปฏิเสธ!
              </div>
            </div>
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 6 (6.4s – 7.8s | Frames 192..233): BEAT 3A
            Voice: "ซีเอ็กซ์เอ็มแจ้งในอีเมลว่า..."
           ================================================================= */}
        {frame >= 192 && frame < 234 && (
          <AbsoluteFill>
            <Sequence from={192} durationInFrames={42} layout="none">
              <OffthreadVideo
                src={staticFile('broll/typewriter-red-neon-ticker-tape.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(
                    frame,
                    [192, 233],
                    [1.08, 1.22]
                  )})`,
                  filter: 'brightness(0.56) contrast(1.22)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.crimsonBright} />

            {/* Top Left: Lip-synced Presenter at 6.4s – 7.8s */}
            <SyncedAvatar
              shotStartFrame={192}
              shotDuration={42}
              frame={frame}
              borderColor={COLORS.crimsonBright}
              label="BROKER EMAIL · CXM"
              style={{
                left: SAFE_LEFT,
                top: 146,
                width: 424,
                height: 500,
              }}
            />

            {/* Top Right: Incoming Email Alert Badge Card */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT + 442,
                top: 146,
                width: SAFE_WIDTH - 442,
                height: 500,
                borderRadius: 20,
                backgroundColor: 'rgba(11, 12, 18, 0.94)',
                border: `2.5px solid ${COLORS.crimsonBright}`,
                padding: '24px 20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transform: `translateX(${slideOffset(frame, 192, 55, 7)}px)`,
              }}
            >
              <div
                style={{
                  backgroundColor: 'rgba(230, 25, 46, 0.2)',
                  border: `1.5px solid ${COLORS.crimsonBright}`,
                  padding: '6px 14px',
                  borderRadius: 8,
                  alignSelf: 'flex-start',
                  fontFamily: FONT_ARCHIVO_800,
                  fontSize: 20,
                  color: COLORS.crimsonBright,
                  letterSpacing: 1,
                  whiteSpace: 'nowrap',
                }}
              >
                ✉️ INCOMING EMAIL
              </div>

              <div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 24,
                    color: COLORS.silver,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ผู้ส่ง (ตามคำบอกเล่า):
                </div>
                <div
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 58,
                    color: '#FFFFFF',
                    lineHeight: 1.05,
                    whiteSpace: 'nowrap',
                    marginTop: 4,
                  }}
                >
                  BROKER CXM
                </div>
              </div>

              <div
                style={{
                  backgroundColor: '#161822',
                  borderLeft: `5px solid ${COLORS.gold}`,
                  padding: '12px 14px',
                  borderRadius: 8,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 22,
                    color: COLORS.gold,
                    whiteSpace: 'nowrap',
                  }}
                >
                  สถานะคำสั่งถอนกำไร:
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 34,
                    color: COLORS.crimsonBright,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ❌ ปฏิเสธการจ่ายเงิน
                </div>
              </div>
            </div>

            {/* Lower Stylized Email Terminal Window */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 672,
                width: SAFE_WIDTH,
                borderRadius: 22,
                overflow: 'hidden',
                backgroundColor: 'rgba(10, 11, 17, 0.96)',
                border: '2.5px solid rgba(255, 255, 255, 0.25)',
                boxShadow: '0 24px 55px rgba(0,0,0,0.92)',
                transform: `translateY(${slideOffset(frame, 192, 48, 7)}px)`,
              }}
            >
              {/* Terminal Top Bar */}
              <div
                style={{
                  height: 48,
                  backgroundColor: '#181A24',
                  borderBottom: '2px solid #E6192E',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0 20px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      backgroundColor: '#FF5F56',
                    }}
                  />
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      backgroundColor: '#FFBD2E',
                    }}
                  />
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      backgroundColor: '#27C93F',
                    }}
                  />
                  <span
                    style={{
                      fontFamily: FONT_KANIT_600,
                      fontSize: 20,
                      color: COLORS.silver,
                      marginLeft: 10,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    คำชี้แจงทางอีเมลจาก CXM (ตามที่เจ้าของโพสต์เล่า)
                  </span>
                </div>
              </div>

              <div
                style={{
                  padding: '28px 30px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 18,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 68,
                    color: '#FFFFFF',
                    lineHeight: 1.1,
                    whiteSpace: 'nowrap',
                    transform: `scale(${slamScale(frame, 193, 1.4)})`,
                  }}
                >
                  “CXM แจ้งในอีเมลว่า...”
                </div>

                <div
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(230, 25, 46, 0.16)',
                    border: `2px dashed ${COLORS.crimsonBright}`,
                    borderRadius: 14,
                    padding: '18px 24px',
                    textAlign: 'center',
                  }}
                >
                  <div
                    style={{
                      fontFamily: FONT_KANIT_600,
                      fontSize: 34,
                      color: COLORS.goldBright,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    ⚠️ กล่าวหาว่าออเดอร์ที่ทำกำไรเกือบ 6 ล้านบาทนั้น...
                  </div>
                </div>
              </div>
            </div>
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 7 (7.8s – 9.3s | Frames 234..278): BEAT 3B CLIMAX
            Voice: "...เป็นท็อกซิกเทรดดิ้ง"
           ================================================================= */}
        {frame >= 234 && frame < 279 && (
          <AbsoluteFill>
            <Sequence from={234} durationInFrames={45} layout="none">
              <OffthreadVideo
                src={staticFile('broll/red-forbidden-icon-glow.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(
                    frame,
                    [234, 278],
                    [1.12, 1.28]
                  )})`,
                  filter: 'brightness(0.6) contrast(1.3)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.warningYellow} />

            {/* Upper Widescreen Synced Presenter (7.8s – 9.3s) */}
            <SyncedAvatar
              shotStartFrame={234}
              shotDuration={45}
              frame={frame}
              videoScale={1.15}
              videoOffsetY={20}
              borderColor={COLORS.warningYellow}
              label="VERDICT · TOXIC TRADING?!"
              style={{
                left: SAFE_LEFT,
                top: 146,
                width: SAFE_WIDTH,
                height: 490,
              }}
            />

            {/* CLIMAX "TOXIC TRADING" HAZARD CARD */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 660,
                width: SAFE_WIDTH,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 16,
              }}
            >
              {/* Hazard Caution Strip */}
              <div
                style={{
                  width: SAFE_WIDTH,
                  height: 46,
                  borderRadius: 10,
                  background:
                    'repeating-linear-gradient(-45deg, #FFE600 0px, #FFE600 24px, #111216 24px, #111216 48px)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 10px 25px rgba(0,0,0,0.8)',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#0A0B0E',
                    padding: '4px 24px',
                    borderRadius: 6,
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 22,
                    color: COLORS.warningYellow,
                    letterSpacing: 1.5,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ⚠️ BROKER ACCUSATION · ข้อกล่าวหาตามโพสต์ ⚠️
                </div>
              </div>

              {/* Giant English Stamp: TOXIC TRADING */}
              <div
                style={{
                  width: SAFE_WIDTH,
                  background:
                    'linear-gradient(135deg, #E6192E 0%, #7A0510 100%)',
                  border: `4px solid ${COLORS.warningYellow}`,
                  borderRadius: 24,
                  padding: '26px 20px',
                  textAlign: 'center',
                  boxShadow:
                    '0 24px 60px rgba(230, 25, 46, 0.75), 0 0 40px rgba(255, 230, 0, 0.45)',
                  transform: `scale(${slamScale(frame, 234, 1.8)}) rotate(-1.2deg)`,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 88,
                    color: COLORS.warningYellow,
                    letterSpacing: 2,
                    lineHeight: 1.02,
                    textShadow:
                      '5px 5px 0px #000000, 0 0 30px rgba(255, 230, 0, 0.6)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  “TOXIC TRADING”
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 68,
                    color: '#FFFFFF',
                    lineHeight: 1.1,
                    marginTop: 6,
                    textShadow: '0 4px 16px rgba(0,0,0,0.85)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  เป็น “ท็อกซิกเทรดดิ้ง”!
                </div>
              </div>

              {/* Bottom Paradox Summary Pill */}
              {frame >= 244 && (
                <div
                  style={{
                    width: SAFE_WIDTH,
                    backgroundColor: 'rgba(10, 11, 16, 0.95)',
                    border: `2.5px solid ${COLORS.gold}`,
                    borderRadius: 16,
                    padding: '16px 24px',
                    textAlign: 'center',
                    transform: `scale(${popScale(frame, 244)})`,
                  }}
                >
                  <span
                    style={{
                      fontFamily: FONT_KANIT_800,
                      fontSize: 40,
                      color: COLORS.goldBright,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    ถือออเดอร์ 2 ชั่วโมง = Toxic Trading?!
                  </span>
                </div>
              )}
            </div>
          </AbsoluteFill>
        )}

        {/* =================================================================
            SHOT 8 (9.3s – 10.0s | Frames 279..299): SILENCE / OUTRO VERDICT
            Case Dossier + BLACK LIQUIDITY EP.62 Cliffhanger
           ================================================================= */}
        {frame >= 279 && frame < 300 && (
          <AbsoluteFill>
            <Sequence from={279} durationInFrames={21} layout="none">
              <OffthreadVideo
                src={staticFile('broll/hourglass-red-sand.mp4')}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: `scale(${interpolate(
                    frame,
                    [279, 299],
                    [1.1, 1.18]
                  )})`,
                  filter: 'brightness(0.42) contrast(1.25)',
                }}
              />
            </Sequence>

            <AmbientParticles frame={frame} color={COLORS.gold} />

            {/* Top Left: Synced Presenter (9.3s – 10.0s) */}
            <SyncedAvatar
              shotStartFrame={279}
              shotDuration={21}
              frame={frame}
              borderColor={COLORS.gold}
              label="BLACK LIQUIDITY"
              style={{
                left: SAFE_LEFT,
                top: 146,
                width: 390,
                height: 468,
              }}
            />

            {/* Top Right: Channel Logo & Case Summary Dossier Card */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT + 408,
                top: 146,
                width: SAFE_WIDTH - 408,
                height: 468,
                borderRadius: 20,
                backgroundColor: 'rgba(10, 11, 16, 0.95)',
                border: `2.5px solid ${COLORS.gold}`,
                padding: '22px 20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transform: `scale(${slamScale(frame, 279, 1.2)})`,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <Img
                  src={staticFile('bl-logo.png')}
                  style={{
                    height: 48,
                    width: 'auto',
                    objectFit: 'contain',
                  }}
                />
                <span
                  style={{
                    backgroundColor: COLORS.crimson,
                    padding: '4px 12px',
                    borderRadius: 8,
                    fontFamily: FONT_ARCHIVO_800,
                    fontSize: 20,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  EP.62
                </span>
              </div>

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_KANIT_800,
                    fontSize: 28,
                    color: COLORS.goldBright,
                    whiteSpace: 'nowrap',
                  }}
                >
                  📋 สรุปข้อมูลตามที่เจ้าของโพสต์เล่า:
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 26,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  • เทรดทอง ถือออเดอร์นาน 2 ชั่วโมง
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 26,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  • โบรก CXM ปฏิเสธจ่ายกำไรเกือบ 6 ล้าน
                </div>
                <div
                  style={{
                    fontFamily: FONT_KANIT_600,
                    fontSize: 26,
                    color: COLORS.warningYellow,
                    whiteSpace: 'nowrap',
                  }}
                >
                  • อีเมลแจ้งข้อหา “Toxic Trading”
                </div>
              </div>

              <div
                style={{
                  fontFamily: FONT_KANIT_600,
                  fontSize: 20,
                  color: COLORS.silver,
                  whiteSpace: 'nowrap',
                }}
              >
                *เป็นคำบอกเล่าจากฝั่งผู้โพสต์เท่านั้น
              </div>
            </div>

            {/* Middle Evidence Post Band */}
            <EvidenceStillBand
              stillFile="stills/cxm-post-claim.png"
              highlightProgress={1}
              highlightTopPx={148}
              highlightHeightPx={96}
              style={{
                left: SAFE_LEFT + 10,
                top: 636,
              }}
            />

            {/* Bottom Final Question / Engagement Callout */}
            <div
              style={{
                position: 'absolute',
                left: SAFE_LEFT,
                top: 1036,
                width: SAFE_WIDTH,
                borderRadius: 20,
                background:
                  'linear-gradient(135deg, #E6192E 0%, #9E0816 100%)',
                border: `3px solid ${COLORS.goldBright}`,
                padding: '22px 24px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                boxShadow: '0 20px 50px rgba(0,0,0,0.9)',
                transform: `scale(${slamScale(frame, 279, 1.3)})`,
              }}
            >
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 42,
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                }}
              >
                ถือ 2 ชม. กำไรเกือบ 6 ล้าน แต่ไม่ได้เงิน?
              </div>
              <div
                style={{
                  fontFamily: FONT_KANIT_800,
                  fontSize: 36,
                  color: COLORS.warningYellow,
                  whiteSpace: 'nowrap',
                }}
              >
                คุณคิดยังไงกับเรื่องที่เธอเล่า? คอมเมนต์เลย 👇
              </div>
            </div>
          </AbsoluteFill>
        )}
      </AbsoluteFill>

      {/* Persistent Broadcast HUD + Persistent Legal Label (0.0s - 10.0s) */}
      <BroadcastHUD frame={frame} />
    </AbsoluteFill>
  );
};
