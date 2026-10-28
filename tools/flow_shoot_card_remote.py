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


def shoot():
    root = Path(sys.argv[2])
    sys.path.insert(0, str(root))
    os.chdir(root)
    os.environ['FLOW_CDP'] = 'http://127.0.0.1:9226'
    from tools import flow_shoot
    project = (root / 'project.txt').read_text()

    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        pages = [p for c in self._browser.contexts for p in c.pages
                 if p.url == project or p.url.startswith(project + '/edit/')]
        if len(pages) != 1:
            raise RuntimeError('own project tab missing or ambiguous')
        self.page = pages[0]
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
                return True
            except OSError:
                lock.close()
                lock = None
                return False
        if lock is None:
            raise RuntimeError('lock required')
        if verb == 'balance':
            # Execute the pinned stdlib reader from stdin, with exact tab selection.
            # No bundle or input file is pushed before this gate.
            source = q['source']
            start = source.index('mine = ')
            end = source.index('print("my tabs"', start)
            source = source[:start] + (
                'project = ' + repr(q['project']) + '\n'
                'mine = [t for t in tabs if t["type"] == "page" and '
                '(t["url"] == project or t["url"].startswith(project + "/edit/"))]\n'
                'assert len(mine) == 1, "own project missing or ambiguous"\n'
            ) + source[end:]
            result = subprocess.run([sys.executable, '-u', '-c', source, q['project'], '--reload'],
                                    capture_output=True, text=True, encoding='utf-8', timeout=90)
            match = re.search(r'^BALANCE (\d+)$', result.stdout, re.M)
            return int(match[1]) if result.returncode == 0 and match else None
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
        if verb == 'pull':
            files = {'ledger.tsv': folder / 'ledger.tsv'}
            files.update({p.name: p for p in (folder / 'out').glob('*') if p.is_file()})
            return {n: base64.b64encode(p.read_bytes()).decode() for n, p in files.items()}
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
