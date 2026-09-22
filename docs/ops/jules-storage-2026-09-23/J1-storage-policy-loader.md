Context: `config/storage-policy.yaml` (read it first, and ADR summary in its header) tells the org which tier every path on the Mac belongs to: HOT, REBUILD, COLD, NEVER. Nothing reads it yet. Build the loader + classifier.

1. GOAL — the command that must pass: `python -m pytest tests/test_storage_policy.py -q` exits 0, AND `python tools/storage_policy.py check` exits 0 on the real `config/storage-policy.yaml`.
2. FILES you may touch: `tools/storage_policy.py` (new), `tests/test_storage_policy.py` (new). No other file. Do not edit `config/storage-policy.yaml`.
3. FORBIDDEN: scratch/log/patch files anywhere, dependency or lockfile edits (pyyaml is already in requirements.txt), editing any existing test, skipping or loosening a test, network calls, touching anything outside tmp_path in tests.
4. SPEC:
   - `load(path) -> dict` parses the YAML and validates; raise `PolicyError` with a message naming the bad key. Rules: `gauge` has green > yellow > orange > red >= 0 (all numbers); `tiers` has exactly HOT, REBUILD, COLD, NEVER; every REBUILD entry is a mapping with `glob` and `rebuild` (non-empty); every COLD entry has `glob` and `dest`; HOT/NEVER entries are strings.
   - `classify(path, policy, home=None) -> "HOT"|"REBUILD"|"COLD"|"NEVER"|None`. Expand a leading `~` with `home` (default `Path.home()`). `**` matches any depth. Precedence when several tiers match: NEVER > HOT > COLD > REBUILD (NEVER always wins — a REBUILD glob like `**/__pycache__` must never classify a path under `~/Desktop` as REBUILD). Globs containing `<...>` placeholders are skipped by classify (they are templates, not paths).
   - `band(free_gb, policy) -> "green"|"yellow"|"orange"|"red"`: >= green → green; >= yellow → yellow; >= orange → orange; else red.
   - CLI: `python tools/storage_policy.py check [--policy PATH]` prints `ok` and exits 0, or prints the PolicyError and exits 1. `python tools/storage_policy.py classify <path>` prints the tier or `UNCLASSIFIED`.
   - Tests cover: the real config loads; each validation rule rejects a broken tmp copy; NEVER beats REBUILD for `~/Desktop/x/__pycache__`; `**/node_modules` matches at depth 3; placeholder globs are ignored; band() at 25/15/7/2 GB → green/yellow/orange/red; home injection so no test depends on the machine.
5. ENV NOTE: if your VM lacks a package the repo already declares, report it — do not add dependencies.
6. DELIVERABLE: one PR titled `storage: policy loader + classifier (ADR 0030 J1)`; description = what each function does + the exact test command output.
7. FACTS, NOT GUESSES: every claim in the PR body cites the command output or file:line that proves it; anything you could not establish is written as "unknown — not verified", never guessed. State in the PR body which model you are running as, or "unknown" if you cannot tell.
8. No questions needed; proceed.
