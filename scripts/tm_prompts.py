#!/usr/bin/env python3
"""TraderMindset prompt registry loader (externalized, versioned prompts).

Single source of truth for the generator (scripts/trader_mindset_batch.py),
the reflective evolver (scripts/tm_prompt_evolve.py) and the eval gate
(scripts/tm_prompt_eval.py). Prompts used to live as inline constants in the
batch script; they now live as reviewable, diff-able, versioned files under
prompts/trader-mindset/ so the learning loop can propose v(N+1) drafts and an
A/B gate can compare them before activation.

File layout
-----------
  prompts/trader-mindset/registry.json   {active:{caption,poster}, history:[...]}
  prompts/trader-mindset/caption-v1.md   sections: system, user
  prompts/trader-mindset/poster-v1.md    sections: preamble, art_styles, scenes,
                                          template, lessons_guidance

Prompt-file format
------------------
Markdown for humans, with each machine-consumed section written as a fenced
``text`` block immediately under a ``## <name>`` header::

    ## system

    ```text
    <verbatim prompt text, may contain {{slots}}>
    ```

The fenced block makes whitespace explicit (no trailing-space drift) and keeps
the file readable in a PR. Slots are ``{{name}}`` and filled by render().

No network, no API key, no Pillow — safe to import under --dry.
"""
from __future__ import annotations

import json
import os
import re

PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "prompts", "trader-mindset")
REGISTRY_PATH = os.path.join(PROMPTS_DIR, "registry.json")

KINDS = ("caption", "poster")

# A "## name" header followed by the first ```lang fenced block. The capture is
# verbatim between the fences (DOTALL), minus the newline hugging each fence, so
# section content is exact and not subject to trailing-whitespace stripping.
_SECTION_RE = re.compile(
    r"^##[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\r?\n+```[A-Za-z]*\r?\n(.*?)\r?\n```",
    re.M | re.S)

_PROMPT_CACHE: dict[tuple[str, str], dict[str, str]] = {}
_REGISTRY_CACHE: dict | None = None


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
def load_registry(force: bool = False) -> dict:
    """Read prompts/trader-mindset/registry.json (cached)."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None or force:
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            _REGISTRY_CACHE = json.load(f)
    return _REGISTRY_CACHE


def active_version(kind: str) -> str:
    """Currently-activated version for a kind, e.g. 'v1'."""
    _check_kind(kind)
    return load_registry()["active"][kind]


# --------------------------------------------------------------------------- #
# Prompt files
# --------------------------------------------------------------------------- #
def prompt_path(kind: str, version: str) -> str:
    """Absolute path of a prompt file, e.g. .../caption-v1.md."""
    _check_kind(kind)
    return os.path.join(PROMPTS_DIR, f"{kind}-{version}.md")


def parse_prompt_md(text: str) -> dict[str, str]:
    """Parse a prompt markdown file into {section_name: verbatim_text}."""
    return {m.group(1): m.group(2) for m in _SECTION_RE.finditer(text)}


def load_prompt(kind: str, version: str | None = None) -> dict[str, str]:
    """Load+parse a prompt file. version=None -> registry's active version.

    Pass an explicit version (e.g. 'v2') to load a DRAFT that is not active —
    this is how the eval gate A/B-compares a proposed prompt against the live
    one without touching the registry.
    """
    _check_kind(kind)
    version = version or active_version(kind)
    key = (kind, version)
    if key not in _PROMPT_CACHE:
        with open(prompt_path(kind, version), encoding="utf-8") as f:
            _PROMPT_CACHE[key] = parse_prompt_md(f.read())
    return _PROMPT_CACHE[key]


def render(template: str, **slots: str) -> str:
    """Fill ``{{name}}`` slots. Only the named slots are touched (no .format
    brace pitfalls with literal { } in prompt text)."""
    out = template
    for name, value in slots.items():
        out = out.replace("{{" + name + "}}", value)
    return out


def as_list(section_text: str) -> list[str]:
    """A list-style section (one item per line) -> [items] (blank lines dropped)."""
    return [ln for ln in section_text.splitlines() if ln.strip()]


# --------------------------------------------------------------------------- #
# Versioning helpers (used by the evolver)
# --------------------------------------------------------------------------- #
def list_versions(kind: str) -> list[int]:
    """All on-disk version numbers for a kind, ascending (e.g. [1, 2])."""
    _check_kind(kind)
    out = []
    if os.path.isdir(PROMPTS_DIR):
        for name in os.listdir(PROMPTS_DIR):
            m = re.fullmatch(rf"{re.escape(kind)}-v(\d+)\.md", name)
            if m:
                out.append(int(m.group(1)))
    return sorted(out)


def next_version(kind: str) -> str:
    """Next draft version string, e.g. 'v2' when v1 is the latest on disk."""
    vs = list_versions(kind)
    return f"v{(max(vs) + 1) if vs else 1}"


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown prompt kind {kind!r}; expected one of {KINDS}")
