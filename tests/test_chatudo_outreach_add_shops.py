"""Offline coverage of append-only O1 imports."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

openpyxl = pytest.importorskip("openpyxl")
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/chatudo_outreach_drive.py"
spec = importlib.util.spec_from_file_location("outreach_drive", SCRIPT)
drive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drive)
sheet = drive.sheet


@pytest.fixture
def env(tmp_path, monkeypatch):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet.SHOP
    for i, (name, head, _, kind) in enumerate(sheet.SHOP_COLS, 1):
        ws.cell(1, i, head)
        for r in range(2, 7):
            if name == "num":
                ws.cell(r, i, r - 1)
            elif kind.startswith("formula"):
                ws.cell(r, i, "computed")
    msg = wb.create_sheet(sheet.MSG)
    msg["D2"] = "ข้อความ"
    msg["D3"] = "existing message"
    calls = []
    monkeypatch.setattr(drive, "WORK", str(tmp_path))
    monkeypatch.setattr(drive, "export", lambda *_: copy.deepcopy(wb))
    monkeypatch.setattr(drive.g, "access_token", lambda: pytest.fail("auth forbidden"))

    def api(url, **kwargs):
        calls.append((url, kwargs))
        if "batchGet" in url:
            return {"valueRanges": [{"range": r} for r in parse_qs(urlsplit(url).query)["ranges"]]}
        payload = json.loads(kwargs["data"])
        for item in payload["data"]:
            ws[item["range"].split("!")[1]] = item["values"][0][0]
        return {}

    monkeypatch.setattr(drive.g, "api", api)

    def csv_file(heads=None, rows=None):
        path = tmp_path / "shops.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(heads if heads is not None else [sheet.COLS[sheet.COL[k]][0] for k in ("shop", "note")])
            writer.writerows(rows if rows is not None else [[" Secret Shop ", " =literal "]])
        return path
    return wb, calls, csv_file, api


@pytest.mark.parametrize("heads", [["unknown"], ["กลุ่ม", "กลุ่ม"], ["#"],
                                    [h for _, h, _, k in sheet.SHOP_COLS if k.startswith("formula")][:1], []])
def test_bad_headers(env, heads):
    _, calls, csv_file, _ = env
    with pytest.raises(SystemExit):
        drive.add_shops("fake", csv_file(heads, [["private"]]))
    assert calls == []


@pytest.mark.parametrize("rows", [[], [["only one"]]])
def test_empty_or_malformed(env, rows):
    _, calls, csv_file, _ = env
    with pytest.raises(SystemExit):
        drive.add_shops("fake", csv_file(rows=rows))
    assert not calls


def test_dry_run_skips_any_input(env, capsys):
    wb, calls, csv_file, _ = env
    wb[sheet.SHOP][f"{sheet.COL['sent']}2"] = 0
    wb[sheet.SHOP][f"{sheet.COL['owner']}3"] = "owner secret"
    drive.add_shops("fake", csv_file())
    output = capsys.readouterr().out
    assert "target_rows=4" in output
    assert "Secret" not in output and "literal" not in output and "owner" not in output
    assert not calls


def test_insufficient_rows(env):
    _, calls, csv_file, _ = env
    with pytest.raises(SystemExit, match="insufficient"):
        drive.add_shops("fake", csv_file(rows=[["a", "b"]] * 6), apply=True)
    assert not calls


def test_apply_raw_exact_ranges(env, capsys):
    _, calls, csv_file, _ = env
    drive.add_shops("fake", csv_file(rows=[[" Secret Shop ", " =literal "], ["Other", ""]]), apply=True)
    assert len(calls) == 2
    payload = json.loads(calls[1][1]["data"])
    assert payload["valueInputOption"] == "RAW"
    expected = [f"'{sheet.SHOP}'!{sheet.COL[c]}{r}" for r in (2, 3) for c in ("shop", "note")]
    assert [d["range"] for d in payload["data"]] == expected
    assert parse_qs(urlsplit(calls[0][0]).query)["ranges"] == expected
    assert payload["data"][1]["values"] == [["=literal"]]
    assert payload["data"][-1]["values"] == [[""]]
    assert "Secret" not in capsys.readouterr().out


@pytest.mark.parametrize("value", ["filled", "=IF(TRUE,\"\",\"\")", 0, False])
def test_race_refuses(env, monkeypatch, value):
    _, calls, csv_file, api = env
    def race(url, **kwargs):
        response = api(url, **kwargs)
        response["valueRanges"][0]["values"] = [[value]]
        return response
    monkeypatch.setattr(drive.g, "api", race)
    with pytest.raises(SystemExit, match="target cells changed"):
        drive.add_shops("fake", csv_file(), apply=True)
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["mismatch", "old_input", "new_error", "extra_input"])
def test_verification(env, monkeypatch, change):
    wb, _, csv_file, api = env
    def corrupt(url, **kwargs):
        response = api(url, **kwargs)
        if "batchUpdate" in url:
            if change == "mismatch":
                wb[sheet.SHOP][f"{sheet.COL['shop']}2"] = "wrong"
            elif change == "old_input":
                wb[sheet.MSG]["D3"] = "changed"
            elif change == "new_error":
                wb[sheet.SHOP][f"{sheet.COL['draft']}2"] = "#REF!"
            else:
                wb[sheet.SHOP][f"{sheet.COL['owner']}4"] = "unexpected"
        return response
    monkeypatch.setattr(drive.g, "api", corrupt)
    with pytest.raises(SystemExit, match="verification FAILED"):
        drive.add_shops("fake", csv_file(), apply=True)


@pytest.mark.parametrize("head", [h for _, h, _, k in sheet.SHOP_COLS if k.startswith("formula")])
def test_every_formula_header_rejected(env, head):
    _, calls, csv_file, _ = env
    with pytest.raises(SystemExit, match="protected"):
        drive.add_shops("fake", csv_file([head], [["text"]]), apply=True)
    assert not calls


def test_incomplete_race_response(env, monkeypatch):
    _, _, csv_file, _ = env
    monkeypatch.setattr(drive.g, "api", lambda *a, **k: {})
    with pytest.raises(SystemExit, match="incomplete"):
        drive.add_shops("fake", csv_file(), apply=True)


def test_existing_error_allowed(env):
    wb, _, csv_file, _ = env
    wb[sheet.SHOP][f"{sheet.COL['draft']}6"] = "#REF!"
    drive.add_shops("fake", csv_file(), apply=True)


def test_cli(env, monkeypatch):
    _, calls, csv_file, _ = env
    monkeypatch.setattr(drive.sys, "argv", ["script", "add-shops", "fake", str(csv_file())])
    drive.main()
    assert not calls
