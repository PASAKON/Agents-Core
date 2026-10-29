"""Small offline fixtures: four solid-color shots, three hard cuts."""
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "film_breakdown.py"
spec = importlib.util.spec_from_file_location("film_breakdown", SCRIPT)
film = importlib.util.module_from_spec(spec)
spec.loader.exec_module(film)
pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                                reason="ffmpeg/ffprobe required")


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "cuts.mp4"
    args = ["ffmpeg", "-v", "error", "-nostdin", "-filter_complex_threads", "1"]
    for color in ("black", "white", "red", "blue"):
        args += ["-f", "lavfi", "-i", f"color={color}:s=160x90:r=10:d=2"]
    subprocess.run(args + ["-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]",
                          "-map", "[v]", "-c:v", "mpeg4", "-threads", "1", str(path)], check=True)
    return path


def test_cli_three_cuts(video, tmp_path):
    out = tmp_path / "result"
    subprocess.run([sys.executable, str(SCRIPT), str(video), "--out", str(out)], check=True,
                   capture_output=True)
    summary = json.loads((out / "summary.json").read_text())
    rows = list(csv.DictReader((out / "shots.csv").open()))
    assert abs(summary["n_shots"] - 1 - 3) <= 1
    assert summary["runtime_s"] == pytest.approx(8, abs=0.1)
    assert summary["n_shots"] == len(rows) == len(list((out / "thumbs").glob("*.jpg")))
    assert sum(float(row["len_s"]) for row in rows) == pytest.approx(8)
    assert summary["shots_per_min"] == [len(rows)]
    for thumb in (out / "thumbs").glob("*.jpg"):
        width = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                         "-show_entries", "stream=width", "-of", "csv=p=0", str(thumb)])
        assert int(width) == 320


def test_ffmpeg_fallback(video, monkeypatch):
    monkeypatch.setitem(sys.modules, "scenedetect", None)
    cuts, method = film.video_cuts(video, 27)
    assert method == "ffmpeg"
    assert cuts == pytest.approx([2, 4, 6], abs=0.11)


def test_storyboard(video, tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-threads", "1", "-filter_threads", "1",
                    "-i", str(video), "-vf", "fps=1", "-threads", "1",
                    str(frames / "frame%d.png")], check=True)
    out = tmp_path / "coarse"
    film.main(["--storyboard", str(frames), "--interval-s", "1", "--out", str(out)])
    summary = json.loads((out / "summary.json").read_text())
    assert summary["coarse"] is True
    assert summary["method"] == "storyboard"
    assert summary["n_shots"] == 4
    assert summary["runtime_s"] == 8
    assert "Coarse" in summary["notes"]
    assert all(row["method"] == "storyboard" for row in
               csv.DictReader((out / "shots.csv").open()))


def test_summary_and_boundaries():
    shots = film.shot_table([0, 60, 60, 90, 121, -1], 121, "ffmpeg")
    summary = film.summarize(shots, 121, "ffmpeg")
    assert summary["shots_per_min"] == [1, 2, 0]
    assert summary["median_shot_len_s"] == 31
    assert summary["avg_shot_len_s"] == pytest.approx(121 / 3)
    assert [s["len_s"] for s in summary["longest_shots"]] == [60, 31, 30]
    assert film.shot_table([], 2, "ffmpeg")[0]["len_s"] == 2
    assert sorted([Path("frame10.png"), Path("frame2.png")], key=film.natural_key)[0].name == "frame2.png"


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_invalid_interval(tmp_path, value):
    with pytest.raises(SystemExit):
        film.main(["--storyboard", str(tmp_path), "--interval-s", value, "--out", str(tmp_path / "out")])


def test_missing_input(tmp_path):
    with pytest.raises(SystemExit):
        film.main(["https://example.com/video.mp4", "--out", str(tmp_path)])
    with pytest.raises(ValueError, match="no supported images"):
        film.main(["--storyboard", str(tmp_path), "--interval-s", "2", "--out", str(tmp_path / "out")])
