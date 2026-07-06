#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: scripts/ci/verify_build_baseline.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for scripts/ci/verify_build_baseline.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Reproducible-build baseline verifier (GitHub issue #41).

Scans tracked files only (`git ls-files`) and fails the build if any of the
following invariants regress:

  * Python runtime Dockerfiles pin Python 3.13 (no 3.11/3.12).
  * Python runtime Dockerfiles use `uv`, never `pip install`.
  * Python runtime Dockerfiles never reference `requirements.txt`.
  * Every tracked runtime Dockerfile declares a fixed numeric final `USER`.
  * `docker-compose.yml` and `docker-compose.dev.yml` pass `docker compose config`.
  * No tracked compose file floats a `:latest` image tag.
  * No tracked Dockerfile/CI file declares a Node baseline other than 22.

Run: `uv run python scripts/ci/verify_build_baseline.py`
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

NUMERIC_USER_RE = re.compile(r'^\d+(:\d+)?$')
FROM_RE = re.compile(r'^FROM\s+(\S+)', re.MULTILINE)
USER_RE = re.compile(r'^USER\s+(\S+)', re.MULTILINE)
PYTHON_STAGE_RE = re.compile(r'^FROM\s+python[@:]', re.MULTILINE)
FORBIDDEN_PY_VERSION_RE = re.compile(r'python:3\.(?:9|10|11|12)\b')
PIP_INSTALL_RE = re.compile(r'\bpip\s+install\b')
REQUIREMENTS_TXT_RE = re.compile(r'requirements\.txt')
COMPOSE_LATEST_IMAGE_RE = re.compile(r'^\s*image:\s*\S*:latest\s*$', re.MULTILINE)
FORBIDDEN_NODE_VERSION_RE = re.compile(r'node:(?:1[0-9]|20|21|23|24|25|26)\b')
NODE_VERSION_ENV_RE = re.compile(r'NODE_VERSION:\s*["\']?(\d+)')


class Failure(list):
    def add(self, path: str, message: str) -> None:
        self.append(f'{path}: {message}')


def tracked_files() -> list[str]:
    out = subprocess.run(
        ['git', 'ls-files'],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def tracked_dockerfiles(files: list[str]) -> list[str]:
    return [f for f in files if Path(f).name == 'Dockerfile']


def last_stage(text: str) -> str:
    """Return the source text of the final build stage (after the last FROM)."""
    matches = list(FROM_RE.finditer(text))
    if not matches:
        return text
    return text[matches[-1].start() :]


def check_python_dockerfiles(dockerfiles: list[str], failures: Failure) -> None:
    for rel_path in dockerfiles:
        text = (REPO_ROOT / rel_path).read_text()
        if not PYTHON_STAGE_RE.search(text):
            continue  # Not a Python runtime Dockerfile (Node/Java/other).

        if FORBIDDEN_PY_VERSION_RE.search(text):
            failures.add(rel_path, 'pins a Python version older than 3.13')

        non_comment_lines = '\n'.join(
            line for line in text.splitlines() if not line.strip().startswith('#')
        )
        if PIP_INSTALL_RE.search(non_comment_lines):
            failures.add(rel_path, 'uses `pip install` (uv is the only allowed installer)')

        if REQUIREMENTS_TXT_RE.search(non_comment_lines):
            failures.add(rel_path, 'references requirements.txt (lock-file-only builds required)')


def check_numeric_user(dockerfiles: list[str], failures: Failure) -> None:
    for rel_path in dockerfiles:
        text = (REPO_ROOT / rel_path).read_text()
        final_stage = last_stage(text)
        user_matches = USER_RE.findall(final_stage)
        if not user_matches:
            failures.add(rel_path, 'final build stage declares no USER (defaults to root)')
            continue
        final_user = user_matches[-1]
        if not NUMERIC_USER_RE.match(final_user):
            failures.add(
                rel_path,
                f'final USER "{final_user}" is not a fixed numeric UID[:GID] (e.g. 10001:10001)',
            )


def check_compose_config(compose_files: list[str], failures: Failure) -> None:
    for rel_path in compose_files:
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            continue
        try:
            result = subprocess.run(
                ['docker', 'compose', '-f', str(full_path), 'config'],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            failures.add(rel_path, 'docker compose not available to validate (install Docker)')
            continue
        if result.returncode != 0:
            failures.add(rel_path, f'`docker compose config` failed:\n{result.stderr.strip()}')


def check_no_floating_latest(compose_files: list[str], failures: Failure) -> None:
    for rel_path in compose_files:
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            continue
        text = full_path.read_text()
        if COMPOSE_LATEST_IMAGE_RE.search(text):
            failures.add(rel_path, 'floating `:latest` image tag found')


def check_node_baseline(files: list[str], failures: Failure) -> None:
    node_relevant_suffixes = ('Dockerfile', '.yml', '.yaml')
    for rel_path in files:
        if not rel_path.endswith(node_relevant_suffixes):
            continue
        if 'node_modules/' in rel_path:
            continue
        full_path = REPO_ROOT / rel_path
        if not full_path.is_file():
            continue
        text = full_path.read_text(errors='ignore')
        if FORBIDDEN_NODE_VERSION_RE.search(text):
            failures.add(rel_path, 'declares a Node baseline other than 22')
        for match in NODE_VERSION_ENV_RE.finditer(text):
            if match.group(1) != '22':
                failures.add(rel_path, f'NODE_VERSION env declares {match.group(1)}, expected 22')


def main() -> int:
    files = tracked_files()
    dockerfiles = tracked_dockerfiles(files)
    compose_files = [
        f
        for f in files
        if Path(f).name in {'docker-compose.yml', 'docker-compose.dev.yml'}
        or re.search(r'(^|/)compose.*\.ya?ml$', f)
    ]

    failures = Failure()
    check_python_dockerfiles(dockerfiles, failures)
    check_numeric_user(dockerfiles, failures)
    check_no_floating_latest(compose_files, failures)
    check_node_baseline(files, failures)
    check_compose_config(compose_files, failures)

    if failures:
        print('Reproducible-build baseline verification FAILED:\n', file=sys.stderr)
        for failure in failures:
            print(f'  - {failure}', file=sys.stderr)
        print(f'\n{len(failures)} invariant violation(s).', file=sys.stderr)
        return 1

    print(
        f'Reproducible-build baseline OK: {len(dockerfiles)} Dockerfile(s), '
        f'{len(compose_files)} compose file(s) checked.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
