"""Offline checks only: never contact winbox."""
import hashlib
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / 'scripts/winbox-install-disk-steward.sh'


def test_pins_match_payloads():
    text = CARD.read_text()
    for prefix, filename in [('TICK', 'disk-steward/disk-steward-tick.ps1'), ('REGISTER', 'disk-steward/register-disk-steward.ps1'), ('PUSH', 'disk-push/disk-push.ps1')]:
        pin = re.search(rf'^{prefix}_SHA256=([0-9a-f]{{64}})$', text, re.M)
        payload = ROOT / 'windows' / filename
        assert pin and pin[1] == hashlib.sha256(payload.read_bytes()).hexdigest()
        assert 'UsEr' not in payload.read_text()


def test_template_headings():
    text = (ROOT / '.claude/skills/ALL_Rules_DiskHygiene/references/new-host-template.md').read_text()
    for heading in ['Machine contract', 'Storage policy', 'Scheduler installation', 'Disk hub verification', 'Host reference', 'Rollback']:
        assert f'## {heading}' in text


def test_task_xml_contract():
    script = (ROOT / 'windows/disk-steward/register-disk-steward.ps1').read_text()
    xml = script.split('$xml = @"\n', 1)[1].split('\n"@', 1)[0]
    task = ET.fromstring(xml)
    ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    for tag, expected in [('Interval', 'PT30M'), ('LogonType', 'InteractiveToken'), ('RunLevel', 'LeastPrivilege'), ('MultipleInstancesPolicy', 'IgnoreNew')]:
        assert task.find(f'.//t:{tag}', ns).text == expected
    assert task.find('.//t:Duration', ns) is None


def test_print_sha_is_local():
    result = subprocess.run(['bash', str(CARD), '--print-sha'], check=True, capture_output=True, text=True)
    assert len(result.stdout.splitlines()) == 3


def test_dedicated_checkout_and_elevation():
    card = CARD.read_text()
    resolver = (ROOT / 'windows/disk-steward/disk-steward-tick.ps1').read_text()
    for source in (card, resolver):
        paths = next(line for line in source.splitlines() if line.startswith('paths ='))
        assert paths.index('repo/Agents-Core') < paths.index('repo/MoonieX-Agents')
    assert "root = next((p for p in paths" in resolver
    assert card.index('fetch origin main') < card.index('sha256sum --check')
    assert 'status --porcelain --untracked-files=all' in card
    assert 'checkout --detach origin/main' in card
    assert 'worktree add --detach' in card
    assert 'git -C \\$existing checkout' not in card
    assert 'py -3 -m venv' in card and 'pip install --quiet pyyaml' in card
    assert 'from tools import disk_steward' in card
    assert card.index('FAIL CLOSED: elevated administrator') < card.index('fetch origin main')
    assert card.index('SHA256 mismatch') < card.index('Copy-Item -LiteralPath "\\$data\\disk-push.ps1"')
    assert 'steward-status.path' in card and 'disk-push.ps1.bak-' in card
    assert 'Copy-Item -LiteralPath $backup -Destination "$dir\\disk-push.ps1" -Force' in card


def test_system_pusher_static_contract():
    source = (ROOT / 'windows/disk-push/disk-push.ps1').read_text()
    assert '$token = (Get-Content -Raw "$dir\\disk-push.token").Trim()' in source
    assert '$candidate.band -is [string]' in source
    assert r"-cmatch '\A[a-z]{1,10}\z'" in source
    assert '$candidate.tick_at -is [string]' in source
    assert '$candidate.tick_at.Length -le 40' in source
    assert '($candidate.actions -is [int] -or $candidate.actions -is [long])' in source
    assert '$candidate.actions -ge 0 -and $candidate.actions -le 1000' in source
    assert 'catch { $steward = $null }' in source
    assert "if ($steward) { $payload['steward'] = $steward }" in source
    assert '$st.steward_tick_at -cne $steward.tick_at' in source
    assert '-and -not $stewardChanged' in source
    assert source.index('Invoke-RestMethod') < source.index('steward_tick_at =')
    assert '$_.Exception.Message' not in source
    assert all('$body' not in line and '$token' not in line for line in source.splitlines() if 'Set-Content $log' in line)


def test_tick_resolver_keeps_dedicated_checkout(tmp_path):
    import sys
    import yaml
    source = (ROOT / 'windows/disk-steward/disk-steward-tick.ps1').read_text()
    resolver = source.split("$resolve = @'\n", 1)[1].split("\n'@", 1)[0]
    dedicated = tmp_path / 'mooniex/repo/Agents-Core'
    other = tmp_path / 'mooniex/repo/MoonieX-Agents'
    for checkout in (dedicated, other):
        for relative in ('tools/disk_steward.py', '.venv/Scripts/python.exe'):
            path = checkout / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
    contract = tmp_path / 'contract.yaml'
    contract.write_text(yaml.safe_dump({'machines': {'winbox': dict(home=str(tmp_path),
        hq=str(tmp_path / 'hq'), scheduler='task_scheduler', drive_leg='rclone_local')}}))
    for seed in (other, dedicated):
        result = subprocess.run([sys.executable, '-c', resolver, str(contract), str(seed)],
                                check=True, capture_output=True, text=True)
        assert Path(result.stdout.strip()) == dedicated


def test_remote_blocks_do_not_abort_on_native_stderr():
    # RUN-20261029-0436-a509: git's progress on stderr became a terminating
    # RemoteException under PowerShell 5.1's Stop preference.
    text = (ROOT / 'scripts/winbox-install-disk-steward.sh').read_text()
    prepare = text[text.index('$paths = @($candidates)') - 400:text.index('Write-Output \\$dedicated')]
    assert "\\$ErrorActionPreference = 'Continue'" in prepare
    assert 'rev-parse --show-toplevel 2>\\$null' in prepare
    # review of #550: Continue must not let a failed cd reach the import check
    assert 'Push-Location \\$dedicated -ErrorAction Stop' in prepare
    deploy = text[text.index('Pusher backup'):text.index('-DryRun 2>&1')]
    assert "\\$ErrorActionPreference = 'Continue'" in deploy
    assert deploy.index("'Continue'") < deploy.index('register-disk-steward.ps1')
