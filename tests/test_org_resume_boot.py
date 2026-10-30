"""Boot regressions: isolated commands, no host services or credentials."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "scripts/hub").mkdir(parents=True)
        (self.root / "state/restart").mkdir(parents=True)
        (self.root / "state/restart/pending-contabo.json").write_text("{}")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        HOME=str(self.root), PYTHONPATH=str(self.root),
                        ORG_DB_URL="unreachable-test-sentinel", TAILNET_IP="192.0.2.1")

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/bash\n" + body)
        path.chmod(0o755)

    def run_script(self, name, transform=lambda s: s):
        target = self.root / "scripts" / name
        target.write_text(transform((ROOT / "scripts" / name).read_text()))
        return subprocess.run(["bash", str(target)], cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=10)

    def resume_setup(self):
        # Functional stubs never dump arguments or environment values.
        self.stub("tmux", 'printf "argc=%s\\n" "$#"\n')
        self.stub("cat", "echo '0::/org-tmux.scope'\n")
        (self.root / "scripts/org-tmux-adopt.sh").write_text("exit 0\n")
        self.stub("sleep", 'printf "argc=%s\\n" "$#" >> sleeps\n')

    def test_hub_failure_ignores_snapshot_and_silences_error(self):
        sqlite3.connect(self.root / "state/tasks.snapshot.db").close()
        (self.root / "psycopg.py").write_text(
            'def connect(url, connect_timeout):\n'
            '    assert connect_timeout == 3\n'
            '    raise RuntimeError(url)\n')
        shutil.copy(ROOT / "scripts/hub/org-python.sh", self.root / "scripts/hub")
        # Expire the production loop immediately, while executing its actual probe.
        result = self.run_script("org-resume.sh", lambda s: s.replace(
            "deadline=$((SECONDS + 600))", "deadline=$SECONDS"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Hub unavailable after 10 minutes", result.stdout)
        self.assertNotIn(self.env["ORG_DB_URL"], result.stdout + result.stderr)
        self.assertNotIn("RuntimeError", result.stdout + result.stderr)

    def retry_case(self, succeeds=False, report_status=0):
        self.resume_setup()
        wrapper = self.root / "scripts/hub/org-python.sh"
        wrapper.write_text('''if [[ "$1" == -c ]]; then exit 0; fi
if [[ "$4" == resume ]]; then
  printf 'argc=%s\\n' "$#" >> resumes
'''+ ("  [[ $(wc -l < resumes) -ge 2 ]]\n" if succeeds else "  exit 7\n") + '''else
  printf 'argc=%s\\n' "$#" >> reports
  exit ''' + str(report_status) + '\nfi\n')
        result = self.run_script("org-resume.sh")
        self.assertEqual(len((self.root / "resumes").read_text().splitlines()),
                         2 if succeeds else 4)
        self.assertEqual(len((self.root / "sleeps").read_text().splitlines()),
                         1 if succeeds else 3)
        self.assertEqual((self.root / "reports").read_text(), "argc=5\n")
        return result

    def test_three_retries_then_give_up_and_report_once(self):
        self.assertEqual(self.retry_case().returncode, 7)

    def test_retry_success_clears_failure(self):
        self.assertEqual(self.retry_case(succeeds=True).returncode, 0)

    def test_report_failure_fails_service(self):
        self.assertEqual(self.retry_case(succeeds=True, report_status=9).returncode, 9)

    def tailnet_setup(self, listening=False, recovers=True):
        self.stub("ip", "echo '1: tailscale0 inet 192.0.2.1/32 scope global'\n")
        self.stub("ss", ("true" if listening else "test -f restarted") +
                  " && echo 'LISTEN 0 128 192.0.2.1:5432 0.0.0.0:*'\nexit 0\n")
        self.stub("docker", '[[ "$1" == restart && "$2" == org-postgres && "$#" == 2 ]] || exit 99\n'
                  'printf "argc=%s\\n" "$#" >> docker-calls\n' +
                  ("touch restarted\n" if recovers else "true\n"))
        self.stub("sleep", 'printf "argc=%s\\n" "$#" >> sleeps\n')

    def test_existing_listener_not_restarted(self):
        self.tailnet_setup(listening=True)
        self.assertEqual(self.run_script("org-postgres-tailnet.sh").returncode, 0)
        self.assertFalse((self.root / "docker-calls").exists())

    def test_missing_listener_restarted_once(self):
        self.tailnet_setup()
        self.assertEqual(self.run_script("org-postgres-tailnet.sh").returncode, 0)
        self.assertEqual((self.root / "docker-calls").read_text(), "argc=2\n")

    def test_unrecovered_listener_fails(self):
        self.tailnet_setup(recovers=False)
        self.assertEqual(self.run_script("org-postgres-tailnet.sh").returncode, 1)
        self.assertEqual((self.root / "docker-calls").read_text(), "argc=2\n")

    def test_missing_address_never_restarts(self):
        self.tailnet_setup()
        self.stub("ip", "exit 0\n")
        result = self.run_script("org-postgres-tailnet.sh", lambda s: s.replace(
            "deadline=$((SECONDS + 300))", "deadline=$SECONDS"))
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / "docker-calls").exists())

    def test_shell_syntax(self):
        for name in ("org-resume.sh", "org-postgres-tailnet.sh",
                     "hub/org-python.sh", "hub/with-org-db-env.sh"):
            with self.subTest(script=name):
                subprocess.run(["bash", "-n", str(ROOT / "scripts" / name)], check=True)

    @unittest.skipUnless(shutil.which("systemd-analyze"), "systemd-analyze unavailable")
    def test_units_verify(self):
        # Isolate dependency resolution from whatever services this host has.
        units = self.root / "units"
        units.mkdir()
        for name in ("org-resume.service", "org-postgres-tailnet.service"):
            shutil.copy(ROOT / "deploy/systemd" / name, units)
        for name in ("docker.service", "tailscaled.service"):
            (units / name).write_text("[Service]\nExecStart=/bin/true\n")
        subprocess.run(["systemd-analyze", "verify", str(units / "org-resume.service"),
                        str(units / "org-postgres-tailnet.service")], check=True,
                       env=dict(os.environ, SYSTEMD_UNIT_PATH=f"{units}:/usr/lib/systemd/system"),
                       capture_output=True, text=True)
