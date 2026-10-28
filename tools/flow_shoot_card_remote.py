"""Pinned Windows worker for flow_shoot_card; bootstrap uses only stdlib."""
import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

CDP = 'http://127.0.0.1:9226'


def own_tab(project):
    """Regex for this project's pages only: /project/<id>, its /edit/ routes, a query string."""
    ident = re.escape(project.rsplit('/project/', 1)[1])
    return r'https://flow\.google\.com/(?:[^?#]*/)?project/' + ident + r'(?:[/?#]|$)'


def ensure_tab(project):
    """Open the project's tab when none is open: navigation only, no credits. Never closes a tab."""
    def mine():
        tabs = json.load(urllib.request.urlopen(CDP + '/json/list', timeout=8))
        return [t for t in tabs if t.get('type') == 'page' and re.match(own_tab(project), t['url'])]
    if mine():
        return
    urllib.request.urlopen(urllib.request.Request(CDP + '/json/new?' + project, method='PUT'), timeout=15).read()
    for _ in range(15):
        time.sleep(3)
        if mine():
            return
    raise RuntimeError('own project tab did not open')


def other_flow_job():
    """A flow_shoot run started the old way holds no card lock; the card must not share 9226 with it."""
    out = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                          "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                          "ForEach-Object { $_.CommandLine }"],
                         capture_output=True, text=True, timeout=60).stdout
    return any('flow_shoot' in line and 'flow_shoot_card_remote' not in line for line in out.splitlines())


def shoot():
    root = Path(sys.argv[2])
    sys.path.insert(0, str(root))
    os.chdir(root)
    os.environ['FLOW_CDP'] = 'http://127.0.0.1:9226'
    from tools import flow_shoot
    project = (root / 'project.txt').read_text()

    def attach(self):
        flow_shoot.flow_cdp.enforce_platform()
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        pages = [p for c in self._browser.contexts for p in c.pages if re.match(own_tab(project), p.url)]
        if not pages:
            raise RuntimeError('own project tab missing')
        # The bare project tab first, the one the balance reader picks; an /edit/ tab otherwise.
        self.page = sorted(pages, key=lambda p: '/edit/' in p.url)[0]
        try:
            self.page.bring_to_front()
        except Exception:
            pass
        self._project_url = project
        self.page.on('response', self._on_response)
        return self.page

    flow_shoot.FlowBrowser.attach = attach
    sys.exit(flow_shoot.main(sys.argv[3:]))


def serve():
    lock = None
    def dispatch(q):
        nonlocal lock
        verb = q['verb']
        if verb == 'lock':
            import msvcrt
            root = Path(r'C:\mooniex\flowcard')
            root.mkdir(parents=True, exist_ok=True)
            lock = (root / 'exclusive.lock').open('a+b')
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                lock.close()
                lock = None
                return False
            if other_flow_job():
                lock.close()
                lock = None
                return False
            return True
        if lock is None:
            raise RuntimeError('lock required')
        if verb == 'balance':
            # Execute the pinned stdlib reader from stdin, on this project's own tab only.
            # No bundle or input file is pushed before this gate.
            ensure_tab(q['project'])
            source = q['source']
            start = source.index('mine = ')
            end = source.index('print("my tabs"', start)
            source = source[:start] + (
                'mine = [t for t in tabs if t["type"] == "page" and re.match('
                + repr(own_tab(q['project'])) + ', t["url"])]\n'
                'mine.sort(key=lambda t: "/edit/" in t["url"])\n'
                'assert mine, "own project tab missing"\n'
            ) + source[end:]
            for attempt in range(3):
                result = subprocess.run([sys.executable, '-u', '-c', source, q['project'], '--reload'],
                                        capture_output=True, text=True, encoding='utf-8', timeout=90)
                match = re.search(r'^BALANCE (\d+)$', result.stdout, re.M)
                if result.returncode == 0 and match:
                    return int(match[1])
                if attempt < 2:
                    time.sleep(5)
            return None
        folder = Path(q['folder'])
        if verb == 'put':
            path = folder / q['name']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(q['data']))
            return hashlib.sha256(path.read_bytes()).hexdigest()
        if verb == 'run':
            # Child waits for a gate; PID is durable before it may attach or spend.
            gate = folder / 'go'
            boot = ('import os,time,runpy,sys; from pathlib import Path; '
                    'p=Path(sys.argv[1]); '
                    'exec("while not (p / \'go\').exists(): time.sleep(.05)"); '
                    'sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name="__main__")')
            argv = q['argv']
            child = subprocess.Popen([argv[0], '-u', '-c', boot, str(folder),
                                      str(folder / 'tools/flow_shoot_card_remote.py'),
                                      'shoot', str(folder)] + argv[3:],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding='utf-8', errors='replace',
                                     env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            (folder / 'pid').write_text(str(child.pid))
            gate.touch()
            with (folder / 'charges.tsv').open('w') as charges:
                for line in child.stdout:
                    match = re.search(r'shot (\d+): submitted .*est (\d+) credits', line)
                    if match:
                        charges.write(match[1] + '\t' + match[2] + '\n')
                        charges.flush()
                    # If Contabo dies, drain stdout and retain the lock until child ends.
                    try:
                        print(json.dumps({'output': line.rstrip()}), flush=True)
                    except (BrokenPipeError, OSError):
                        pass
            return child.wait()
        if verb == 'list':
            files = {'ledger.tsv': folder / 'ledger.tsv'}
            files.update({'out/' + p.name: p for p in (folder / 'out').glob('*') if p.is_file()})
            result = []
            for name, path in files.items():
                sha = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        sha.update(chunk)
                result.append(dict(name=name, size=path.stat().st_size, sha256=sha.hexdigest()))
            return result
        if verb == 'get':
            name = q['name']
            if name != 'ledger.tsv' and not re.fullmatch(r'out/[\w.-]+', name):
                raise RuntimeError('unsafe output filename')
            if Path(name).name in ('.', '..'):
                raise RuntimeError('unsafe output filename')
            return base64.b64encode((folder / name).read_bytes()).decode()
        if verb == 'estimate':
            return sum(float(line.split('\t')[1]) for line in (folder / 'charges.tsv').read_text().splitlines())
        raise RuntimeError('unknown verb')

    try:
        for line in sys.stdin:
            try:
                answer = {'result': dispatch(json.loads(line))}
            except Exception as exc:
                answer = {'error': str(exc)}
            print(json.dumps(answer), flush=True)
    finally:
        if lock:
            lock.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'shoot':
        shoot()
    else:
        serve()
