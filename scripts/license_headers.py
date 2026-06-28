#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: scripts/license_headers.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Implements AstraDesk functionality for scripts/license_headers.py.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

"""Deterministic AstraDesk license-header normalization and verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

SPDX = 'SPDX-License-Identifier: GPL-2.0-only'
PROJECT = 'Project: AstraDesk'
APACHE_NAME = 'Apache'
APACHE_SPDX = APACHE_NAME + '-2.0'
APACHE_LICENSE = APACHE_NAME + ' License'
APACHE_PATTERN = re.compile(
    APACHE_SPDX.replace('.', r'\.')
    + '|'
    + APACHE_LICENSE
    + r'(?:,? Version)? 2\.0|www\.'
    + APACHE_NAME.lower()
    + r'\.org/licenses/LICENSE-2\.0',
    re.IGNORECASE,
)

HASH_EXTENSIONS = {
    '.env',
    '.ini',
    '.pp',
    '.properties',
    '.py',
    '.rego',
    '.sh',
    '.sls',
    '.tf',
    '.tfvars',
    '.toml',
    '.yaml',
    '.yml',
}
SLASH_EXTENSIONS = {
    '.c',
    '.cc',
    '.cpp',
    '.go',
    '.h',
    '.hpp',
    '.java',
    '.js',
    '.kts',
    '.proto',
    '.rs',
    '.ts',
    '.tsx',
}
HTML_EXTENSIONS = {'.html', '.md', '.svg', '.xml'}
CSS_EXTENSIONS = {'.css', '.less', '.scss'}
SQL_EXTENSIONS = {'.sql'}
STRICT_JSON_NAMES = {'.eslintrc.json', '.prettierrc', 'package.json'}
SPECIAL_HASH_NAMES = {
    '.dockerignore',
    '.env.example',
    '.gitignore',
    'Dockerfile',
    'Makefile',
}
SPECIAL_SLASH_NAMES = {'Jenkinsfile', 'tsconfig.json'}
PACKAGE_MANIFESTS = {'services/admin-portal/package.json'}

EXCLUDED_PARTS = {
    '.docker-config',
    '.gradle',
    '.next',
    '.venv',
    '__pycache__',
    '_gen',
    'build',
    'coverage',
    'dist',
    'node_modules',
    'target',
    'vendor',
}
EXCLUDED_SUFFIXES = {
    '.bin',
    '.ico',
    '.jar',
    '.lock',
    '.png',
    '.pyc',
    '.tsbuildinfo',
}
EXCLUDED_NAMES = {
    '.python-version',
    'LICENSE',
    'gradle-wrapper.properties',
    'gradlew',
    'gradlew.bat',
    'next-env.d.ts',
    'package-lock.json',
    'uv.lock',
}


def repository_root() -> Path:
    """Return the Git repository root containing this script."""
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def tracked_paths(root: Path) -> list[PurePosixPath]:
    """Return tracked and non-ignored untracked repository paths in deterministic order."""
    result = subprocess.run(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(PurePosixPath(raw.decode()) for raw in result.stdout.split(b'\0') if raw)


def is_excluded(path: PurePosixPath) -> bool:
    """Return whether a tracked path is generated, third-party, binary, or dependency state."""
    if set(path.parts) & EXCLUDED_PARTS:
        return True
    if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES:
        return True
    if path.name == '.gitkeep':
        return True
    if '.gen.' in path.name or path.name.endswith(('_pb2.py', '_pb2_grpc.py')):
        return True
    return False


def comment_style(path: PurePosixPath) -> str | None:
    """Return the canonical header style for a project-owned path."""
    if is_excluded(path):
        return None
    if path.name in SPECIAL_HASH_NAMES or path.suffix in HASH_EXTENSIONS:
        return 'hash'
    if path.name in SPECIAL_SLASH_NAMES or path.suffix in SLASH_EXTENSIONS:
        return 'slash'
    if path.suffix in HTML_EXTENSIONS:
        return 'html'
    if path.suffix in CSS_EXTENSIONS:
        return 'css'
    if path.suffix in SQL_EXTENSIONS:
        return 'sql'
    return None


def description_for(path: PurePosixPath) -> str:
    """Build a concise deterministic description for a project-owned file."""
    path_text = path.as_posix()
    if 'test' in path.parts or path.name.startswith('test_') or '.test.' in path.name:
        return 'Verifies AstraDesk behavior for the associated component.'
    if path.name == 'Dockerfile':
        return 'Builds the AstraDesk container image for the associated component.'
    if '.github' in path.parts or path.name in {'Jenkinsfile', '.gitlab-ci.yml'}:
        return 'Defines continuous integration and delivery automation for AstraDesk.'
    if path.suffix == '.md' or path.name.startswith('README'):
        return 'Documents AstraDesk architecture, operation, or component behavior.'
    if path.suffix in {'.yaml', '.yml', '.toml', '.tf', '.tfvars', '.ini', '.properties'}:
        return 'Configures the associated AstraDesk component or deployment.'
    if path.name in {'Makefile'} or path.suffix in {'.sh', '.sls', '.pp'}:
        return 'Automates AstraDesk development, deployment, or operational tasks.'
    if path.name == '__init__.py':
        return 'Declares the associated AstraDesk Python package.'
    if path.suffix in {'.svg', '.css'}:
        return 'Defines AstraDesk visual assets or presentation behavior.'
    if path.suffix in {'.proto', '.sql'}:
        return 'Defines an AstraDesk service or persistence interface.'
    return f'Implements AstraDesk functionality for {path_text}.'


def _prefixed_header(prefix: str, path: PurePosixPath, description: str) -> str:
    lines = [
        f'{prefix} {SPDX}',
        f'{prefix} {PROJECT}',
        f'{prefix} File: {path.as_posix()}',
        f'{prefix} Website: https://www.astradesk.dev',
        f'{prefix} Repository: https://github.com/SSobol77/astradesk',
        prefix,
        f'{prefix} Description: {description}',
        prefix,
        f'{prefix} Copyright (c) 2026 Siergej Sobolewski',
        prefix,
        f'{prefix} This file is part of AstraDesk.',
        prefix,
        f'{prefix} AstraDesk is licensed under the GNU General Public License version 2 only.',
        f'{prefix} See the LICENSE file in the project root for the full license text.',
    ]
    return '\n'.join(lines)


def canonical_header(path: PurePosixPath, style: str) -> str:
    """Return the canonical AstraDesk header for a path and comment grammar."""
    description = description_for(path)
    if style == 'hash':
        return _prefixed_header('#', path, description)
    if style == 'slash':
        return _prefixed_header('//', path, description)
    if style == 'sql':
        return _prefixed_header('--', path, description)
    if style == 'html':
        return '\n'.join(
            [
                '<!--',
                SPDX,
                PROJECT,
                f'File: {path.as_posix()}',
                'Website: https://www.astradesk.dev',
                'Repository: https://github.com/SSobol77/astradesk',
                '',
                f'Description: {description}',
                '',
                'Copyright (c) 2026 Siergej Sobolewski',
                'This file is part of AstraDesk.',
                '',
                'AstraDesk is licensed under the GNU General Public License version 2 only.',
                'See the LICENSE file in the project root for the full license text.',
                '-->',
            ]
        )
    if style == 'css':
        body = [
            SPDX,
            PROJECT,
            f'File: {path.as_posix()}',
            'Website: https://www.astradesk.dev',
            'Repository: https://github.com/SSobol77/astradesk',
            '',
            f'Description: {description}',
            '',
            'Copyright (c) 2026 Siergej Sobolewski',
            'This file is part of AstraDesk.',
            '',
            'AstraDesk is licensed under the GNU General Public License version 2 only.',
            'See the LICENSE file in the project root for the full license text.',
        ]
        return '/*\n' + '\n'.join(f' * {line}' if line else ' *' for line in body) + '\n */'
    raise ValueError(f'Unsupported comment style: {style}')


def _split_preamble(text: str) -> tuple[str, str]:
    """Preserve required interpreter, encoding, XML, and HTML declaration lines."""
    lines = text.splitlines(keepends=True)
    index = 0
    if index < len(lines) and lines[index].startswith('#!'):
        index += 1
        if index < len(lines) and re.match(r'^#.*coding[:=]', lines[index]):
            index += 1
    elif index < len(lines) and re.match(r'^#.*coding[:=]', lines[index]):
        index += 1
    elif index < len(lines) and lines[index].lstrip().startswith('<?xml'):
        index += 1
    elif index < len(lines) and re.match(r'(?i)^\s*<!DOCTYPE\s+html', lines[index]):
        index += 1
    return ''.join(lines[:index]), ''.join(lines[index:])


def _strip_html_header(body: str) -> str:
    while body.lstrip().startswith('<!--'):
        leading = len(body) - len(body.lstrip())
        end = body.find('-->', leading)
        if end < 0:
            break
        block = body[leading : end + 3]
        metadata = block.strip('<!-> \n').split(':', 1)[0].strip()
        if SPDX.split(':', 1)[0] not in block and metadata not in {
            'Author',
            'Copyright (c) 2026 Siergej Sobolewski',
            'Description',
            'File',
            'Project',
            'Repository',
            'Since',
            'Website',
        }:
            break
        body = body[end + 3 :].lstrip('\n')
    first, separator, rest = body.partition('\n')
    if 'SPDX-License-Identifier:' in first:
        body = rest if separator else ''
    return body.lstrip('\n')


def strip_existing_header(body: str, style: str) -> str:
    """Remove one or more leading AstraDesk header forms without touching third-party notices."""
    body = body.lstrip('\n')
    if style == 'html':
        return _strip_html_header(body)
    if style in {'css', 'slash'} and body.startswith('/*'):
        end = body.find('*/')
        if end >= 0 and 'SPDX-License-Identifier:' in body[: end + 2]:
            return body[end + 2 :].lstrip('\n')
    prefix = {'hash': '#', 'slash': '//', 'sql': '--', 'css': None}.get(style)
    if prefix and body.startswith(prefix):
        lines = body.splitlines(keepends=True)
        index = 0
        while index < len(lines) and lines[index].lstrip().startswith(prefix):
            index += 1
        leading_comments = ''.join(lines[:index])
        if 'SPDX-License-Identifier:' in leading_comments or (
            'Project: AstraDesk' in leading_comments
            and any(marker in leading_comments for marker in ('Author:', 'File:', 'Since:'))
        ):
            return ''.join(lines[index:]).lstrip('\n')
    return body


def strip_legacy_metadata(body: str, style: str) -> str:
    """Remove obsolete AstraDesk metadata adjacent to the canonical header."""
    if style == 'html':
        prefix = body[:2000]
        for match in reversed(list(re.finditer(r'<!--.*?-->', prefix, flags=re.DOTALL))):
            block = match.group(0)
            if 'SPDX-License-Identifier:' in block or re.match(
                r'<!--\s*(?:Author|Description|File|Project|Since):', block
            ):
                body = body[: match.start()] + body[match.end() :]
        return re.sub(r'\n{3,}', '\n\n', body).lstrip('\n')

    if style != 'hash':
        return body
    docstring_match = re.match(r'(?P<quote>"""|\'\'\')(?P<content>.*?)(?P=quote)', body, re.DOTALL)
    if docstring_match is None:
        return body
    content = docstring_match.group('content')
    if 'Project:' not in content and 'File:' not in content:
        return body
    retained: list[str] = []
    for line in content.splitlines():
        metadata = re.match(r'^\s*(?:Author|File|Package|Pakage|Project|Since):(?:\s+.*)?$', line)
        if metadata:
            continue
        description = re.match(r'^\s*Description:\s*(.*)$', line)
        if description:
            if description.group(1):
                retained.append(description.group(1))
            continue
        retained.append(line)
    while retained and not retained[0].strip():
        retained.pop(0)
    if retained:
        retained[0] = retained[0].lstrip()
    cleaned = '\n'.join(retained).strip('\n')
    replacement = f'{docstring_match.group("quote")}{cleaned}\n{docstring_match.group("quote")}'
    return replacement + body[docstring_match.end() :]


def replace_project_license_references(text: str) -> str:
    """Replace obsolete AstraDesk-owned Apache license metadata and prose."""
    replacements = {
        'https://img.shields.io/badge/License-' + APACHE_NAME + '%202.0-yellow.svg': (
            'https://img.shields.io/badge/License-GPL--2.0--only-blue.svg'
        ),
        'https://www.' + APACHE_NAME.lower() + '.org/licenses/LICENSE-2.0': (
            'https://www.gnu.org/licenses/old-licenses/gpl-2.0.html'
        ),
        APACHE_LICENSE + ', Version 2.0': 'GNU General Public License version 2 only',
        APACHE_LICENSE + ' 2.0': 'GNU General Public License version 2 only',
        APACHE_SPDX: 'GPL-2.0-only',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def normalize_text(path: PurePosixPath, text: str) -> str:
    """Return normalized file content without writing to disk."""
    style = comment_style(path)
    if style is None:
        return text
    preamble, body = _split_preamble(text)
    body = strip_existing_header(body, style)
    body = strip_legacy_metadata(body, style)
    body = replace_project_license_references(body)
    header = canonical_header(path, style)
    separator = '' if not preamble or preamble.endswith('\n') else '\n'
    normalized = f'{preamble}{separator}{header}\n\n{body.lstrip(chr(10))}'
    return normalized.rstrip() + '\n'


def normalize_package_manifest(path: PurePosixPath, text: str) -> str:
    """Set project package metadata without adding invalid JSON comments."""
    if path.as_posix() not in PACKAGE_MANIFESTS:
        return text
    data = json.loads(text)
    if data.get('license') == 'GPL-2.0-only':
        return text
    if 'license' in data:
        return re.sub(
            r'("license"\s*:\s*)"[^"]*"',
            r'\1"GPL-2.0-only"',
            text,
            count=1,
        )
    anchor = re.search(r'^(\s*)"private"\s*:\s*(?:true|false),\s*$', text, re.MULTILINE)
    if anchor is None:
        raise ValueError(f'Cannot insert license metadata into {path}')
    insertion = f'{anchor.group(0)}\n{anchor.group(1)}"license": "GPL-2.0-only",'
    return text[: anchor.start()] + insertion + text[anchor.end() :]


def expected_text(path: PurePosixPath, text: str) -> str:
    """Return the complete expected content for any tracked path."""
    if path.as_posix() in PACKAGE_MANIFESTS:
        return normalize_package_manifest(path, text)
    return normalize_text(path, text)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def excluded_digests(root: Path, paths: Iterable[PurePosixPath]) -> dict[str, str]:
    """Capture immutable exclusion hashes to prove normalization did not touch them."""
    digests: dict[str, str] = {}
    for path in paths:
        absolute = root / path
        if is_excluded(path) and absolute.is_file() and not absolute.is_symlink():
            digests[path.as_posix()] = _digest(absolute)
    return digests


def process_repository(root: Path, *, check: bool) -> tuple[list[str], list[str]]:
    """Normalize or verify all tracked project-owned files."""
    paths = tracked_paths(root)
    before_exclusions = excluded_digests(root, paths)
    changed: list[str] = []
    errors: list[str] = []

    for path in paths:
        absolute = root / path
        if absolute.is_symlink() or not absolute.is_file() or is_excluded(path):
            continue
        if comment_style(path) is None and path.as_posix() not in PACKAGE_MANIFESTS:
            continue
        try:
            text = absolute.read_text(encoding='utf-8')
            expected = expected_text(path, text)
        except (UnicodeDecodeError, ValueError) as exc:
            errors.append(f'{path}: {exc}')
            continue
        if text != expected:
            changed.append(path.as_posix())
            if not check:
                absolute.write_text(expected, encoding='utf-8')

    after_exclusions = excluded_digests(root, paths)
    if before_exclusions != after_exclusions:
        errors.append('Generated, vendored, dependency, lock, build, or binary exclusions changed')

    if check:
        errors.extend(f'{path}: header or license metadata is not canonical' for path in changed)

    license_text = (root / 'LICENSE').read_text(encoding='utf-8')
    if (
        'GNU GENERAL PUBLIC LICENSE' not in license_text
        or 'Version 2, June 1991' not in license_text
        or APACHE_PATTERN.search(license_text)
    ):
        errors.append('LICENSE: root license is not the canonical GNU GPL version 2 text')

    for path in paths:
        absolute = root / path
        if absolute.is_symlink() or not absolute.is_file() or is_excluded(path):
            continue
        try:
            text = absolute.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        style = comment_style(path)
        if style is not None:
            header = canonical_header(path, style)
            if text.count(header) != 1:
                errors.append(f'{path}: expected exactly one complete canonical header')
        if APACHE_PATTERN.search(text):
            errors.append(f'{path}: obsolete Apache license reference remains')
        if (path.suffix == '.json' and style is None) or path.name in STRICT_JSON_NAMES:
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f'{path}: strict JSON is invalid: {exc}')
        if path.as_posix() in PACKAGE_MANIFESTS:
            if json.loads(text).get('license') != 'GPL-2.0-only':
                errors.append(f'{path}: project license metadata is not GPL-2.0-only')
        if path.name == 'pyproject.toml' and not re.search(
            r'^license\s*=.*GPL-2\.0-only', text, re.MULTILINE
        ):
            errors.append(f'{path}: Python project license metadata is not GPL-2.0-only')

    return changed, sorted(set(errors))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--check',
        action='store_true',
        help='Verify canonical headers and metadata without modifying files.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repository_root()
    changed, errors = process_repository(root, check=args.check)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    action = 'would normalize' if args.check else 'normalized'
    print(f'License headers verified; {action} {len(changed)} file(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
