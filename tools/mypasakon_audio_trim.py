#!/usr/bin/env python3
"""tools/mypasakon_audio_trim.py — MYPASAKON Audio Dead-Air & Retake Trimmer, 15s Lipsync Chunker,
Existing-Lipsync Frame-Exact Syncer, and Final Cut Verifier.

Subcommands:
  1. inspect    --input <raw.mp4|.mov> [--insert <pickup.m4a>] --out-dir <dir>
  2. render     --out-dir <dir> --edl-spec <edl_spec.json> --out-prefix <name>
  3. chunks     --audio <trimmed.mp3> --edl <edit_decision_list.json> --out-dir <dir> [--chunk-sec 15] [--count 3]
  4. sync-lip   --edl <edit_decision_list.json> --master <trimmed.mp3> --lip <name=path.mp4> --out-dir <dir>
  5. verify-cut --video <final.mp4> --audio <trimmed.mp3> [--sheet <qc_sheet.jpg>]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np


def _snap_zero_crossing(buf: np.ndarray, idx: int, radius: int = 220) -> int:
    lo = max(0, idx - radius)
    hi = min(len(buf) - 1, idx + radius)
    if hi <= lo:
        return idx
    seg = buf[lo : hi + 1]
    zc = np.where(seg[:-1] * seg[1:] <= 0)[0]
    if len(zc) > 0:
        best = zc[np.argmin(np.abs((lo + zc) - idx))]
        return int(lo + best)
    return int(lo + np.argmin(np.abs(seg)))


def _read_wav_mono(p: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(p), "rb") as wf:
        sr = wf.getframerate()
        arr = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return sr, arr


def cmd_inspect(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_wav = out_dir / "raw_44k.wav"
    raw_mp3 = out_dir / "raw_extracted.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(args.input), "-vn", "-ac", "1", "-ar", "44100", str(raw_wav)],
        check=True, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_wav), "-b:a", "192k", str(raw_mp3)],
        check=True, stderr=subprocess.DEVNULL,
    )
    if args.insert:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(args.insert), "-vn", "-ac", "1", "-ar", "44100", str(out_dir / "insert_44k.wav")],
            check=True, stderr=subprocess.DEVNULL,
        )

    sr, pcm = _read_wav_mono(raw_wav)
    hop = sr // 100  # 10ms
    n_frames = len(pcm) // hop
    frames = pcm[: n_frames * hop].reshape(n_frames, hop)
    db = 20.0 * np.log10(np.sqrt(np.mean(frames * frames, axis=1) + 1e-12))
    p10 = float(np.percentile(db, 10))
    thresh_db = float(np.clip(p10 + 14.0, -42.0, -32.0))
    is_speech = db > thresh_db

    # Bridge micro-gaps < 180ms, drop clicks < 80ms
    i = 0
    while i < n_frames:
        if not is_speech[i]:
            j = i
            while j < n_frames and not is_speech[j]:
                j += 1
            if 0 < i and j < n_frames and (j - i) < 18:
                is_speech[i:j] = True
            i = j
        else:
            i += 1

    islands = []
    i = 0
    while i < n_frames:
        if is_speech[i]:
            j = i
            while j < n_frames and is_speech[j]:
                j += 1
            if (j - i) >= 8:
                s_t = max(0.0, (i - 6) * 0.01)
                e_t = min(len(pcm) / sr, (j + 9) * 0.01)
                if islands and s_t <= islands[-1]["end"] + 0.04:
                    islands[-1]["end"] = round(max(islands[-1]["end"], e_t), 3)
                    islands[-1]["dur"] = round(islands[-1]["end"] - islands[-1]["start"], 3)
                else:
                    islands.append({"id": len(islands), "start": round(s_t, 3), "end": round(e_t, 3), "dur": round(e_t - s_t, 3)})
            i = j
        else:
            i += 1

    tot_dur = round(len(pcm) / sr, 3)
    sp_dur = round(sum(x["dur"] for x in islands), 3)
    out_json = {
        "raw_duration_s": tot_dur,
        "speech_duration_s": sp_dur,
        "dead_air_s": round(tot_dur - sp_dur, 3),
        "thresh_db": round(thresh_db, 2),
        "islands": islands,
    }
    (out_dir / "speech_islands.json").write_text(json.dumps(out_json, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in out_json.items() if k != "islands"}, ensure_ascii=False))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Assemble trimmed master MP3 + M4A + edit_decision_list.json from an EDL spec JSON.
    edl_spec.json format:
      {"lip_ranges": {"lip_1.mp4": [0.0, 30.04]}, "segments": [{"source": "raw", "start": 0.4, "end": 4.7, "pause": 0.1, "note": "..."}]}
    """
    out_dir = Path(args.out_dir)
    spec = json.loads(Path(args.edl_spec).read_text())
    sr, raw_pcm = _read_wav_mono(out_dir / "raw_44k.wav")
    ins_wav = out_dir / "insert_44k.wav"
    ins_pcm = np.zeros(1, dtype=np.float32)
    if ins_wav.exists():
        _, ins_pcm = _read_wav_mono(ins_wav)
        r_act = raw_pcm[np.abs(raw_pcm) > 0.02]
        i_act = ins_pcm[np.abs(ins_pcm) > 0.02]
        if len(r_act) > 0 and len(i_act) > 0:
            gain = float(np.sqrt(np.mean(r_act ** 2)) / (np.sqrt(np.mean(i_act ** 2)) + 1e-8))
            ins_pcm = np.clip(ins_pcm * gain, -0.98, 0.98)

    lip_ranges = {k: (float(v[0]), float(v[1])) for k, v in spec.get("lip_ranges", {}).items()}
    fade_samples = int(0.010 * sr)
    fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_samples, dtype=np.float32)))
    fade_out = fade_in[::-1]

    out_chunks = []
    edl_final = []
    cursor_samples = 0
    for row in spec["segments"]:
        src = row.get("source", "raw")
        buf = raw_pcm if src == "raw" else ins_pcm
        i0 = _snap_zero_crossing(buf, int(round(float(row["start"]) * sr)))
        i1 = _snap_zero_crossing(buf, int(round(float(row["end"]) * sr)))
        if i1 - i0 < fade_samples * 2 + 10:
            continue
        clip = buf[i0:i1].copy()
        clip[:fade_samples] *= fade_in
        clip[-fade_samples:] *= fade_out
        out_start_s = cursor_samples / sr
        out_end_s = (cursor_samples + len(clip)) / sr
        pause_sec = float(row.get("pause", 0.10))

        lip_match = None
        if src == "raw":
            for lname, (ls, le) in lip_ranges.items():
                ov_s, ov_e = max(i0 / sr, ls), min(i1 / sr, le)
                if ov_e - ov_s >= 0.20:
                    lip_match = {"clip": lname, "lip_in_s": round(ov_s - ls, 4), "lip_out_s": round(ov_e - ls, 4)}
                    break

        edl_final.append({
            "source": src,
            "src_start_s": round(i0 / sr, 4),
            "src_end_s": round(i1 / sr, 4),
            "out_start_s": round(out_start_s, 4),
            "out_end_s": round(out_end_s, 4),
            "dur_s": round(len(clip) / sr, 4),
            "pause_after_s": pause_sec,
            "lipsync": lip_match,
            "note": row.get("note", ""),
        })
        out_chunks.append(clip)
        cursor_samples += len(clip)
        p_samp = int(round(pause_sec * sr))
        if p_samp > 0:
            out_chunks.append(np.zeros(p_samp, dtype=np.float32))
            cursor_samples += p_samp

    assembled = np.concatenate(out_chunks)
    pre_wav = out_dir / "_trimmed_pre.wav"
    with wave.open(str(pre_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.clip(assembled, -0.99, 0.99) * 32767.0).astype(np.int16).tobytes())

    af_chain = "highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11"
    out_mp3 = out_dir / f"{args.out_prefix}.mp3"
    out_m4a = out_dir / f"{args.out_prefix}.m4a"
    subprocess.run(["ffmpeg", "-y", "-i", str(pre_wav), "-af", af_chain, "-ar", "44100", "-b:a", "192k", str(out_mp3)], check=True, stderr=subprocess.DEVNULL)
    subprocess.run(["ffmpeg", "-y", "-i", str(pre_wav), "-af", af_chain, "-ar", "44100", "-c:a", "aac", "-b:a", "128k", str(out_m4a)], check=True, stderr=subprocess.DEVNULL)
    pre_wav.unlink(missing_ok=True)

    tot_s = len(assembled) / sr
    raw_tot = len(raw_pcm) / sr + (len(ins_pcm) / sr if ins_wav.exists() else 0.0)
    summary = {
        "raw_duration_s": round(raw_tot, 2),
        "trimmed_duration_s": round(tot_s, 2),
        "removed_seconds": round(raw_tot - tot_s, 2),
        "removed_pct": round((1.0 - tot_s / max(raw_tot, 0.01)) * 100, 1),
        "kept_segments": len(edl_final),
        "edl": edl_final,
    }
    (out_dir / "edit_decision_list.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "edl"}, ensure_ascii=False, indent=2))
    return 0


def cmd_chunks(args: argparse.Namespace) -> int:
    """Slice 3 x ~15s clean voice chunks on natural EDL phrase boundaries from the Gate 1 trimmed master."""
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    edl_doc = json.loads(Path(args.edl).read_text())
    edl = edl_doc["edl"]
    tot = float(edl_doc["trimmed_duration_s"])
    chunk_s = float(args.chunk_sec)

    anchors = [0.0, max(0.0, tot * 0.45 - chunk_s * 0.5), max(0.0, tot - chunk_s)]
    labels = ["a", "b", "c"]
    picked = []
    for lbl, anc in zip(labels[: args.count], anchors[: args.count]):
        start_row = min(edl, key=lambda r: abs(r["out_start_s"] - anc))
        s0 = start_row["out_start_s"]
        end_candidates = [r for r in edl if r["out_end_s"] > s0 + 8.0 and r["out_end_s"] <= s0 + chunk_s + 2.5]
        s1 = end_candidates[-1]["out_end_s"] if end_candidates else min(tot, s0 + chunk_s)
        cname = f"lipsync_chunk_{lbl}_{int(round(s0))}s-{int(round(s1))}s.mp3"
        cpath = out_dir / cname
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{s0:.4f}", "-to", f"{s1:.4f}", "-i", str(args.audio), "-c:a", "libmp3lame", "-b:a", "192k", str(cpath)],
            check=True, stderr=subprocess.DEVNULL,
        )
        picked.append({"part": lbl, "file": str(cpath), "start_s": round(s0, 3), "end_s": round(s1, 3), "dur_s": round(s1 - s0, 3)})
    (out_dir / "lipsync_chunks.json").write_text(json.dumps(picked, ensure_ascii=False, indent=2))
    print(json.dumps(picked, ensure_ascii=False, indent=2))
    return 0


def cmd_sync_lip(args: argparse.Namespace) -> int:
    """Frame-lock pre-existing raw-timed Lipsync MP4s onto the trimmed 30fps timeline (0-frame drift)."""
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    edl = json.loads(Path(args.edl).read_text())["edl"]
    fps = 30
    summary = {}
    for spec in args.lip:
        gname, clip_path_s = spec.split("=", 1)
        clip_path = Path(clip_path_s)
        cname = clip_path.name
        rows = [r for r in edl if r.get("lipsync") and r["lipsync"]["clip"] == cname]
        if not rows:
            continue
        f_start = int(round(rows[0]["out_start_s"] * fps))
        f_end = int(round((rows[-1]["out_end_s"] + rows[-1]["pause_after_s"]) * fps))
        target_frames = f_end - f_start
        parts_fc, concat_inputs, allocated = [], [], 0
        for idx, r in enumerate(rows):
            next_out_s = rows[idx + 1]["out_start_s"] if idx + 1 < len(rows) else (f_end / fps)
            n_frames = (int(round(next_out_s * fps)) - f_start) - allocated
            if n_frames <= 0:
                continue
            lip_in = r["lipsync"]["lip_in_s"]
            dur_needed = n_frames / fps
            parts_fc.append(
                f"[0:v]trim=start={lip_in:.4f}:duration={dur_needed + 0.05:.4f},setpts=PTS-STARTPTS,fps={fps},tpad=stop_mode=clone:stop_duration=0.3,trim=end_frame={n_frames}[v{idx}];"
                f"[0:a]atrim=start={lip_in:.4f}:duration={dur_needed:.4f},asetpts=PTS-STARTPTS,apad=whole_dur={dur_needed:.4f}[a{idx}]"
            )
            concat_inputs.append(f"[v{idx}][a{idx}]")
            allocated += n_frames
        fc = ";".join(parts_fc) + ";" + "".join(concat_inputs) + f"concat=n={len(concat_inputs)}:v=1:a=1[vout][aout]"
        out_p = out_dir / f"{gname}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(clip_path), "-filter_complex", fc,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", str(out_p),
        ], check=True, stderr=subprocess.DEVNULL)
        p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(out_p)], capture_output=True, text=True)
        summary[gname] = {"file": str(out_p), "start_frame": f_start, "end_frame": f_end, "frames": int(p.stdout.strip()), "expected_frames": target_frames}
    (out_dir / "sync_manifest.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


def cmd_verify_cut(args: argparse.Namespace) -> int:
    vid = Path(args.video)
    aud = Path(args.audio)
    p = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(vid)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(p.stdout)
    vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    astream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not vstream or not astream:
        raise SystemExit("FAIL: missing video or audio stream")
    w, h = int(vstream["width"]), int(vstream["height"])
    fps = eval(vstream["r_frame_rate"])
    vdur = float(info["format"]["duration"])

    pa = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(aud)],
        capture_output=True, text=True, check=True,
    )
    adur = float(json.loads(pa.stdout)["format"]["duration"])

    pe = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(vid), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m_lufs = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", pe.stderr)
    lufs = float(m_lufs[-1]) if m_lufs else -99.0

    if args.sheet:
        from PIL import Image, ImageDraw
        cols, rows = 4, 2
        tw, th = 360, 640
        grid = Image.new("RGB", (cols * tw, rows * th), (4, 10, 7))
        draw = ImageDraw.Draw(grid)
        for i in range(8):
            ts = round(vdur * (0.04 + 0.125 * i), 2)
            tmp = vid.parent / f"_qc_{i}.jpg"
            subprocess.run(["ffmpeg", "-y", "-ss", str(ts), "-i", str(vid), "-vf", f"scale={tw}:{th}", "-frames:v", "1", "-q:v", "3", str(tmp)], check=True, stderr=subprocess.DEVNULL)
            grid.paste(Image.open(tmp), ((i % cols) * tw, (i // cols) * th))
            draw.rectangle([(i % cols) * tw + 8, (i // cols) * th + 8, (i % cols) * tw + 110, (i // cols) * th + 34], fill=(0, 0, 0))
            draw.text(((i % cols) * tw + 14, (i // cols) * th + 12), f"t={ts:.1f}s", fill=(124, 255, 0))
            tmp.unlink(missing_ok=True)
        Path(args.sheet).parent.mkdir(parents=True, exist_ok=True)
        grid.save(args.sheet, quality=90)

    errors = []
    if (w, h) != (1080, 1920):
        errors.append(f"resolution {w}x{h} != 1080x1920")
    if abs(fps - 30.0) > 0.1:
        errors.append(f"fps {fps} != 30")
    if abs(vdur - adur) > 0.12:
        errors.append(f"duration drift video={vdur:.3f}s vs audio={adur:.3f}s")
    if not (-16.5 <= lufs <= -11.5):
        errors.append(f"integrated loudness {lufs:.1f} LUFS outside -16.5..-11.5 LUFS")

    res = {"ok": not errors, "width": w, "height": h, "fps": fps, "video_dur_s": round(vdur, 3), "audio_dur_s": round(adur, 3), "lufs": lufs, "errors": errors}
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="tools/mypasakon_audio_trim.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ins = sub.add_parser("inspect")
    p_ins.add_argument("--input", required=True)
    p_ins.add_argument("--insert")
    p_ins.add_argument("--out-dir", required=True)

    p_ren = sub.add_parser("render")
    p_ren.add_argument("--out-dir", required=True)
    p_ren.add_argument("--edl-spec", required=True)
    p_ren.add_argument("--out-prefix", default="MYPASAKON_Trimmed_Clean")

    p_chk = sub.add_parser("chunks")
    p_chk.add_argument("--audio", required=True)
    p_chk.add_argument("--edl", required=True)
    p_chk.add_argument("--out-dir", required=True)
    p_chk.add_argument("--chunk-sec", type=float, default=15.0)
    p_chk.add_argument("--count", type=int, default=3)

    p_syn = sub.add_parser("sync-lip")
    p_syn.add_argument("--edl", required=True)
    p_syn.add_argument("--master", required=True)
    p_syn.add_argument("--lip", action="append", required=True)
    p_syn.add_argument("--out-dir", required=True)

    p_ver = sub.add_parser("verify-cut")
    p_ver.add_argument("--video", required=True)
    p_ver.add_argument("--audio", required=True)
    p_ver.add_argument("--sheet")

    args = ap.parse_args()
    if args.cmd == "inspect":
        return cmd_inspect(args)
    if args.cmd == "render":
        return cmd_render(args)
    if args.cmd == "chunks":
        return cmd_chunks(args)
    if args.cmd == "sync-lip":
        return cmd_sync_lip(args)
    return cmd_verify_cut(args)


if __name__ == "__main__":
    sys.exit(main())
