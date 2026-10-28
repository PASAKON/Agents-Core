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
    for prefix, filename in [('TICK', 'disk-steward-tick.ps1'), ('REGISTER', 'register-disk-steward.ps1')]:
        pin = re.search(rf'^{prefix}_SHA256=([0-9a-f]{{64}})$', text, re.M)
        payload = ROOT / 'windows/disk-steward' / filename
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
    assert len(result.stdout.splitlines()) == 2
