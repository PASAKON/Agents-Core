"""Spectral-flux onset detection + band-energy time series on the reference's
audio track — numpy FFT only (no scipy/librosa). Used to find SFX onsets (P4)
and to estimate whether there is a music bed and whether it ducks under
speech, by comparing low/high-band RMS against the whisper speech segments.

Usage: python audio_spectral.py ref_44k_stereo.wav bands_out.csv > measurements/audio_onsets.csv
Also writes bands_out.csv (t, rms_db, low_db, mid_db, high_db).
"""
import subprocess, sys
import numpy as np

WAV = sys.argv[1]
OUT_BANDS = sys.argv[2] if len(sys.argv) > 2 else "audio_bands.csv"

SR = 44100
raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", WAV, "-ar", str(SR), "-ac", "1",
     "-f", "s16le", "-acodec", "pcm_s16le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0

WIN, HOP = 2048, 512
n_frames = (len(x) - WIN) // HOP
window = np.hanning(WIN)
freqs = np.fft.rfftfreq(WIN, 1 / SR)

specs = np.empty((n_frames, len(freqs)), np.float32)
for i in range(n_frames):
    seg = x[i * HOP: i * HOP + WIN] * window
    specs[i] = np.abs(np.fft.rfft(seg))

# spectral flux: sum of positive frame-to-frame magnitude increases
flux = np.zeros(n_frames)
flux[1:] = np.maximum(specs[1:] - specs[:-1], 0).sum(axis=1)
flux_db_scale = flux / (flux.max() + 1e-9)

t = (np.arange(n_frames) * HOP + WIN / 2) / SR

# band energies for bed/ducking analysis
lowband = (freqs >= 40) & (freqs < 250)
midband = (freqs >= 250) & (freqs < 3400)   # ~speech band
highband = (freqs >= 4000) & (freqs < 12000)

def band_db(mask):
    e = (specs[:, mask] ** 2).sum(axis=1)
    return 10 * np.log10(e + 1e-9)

rms_db = band_db(np.ones(len(freqs), bool))
low_db = band_db(lowband)
mid_db = band_db(midband)
high_db = band_db(highband)

with open(OUT_BANDS, "w") as f:
    f.write("t,rms_db,low_db,mid_db,high_db\n")
    for i in range(n_frames):
        f.write(f"{t[i]:.4f},{rms_db[i]:.2f},{low_db[i]:.2f},{mid_db[i]:.2f},{high_db[i]:.2f}\n")

# onset picking: local max in flux, above adaptive baseline
baseline = np.convolve(flux_db_scale, np.ones(15) / 15, mode="same")
score = flux_db_scale - baseline
thr = 0.04
cand = [i for i in range(2, n_frames - 2)
        if score[i] > thr and flux_db_scale[i] >= flux_db_scale[i - 1] and flux_db_scale[i] >= flux_db_scale[i + 1]]
merged = []
for i in cand:
    if merged and t[i] - t[merged[-1]] < 0.12:
        if score[i] > score[merged[-1]]:
            merged[-1] = i
        continue
    merged.append(i)

print("t,flux_score,centroid_hz,high_ratio,low_ratio")
for i in merged:
    spec = specs[i]
    centroid = float((freqs * spec).sum() / (spec.sum() + 1e-9))
    total_e = (spec ** 2).sum() + 1e-9
    high_ratio = float((spec[highband] ** 2).sum() / total_e)
    low_ratio = float((spec[lowband] ** 2).sum() / total_e)
    print(f"{t[i]:.4f},{score[i]:.4f},{centroid:.0f},{high_ratio:.3f},{low_ratio:.3f}")
