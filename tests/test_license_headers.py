# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: tests/test_license_headers.py
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Verifies AstraDesk behavior for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

from __future__ import annotations

import json
from pathlib import PurePosixPath

from scripts.license_headers import (
    SPDX,
    canonical_header,
    comment_style,
    is_excluded,
    normalize_package_manifest,
    normalize_text,
)


def test_normalization_is_idempotent_and_removes_duplicate_old_header() -> None:
    path = PurePosixPath('packages/domain-ops/tests/test_agent.py')
    source = (
        '# SPDX-License-Identifier: ' + 'Apache' + '-2.0\n'
        '# File: old/path.py\n'
        '# SPDX-License-Identifier: ' + 'Apache' + '-2.0\n'
        '"""Agent tests."""\n'
    )
    normalized = normalize_text(path, source)
    assert normalized.count(SPDX) == 1
    assert 'Apache' + '-2.0' not in normalized
    assert '"""Agent tests."""' in normalized
    assert normalize_text(path, normalized) == normalized


def test_shebang_and_encoding_are_preserved_before_header() -> None:
    path = PurePosixPath('scripts/tool.py')
    source = '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\nprint("ok")\n'
    normalized = normalize_text(path, source)
    lines = normalized.splitlines()
    assert lines[0] == '#!/usr/bin/env python3'
    assert lines[1] == '# -*- coding: utf-8 -*-'
    assert lines[2] == f'# {SPDX}'


def test_xml_and_html_declarations_remain_first() -> None:
    svg = normalize_text(PurePosixPath('docs/logo.svg'), '<?xml version="1.0"?>\n<svg></svg>\n')
    html = normalize_text(PurePosixPath('docs/index.html'), '<!DOCTYPE html>\n<html></html>\n')
    assert svg.startswith('<?xml version="1.0"?>\n<!--\n')
    assert html.startswith('<!DOCTYPE html>\n<!--\n')


def test_unrelated_notice_below_source_is_preserved() -> None:
    path = PurePosixPath('src/module.py')
    notice = '# Third-party component license notice: BSD-3-Clause\n'
    normalized = normalize_text(path, f'print("owned")\n{notice}')
    assert notice in normalized


def test_legacy_module_metadata_is_removed_but_description_is_preserved() -> None:
    path = PurePosixPath('src/module.py')
    source = (
        '"""File: src/module.py\n'
        'Project: AstraDesk Framework\n'
        'Description:\n'
        '    Implements the runtime module.\n\n'
        'Author: Previous Author\n'
        'Since: 2025-01-01\n'
        '"""\n'
    )
    normalized = normalize_text(path, source)
    assert 'Project: AstraDesk Framework' not in normalized
    assert 'Author: Previous Author' not in normalized
    assert 'Implements the runtime module.' in normalized


def test_early_markdown_metadata_comments_are_removed() -> None:
    path = PurePosixPath('docs/README.md')
    source = (
        '# Component\n\n'
        '<!-- SPDX-License-Identifier: ' + 'Apache' + '-2.0 -->\n'
        '<!-- Description: Legacy description. -->\n'
        '<!-- Author: Previous Author -->\n\n'
        'Documentation.\n'
    )
    normalized = normalize_text(path, source)
    assert normalized.count(SPDX) == 1
    assert 'Previous Author' not in normalized


def test_tsconfig_uses_jsonc_line_comment_header() -> None:
    path = PurePosixPath('services/admin-portal/tsconfig.json')
    normalized = normalize_text(path, '{\n  // JSONC setting\n}\n')
    assert normalized.startswith('// SPDX-License-Identifier: GPL-2.0-only')
    assert '// JSONC setting' in normalized


def test_generated_and_dependency_paths_are_excluded() -> None:
    excluded = [
        PurePosixPath('services/admin-portal/package-lock.json'),
        PurePosixPath('services/admin-portal/src/api/types.gen.ts'),
        PurePosixPath('packages/domain-finance/src/domain_finance/proto/finance_pb2.py'),
        PurePosixPath('services/ticket-adapter-java/gradlew'),
        PurePosixPath('services/ticket-adapter-java/.gradle/state.bin'),
    ]
    assert all(is_excluded(path) for path in excluded)
    assert all(comment_style(path) is None for path in excluded)


def test_package_json_uses_metadata_without_comment_header() -> None:
    path = PurePosixPath('services/admin-portal/package.json')
    source = '{\n  "name": "astradesk-admin",\n  "private": true,\n  "scripts": {}\n}\n'
    normalized = normalize_package_manifest(path, source)
    assert json.loads(normalized)['license'] == 'GPL-2.0-only'
    assert 'SPDX-License-Identifier' not in normalized


def test_css_header_uses_block_comment() -> None:
    path = PurePosixPath('docs/styles/site.css')
    header = canonical_header(path, 'css')
    assert header.startswith('/*\n * SPDX-License-Identifier: GPL-2.0-only')
    assert header.endswith('\n */')
