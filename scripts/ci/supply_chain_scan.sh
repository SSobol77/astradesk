#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: scripts/ci/supply_chain_scan.sh
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Automates AstraDesk development, deployment, or operational tasks.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

set -euo pipefail

# Fail-closed supply-chain image scan gate (GitHub issue #40 — NEW-01).
#
# Scans one or more already-built container images with Trivy and fails the
# build on any unaccepted HIGH/CRITICAL finding. This intentionally scans
# shipped images (not the repository filesystem, not .venv/node_modules/
# build caches): INV-SC-2/3 care about what actually ships, not about every
# transitive advisory that never reaches a runtime image.
#
# Disposition of any finding that is a documented false positive or a proven
# non-reachable advisory belongs in `.trivyignore` at the repository root,
# with an expiry annotation (`exp:YYYY-MM-DD`) and a justification comment
# directly above the entry — see that file's header for the exact format.
# Reachable findings are never suppressed here; they must be remediated.
#
# Absence of the `trivy` binary is treated as a gate failure (INV-FAIL-CLOSED),
# not a skip: a missing scanner must never silently pass a build.
#
# Usage: scripts/ci/supply_chain_scan.sh <image-ref> [<image-ref> ...]

SEVERITY='HIGH,CRITICAL'
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IGNORE_FILE="${REPO_ROOT}/.trivyignore"

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <image-ref> [<image-ref> ...]" >&2
  exit 2
fi

if ! command -v trivy >/dev/null 2>&1; then
  echo "supply_chain_scan.sh: 'trivy' is not installed or not on PATH." >&2
  echo "supply_chain_scan.sh: refusing to skip the supply-chain gate (fail-closed)." >&2
  exit 1
fi

if [ ! -f "${IGNORE_FILE}" ]; then
  echo "supply_chain_scan.sh: missing ${IGNORE_FILE} (required, even if empty of active entries)." >&2
  exit 1
fi

# INV-SC-4: every active .trivyignore entry must carry an `exp:YYYY-MM-DD`
# expiry and must not already be expired. Trivy itself (confirmed v0.72.0)
# correctly stops suppressing a finding once its `exp:` date has passed, but
# it does NOT require an `exp:` date to be present at all — a bare advisory
# ID would be silently suppressed forever, which this repository's own
# policy forbids. This check closes that gap before Trivy ever runs.
validate_ignorefile_expiry() {
  local file="$1"
  local today
  today="$(date -u +%Y-%m-%d)"
  local line_num=0
  local had_errors=0
  local trimmed
  while IFS= read -r line || [ -n "${line}" ]; do
    line_num=$((line_num + 1))
    trimmed="$(printf '%s' "${line}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -z "${trimmed}" ] && continue
    [ "${trimmed:0:1}" = "#" ] && continue
    if [[ "${trimmed}" =~ exp:([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
      local exp_date="${BASH_REMATCH[1]}"
      if [[ "${exp_date}" < "${today}" ]]; then
        echo "supply_chain_scan.sh: ${file}:${line_num}: entry expired on ${exp_date} (today=${today} UTC) — re-review or remove (INV-SC-4): ${trimmed}" >&2
        had_errors=1
      fi
    else
      echo "supply_chain_scan.sh: ${file}:${line_num}: active entry missing required 'exp:YYYY-MM-DD' suffix (INV-SC-4): ${trimmed}" >&2
      had_errors=1
    fi
  done <"${file}"
  return "${had_errors}"
}

if ! validate_ignorefile_expiry "${IGNORE_FILE}"; then
  echo "supply_chain_scan.sh: ${IGNORE_FILE} failed expiry validation (fail-closed)." >&2
  exit 1
fi

trivy_version="$(trivy --version 2>/dev/null | head -n1 || true)"
echo "supply_chain_scan.sh: using ${trivy_version:-trivy (version unknown)}"
echo "supply_chain_scan.sh: severity=${SEVERITY} ignorefile=${IGNORE_FILE}"

status=0
for image in "$@"; do
  echo ""
  echo "=== supply_chain_scan.sh: scanning ${image} ==="
  if ! trivy image \
      --severity "${SEVERITY}" \
      --exit-code 1 \
      --ignorefile "${IGNORE_FILE}" \
      --format table \
      --scanners vuln \
      "${image}"; then
    echo "supply_chain_scan.sh: ${image} FAILED — unaccepted reachable ${SEVERITY} finding(s)." >&2
    status=1
  else
    echo "supply_chain_scan.sh: ${image} PASSED."
  fi
done

exit "${status}"
