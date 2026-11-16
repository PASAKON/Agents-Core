#!/usr/bin/env python3
"""Build V5 Pure Knowledge & Basket cuts with ONLY the 17 CEO-Approved Mass-Editor SFX,
and with <div class="bl-ai-pill">เนื้อหานี้สร้างด้วย AI</div> removed.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
import wave
import numpy as np

def read_wav_s16(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    assert sw == 2, f"{path} sampwidth={sw} != 2"
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nch == 2:
        arr = arr.reshape(-1, 2)
    else:
        arr = np.stack([arr, arr], axis=1)
    return sr, arr

def write_wav_s16(path: Path, sr: int, arr_s16: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(arr_s16.astype(np.int16).tobytes())

WORK = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/basket-pilot1-work")
SFX_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/sfx-mass-pack/curated-48k")
MANIFEST = json.loads((SFX_DIR / "manifest.json").read_text(encoding="utf-8"))
PEAK_MS = {it["id"]: it["peak_time_ms"] for it in MANIFEST["sounds"]}

# Verify all 17 approved SFX exist
assert len(PEAK_MS) == 17, f"Expected 17 approved SFX, got {len(PEAK_MS)}"

SR = 48000
SFX_CACHE = {}
for sfx_id in PEAK_MS:
    wav_path = SFX_DIR / f"{sfx_id}.wav"
    sr, arr = read_wav_s16(wav_path)
    assert sr == SR, f"{wav_path} sr={sr} != {SR}"
    SFX_CACHE[sfx_id] = arr


def db_to_lin(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def load_voice_stereo_48k(src_wav: Path, duration_s: float, fade_tail: bool) -> np.ndarray:
    tmp_wav = WORK / "audio" / f"_tmp_vo_{src_wav.stem}_{duration_s:.2f}.wav"
    tmp_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(src_wav),
        "-t", f"{duration_s:.3f}",
        "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le",
        str(tmp_wav)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sr, arr = read_wav_s16(tmp_wav)
    tmp_wav.unlink(missing_ok=True)
    target_n = int(round(duration_s * SR))
    if len(arr) < target_n:
        pad = np.zeros((target_n - len(arr), 2), dtype=np.float32)
        arr = np.vstack([arr, pad])
    else:
        arr = arr[:target_n]
    if fade_tail:
        # 350ms smooth cosine/linear fade-out at the end so Pure Knowledge cuts end cleanly
        fade_n = int(0.35 * SR)
        if len(arr) > fade_n:
            ramp = np.linspace(1.0, 0.0, fade_n, dtype=np.float32)[:, None]
            arr[-fade_n:] *= ramp
    return arr


def mix_track_with_17sfx(src_wav: Path, out_wav: Path, duration_s: float, events: list[tuple[float, str, float]], fade_tail: bool):
    vo = load_voice_stereo_48k(src_wav, duration_s, fade_tail=fade_tail)
    n_samples = len(vo)
    sfx_bus = np.zeros_like(vo)

    for t_sync, sfx_id, gain_db in events:
        if t_sync >= duration_s - 0.05:
            continue
        assert sfx_id in SFX_CACHE, f"SFX {sfx_id} is NOT in the 17 CEO-approved pack!"
        clip = SFX_CACHE[sfx_id]
        peak_s = PEAK_MS[sfx_id] / 1000.0
        start_s = t_sync - peak_s
        start_idx = int(round(start_s * SR))
        gain = db_to_lin(gain_db)

        if start_idx < 0:
            clip_slice = clip[-start_idx:]
            dst_start = 0
        else:
            clip_slice = clip
            dst_start = start_idx

        dst_end = min(n_samples, dst_start + len(clip_slice))
        if dst_end > dst_start:
            sfx_bus[dst_start:dst_end] += clip_slice[:dst_end - dst_start] * gain

    mixed = vo + sfx_bus
    peak = np.max(np.abs(mixed))
    if peak > 0.98:
        mixed = mixed * (0.98 / peak)

    raw_wav = out_wav.with_suffix(".raw.wav")
    write_wav_s16(raw_wav, SR, mixed * 32767.0)

    # Normalize to -14.0 LUFS (-1.5 dBTP)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_wav),
        "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=11",
        "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le",
        str(out_wav)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw_wav.unlink(missing_ok=True)
    print(f"[OK] Mixed {out_wav.name} ({duration_s:.2f}s, {len([e for e in events if e[0] < duration_s - 0.05])} SFX events)")


# =========================================================================
# 17 CEO-Approved SFX Event Timelines for EP2 (T1), EP3 (T2), and EP1 (A)
# =========================================================================

# EP2 (T1): Loss Aversion & 2% Stop Loss Rule (Pure cutoff: 64.30s, Full Basket: 70.04s)
EVENTS_T1 = [
    # Beat 1 (0.00 - 7.92s): Hook
    (0.08, "boom_vine_01", -6.0),
    (0.55, "pop_alert_03", -9.0),
    (1.15, "shutter_modern_01", -8.0),
    (2.30, "whoosh_arrow_02", -8.5),
    (2.90, "record_scratch_03", -8.0),
    (3.45, "whoosh_clean_03", -8.5),
    (4.82, "impact_sub_03", -6.5),
    (5.27, "whoosh_arrow_02", -8.5),
    # Beat 2 (7.92 - 24.96s): Failed Habit
    (7.92, "whoosh_clean_03", -8.5),
    (8.10, "bubble_pop_02", -9.5),
    (10.50, "click_mouse_04", -8.5),
    (11.88, "bubble_pop_02", -9.5),
    (15.30, "typing_fast_02", -11.0),
    (17.20, "shatter_glass_02", -8.0),
    (19.78, "stamp_thud_05", -7.5),
    (22.10, "whoosh_arrow_02", -9.0),
    # Beat 3 (24.96 - 44.52s): Hidden Mechanism (Loss Aversion)
    (24.96, "impact_deep_whoosh_02", -6.5),
    (27.06, "shutter_old_02", -8.5),
    (30.62, "page_turn_01", -8.5),
    (30.80, "bubble_pop_02", -9.5),
    (34.92, "bubble_pop_02", -9.5),
    (38.38, "typing_fast_02", -11.0),
    (40.04, "pop_alert_03", -9.5),
    (42.80, "shatter_glass_02", -8.0),
    # Beat 4 (44.52 - 54.16s): Mechanism Pivot (2% Rule)
    (44.52, "switch_ui_05", -9.0),
    (44.65, "pop_alert_03", -9.5),
    (47.20, "page_turn_01", -8.5),
    (49.66, "stamp_thud_05", -7.5),
    (51.80, "typing_fast_02", -11.5),
    # Beat 5 (54.16 - 58.92s): Friction Removal
    (54.16, "whoosh_clean_03", -8.5),
    (56.64, "ding_bright_01", -9.0),
    # Beat 6 (58.92 - 64.30s Pure / 70.04s Basket)
    (58.96, "stamp_thud_05", -7.5),
    (61.40, "click_mouse_04", -9.0),
    (63.40, "ding_bright_01", -9.5),
    # Basket tail (only active if duration > 64.5s)
    (64.40, "pop_alert_03", -9.0),
    (64.50, "page_turn_01", -8.5),
    (67.18, "impact_sub_03", -7.0),
    (68.00, "ding_bright_01", -9.0),
]

# EP3 (T2): Single-Screen Context Switching 3s Delay (Pure cutoff: 61.85s, Full Basket: 67.04s)
EVENTS_T2 = [
    # Beat 1 (0.00 - 8.56s): Hook
    (0.08, "boom_vine_01", -6.0),
    (0.55, "pop_alert_03", -9.0),
    (1.20, "shutter_modern_01", -8.0),
    (2.40, "whoosh_arrow_02", -8.5),
    (3.58, "record_scratch_03", -8.0),
    (4.20, "whoosh_clean_03", -8.5),
    (5.38, "impact_sub_03", -6.5),
    (5.50, "typing_fast_02", -11.0),
    (6.80, "pop_alert_03", -9.0),
    # Beat 2 (8.56 - 22.72s): Failed Habit
    (8.56, "whoosh_clean_03", -8.5),
    (8.70, "bubble_pop_02", -9.5),
    (11.20, "click_mouse_04", -8.5),
    (13.84, "bubble_pop_02", -9.5),
    (15.10, "shatter_glass_02", -8.5),
    (17.22, "stamp_thud_05", -7.5),
    (20.00, "whoosh_arrow_02", -9.0),
    # Beat 3 (22.72 - 38.72s): Hidden Mechanism (Context Switching)
    (22.72, "impact_deep_whoosh_02", -6.5),
    (25.20, "shutter_old_02", -8.5),
    (27.44, "page_turn_01", -8.5),
    (28.44, "bubble_pop_02", -9.5),
    (33.06, "whoosh_arrow_02", -8.5),
    (35.32, "shatter_glass_02", -8.0),
    # Beat 4 (38.72 - 50.36s): Mechanism Pivot (Dual Screen)
    (38.72, "switch_ui_05", -9.0),
    (38.80, "pop_alert_03", -9.5),
    (43.70, "page_turn_01", -8.5),
    (43.80, "bubble_pop_02", -9.5),
    (47.60, "bubble_pop_02", -9.5),
    # Beat 5 (50.36 - 56.36s): Friction Removal
    (50.36, "whoosh_clean_03", -8.5),
    (54.00, "ding_bright_01", -9.0),
    # Beat 6 (56.36 - 61.85s Pure / 67.04s Basket)
    (56.38, "stamp_thud_05", -7.5),
    (59.00, "switch_ui_05", -9.0),
    (61.00, "ding_bright_01", -9.5),
    # Basket tail (only active if duration > 62.0s)
    (61.95, "pop_alert_03", -9.0),
    (64.50, "impact_sub_03", -7.0),
    (65.30, "ding_bright_01", -9.0),
]

# EP1 (A): Blue Light & Melatonin Suppression (Full Basket: 65.44s)
EVENTS_A_BASKET = [
    (0.08, "boom_vine_01", -6.0),
    (0.55, "pop_alert_03", -9.0),
    (1.15, "shutter_modern_01", -8.0),
    (2.30, "whoosh_arrow_02", -8.5),
    (2.82, "record_scratch_03", -8.0),
    (3.45, "whoosh_clean_03", -8.5),
    (4.58, "impact_sub_03", -6.5),
    (5.05, "whoosh_arrow_02", -8.5),
    (6.92, "whoosh_clean_03", -8.5),
    (7.05, "typing_fast_02", -11.0),
    (8.92, "pop_alert_03", -9.5),
    (11.26, "whoosh_arrow_02", -8.5),
    (11.35, "bubble_pop_02", -9.5),
    (13.24, "shatter_glass_02", -8.0),
    (16.02, "stamp_thud_05", -7.5),
    (18.50, "click_mouse_04", -9.0),
    (21.20, "impact_deep_whoosh_02", -6.5),
    (23.08, "bubble_pop_02", -9.5),
    (26.70, "shutter_old_02", -8.5),
    (26.80, "bubble_pop_02", -9.5),
    (29.68, "bubble_pop_02", -9.5),
    (31.98, "stamp_thud_05", -7.5),
    (34.50, "click_mouse_04", -8.5),
    (37.12, "switch_ui_05", -9.0),
    (37.35, "pop_alert_03", -9.5),
    (42.26, "page_turn_01", -8.5),
    (42.35, "bubble_pop_02", -9.5),
    (44.10, "bubble_pop_02", -9.5),
    (48.40, "whoosh_clean_03", -8.5),
    (50.20, "ding_bright_01", -9.0),
    (53.16, "stamp_thud_05", -7.5),
    (57.20, "ding_bright_01", -9.5),
    # Basket tail (58.50 - 65.44s)
    (58.50, "pop_alert_03", -9.0),
    (58.60, "switch_ui_05", -9.0),
    (62.20, "impact_sub_03", -7.0),
    (63.10, "ding_bright_01", -9.0),
]


def setup_workdir(src_dir: Path, dst_dir: Path, duration_s: float, plate_src: Path, plate_name: str, audio_src: Path, audio_name: str, pure_cutoff: float | None):
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Copy hyperframes.json & package.json, symlink node_modules & assets
    for fn in ["hyperframes.json", "package.json"]:
        shutil.copy2(src_dir / fn, dst_dir / fn)
    for sym in ["node_modules", "assets"]:
        s = src_dir / sym
        if s.exists():
            os.symlink(s.resolve(), dst_dir / sym)

    (dst_dir / "clips").mkdir(exist_ok=True)
    (dst_dir / "audio").mkdir(exist_ok=True)

    # Trim or copy plate video
    dst_plate = dst_dir / "clips" / plate_name
    if pure_cutoff is not None:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(plate_src),
            "-t", f"{duration_s:.2f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an",
            str(dst_plate)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.symlink(plate_src.resolve(), dst_plate)

    # Copy audio into dst_dir/audio/ and root audio.wav
    shutil.copy2(audio_src, dst_dir / "audio" / audio_name)
    shutil.copy2(audio_src, dst_dir / "audio.wav")

    # Transform index.html
    html = (src_dir / "index.html").read_text(encoding="utf-8")
    # 1. Remove AI badge pill completely
    html = html.replace('<div class="bl-ai-pill">เนื้อหานี้สร้างด้วย AI</div>', '')
    # 2. Update duration, plate src, and audio src
    html = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{duration_s:.2f}"', html)
    html = re.sub(r'src="clips/[^"]+"', f'src="clips/{plate_name}"', html)
    html = re.sub(r'src="audio/[^"]+"', f'src="audio/{audio_name}"', html)

    if pure_cutoff is not None:
        # Remove calloutBox, caption, and kinetic calls that start at or after pure_cutoff
        lines_out = []
        skip_kinetic = False
        for line in html.splitlines():
            if skip_kinetic:
                if "], 380);" in line:
                    skip_kinetic = False
                continue
            m_call = re.search(r'calloutBox\(([0-9.]+),', line)
            if m_call and float(m_call.group(1)) >= pure_cutoff - 0.1:
                continue
            m_cap = re.search(r'caption\(([0-9.]+),', line)
            if m_cap and float(m_cap.group(1)) >= pure_cutoff - 0.1:
                continue
            m_kin = re.search(r'kinetic\([0-9]+,\s*([0-9.]+),', line)
            if m_kin and float(m_kin.group(1)) >= pure_cutoff - 0.1:
                skip_kinetic = True
                continue
            lines_out.append(line)
        html = "\n".join(lines_out) + "\n"

    (dst_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"[OK] Prepared workdir {dst_dir.name} (duration={duration_s:.2f}s, pure_cutoff={pure_cutoff})")


def main():
    vo_t1 = WORK / "tts_65s/takes/T1_65s_fast.wav"
    vo_t2 = WORK / "tts_65s/takes/T2_65s_slow.wav"
    vo_a = WORK / "tts_65s/takes/A_pilot1_65s_slow.wav"

    # 1. Mix audio tracks with the 17 CEO-approved SFX
    aud_t1_pure = WORK / "audio/T1_v5_64s_pure_14lufs.wav"
    mix_track_with_17sfx(vo_t1, aud_t1_pure, 64.30, EVENTS_T1, fade_tail=True)

    aud_t2_pure = WORK / "audio/T2_v5_62s_pure_14lufs.wav"
    mix_track_with_17sfx(vo_t2, aud_t2_pure, 61.85, EVENTS_T2, fade_tail=True)

    aud_t1_basket = WORK / "audio/T1_v5_70s_basket_14lufs.wav"
    mix_track_with_17sfx(vo_t1, aud_t1_basket, 70.04, EVENTS_T1, fade_tail=False)

    aud_t2_basket = WORK / "audio/T2_v5_67s_basket_14lufs.wav"
    mix_track_with_17sfx(vo_t2, aud_t2_basket, 67.04, EVENTS_T2, fade_tail=False)

    aud_a_basket = WORK / "audio/A_v5_65s_basket_14lufs.wav"
    mix_track_with_17sfx(vo_a, aud_a_basket, 65.44, EVENTS_A_BASKET, fade_tail=False)

    # 2. Setup HyperFrames workdirs
    setup_workdir(
        src_dir=WORK / "cut_pair1_T1_65s",
        dst_dir=WORK / "cut_pair1_T1_v5_64s_pure",
        duration_s=64.30,
        plate_src=WORK / "cut_pair1_T1_65s/clips/v4_plate_track.mp4",
        plate_name="v5_plate_64s.mp4",
        audio_src=aud_t1_pure,
        audio_name="T1_v5_64s_pure_14lufs.wav",
        pure_cutoff=64.30,
    )

    setup_workdir(
        src_dir=WORK / "cut_pair1_T2_65s",
        dst_dir=WORK / "cut_pair1_T2_v5_62s_pure",
        duration_s=61.85,
        plate_src=WORK / "cut_pair1_T2_65s/clips/v4_plate_track.mp4",
        plate_name="v5_plate_62s.mp4",
        audio_src=aud_t2_pure,
        audio_name="T2_v5_62s_pure_14lufs.wav",
        pure_cutoff=61.85,
    )

    setup_workdir(
        src_dir=WORK / "cut_pair1_T1_65s",
        dst_dir=WORK / "cut_pair1_T1_v5_70s_basket",
        duration_s=70.04,
        plate_src=WORK / "cut_pair1_T1_65s/clips/v4_plate_track.mp4",
        plate_name="v4_plate_track.mp4",
        audio_src=aud_t1_basket,
        audio_name="T1_v5_70s_basket_14lufs.wav",
        pure_cutoff=None,
    )

    setup_workdir(
        src_dir=WORK / "cut_pair1_T2_65s",
        dst_dir=WORK / "cut_pair1_T2_v5_67s_basket",
        duration_s=67.04,
        plate_src=WORK / "cut_pair1_T2_65s/clips/v4_plate_track.mp4",
        plate_name="v4_plate_track.mp4",
        audio_src=aud_t2_basket,
        audio_name="T2_v5_67s_basket_14lufs.wav",
        pure_cutoff=None,
    )

    setup_workdir(
        src_dir=WORK / "cut_pilot1_A_65s",
        dst_dir=WORK / "cut_pilot1_A_v5_65s_basket",
        duration_s=65.44,
        plate_src=WORK / "cut_pilot1_A_65s/clips/v4_plate_track.mp4",
        plate_name="v4_plate_track.mp4",
        audio_src=aud_a_basket,
        audio_name="A_v5_65s_basket_14lufs.wav",
        pure_cutoff=None,
    )


if __name__ == "__main__":
    main()
