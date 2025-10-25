#!/usr/bin/env bash
set -euo pipefail

SPEC="openapi/astradesk-admin.v1.yaml"
OPENAPI_WANT="3.1.0"
API_VER_WANT="1.2.0"

grep -Eq "^openapi:[[:space:]]+${OPENAPI_WANT}$" "$SPEC" \
  || { echo "ERROR: openapi must be ${OPENAPI_WANT}"; exit 1; }

grep -Eq '^[[:space:]]*version:[[:space:]]*"'${API_VER_WANT}'"' "$SPEC" \
  || { echo 'ERROR: info.version must be "'${API_VER_WANT}'"'; exit 1; }

# UI: jeśli nie symlink, wymuś zgodność
if [ -f services/admin-portal/openapi/OpenAPI.yaml ] && [ ! -L services/admin-portal/openapi/OpenAPI.yaml ]; then
  diff -q "$SPEC" services/admin-portal/openapi/OpenAPI.yaml \
    || { echo "ERROR: UI OpenAPI.yaml out of sync"; exit 1; }
fi

# Drobny check labelu w mkdocs (warning, nie fail)
grep -Eq 'Admin API v'"${API_VER_WANT}" mkdocs.yml \
  || { echo "WARN: mkdocs.yml nav label may be outdated"; :; }
