#!/usr/bin/env bash
set -euo pipefail

# Optional: if you stay on Docker Desktop, uncomment the next line
# export DOCKER_HOST=unix://$HOME/.docker/desktop/docker.sock

out="Docker_Audit_Report.md"
echo "# Docker Audit Report" > "$out"
echo -e "\n| Service | Image Tag | Port | Build | Run | Health | Notes |" >> "$out"
echo "| --- | --- | --- | --- | --- | --- | --- |" >> "$out"

row() { echo "| $1 | \`$2\` | ${3:-n/a} | $4 | $5 | $6 | $7 |" >> "$out"; }

# Admin Portal
svc="services/admin-portal"; tag="astradesk-admin-portal-audit"; port=3000
b="ok"; r="ok"; h="fail"; note=""
if ! docker build -t "$tag" "$svc" >/dev/null; then b="fail"; r="fail"; note="build failed"
else
  docker rm -f admin-portal-audit >/dev/null 2>&1 || true
  if ! docker run --rm -d --name admin-portal-audit -p ${port}:3000 "$tag" >/dev/null; then r="fail"; note="run failed"
  else
    sleep 2
    if curl -sf "http://localhost:${port}/health" >/dev/null; then h="ok"; else note="GET /health returned non-200"; fi
    docker rm -f admin-portal-audit >/dev/null 2>&1 || true
  fi
fi
row "$svc" "$tag" "$port" "$b" "$r" "$h" "${note:-}"

# Ticket Adapter (Spring)
svc="services/ticket-adapter-java"; tag="astradesk-ticket-adapter-java-audit"; port=8081
b="ok"; r="ok"; h="fail"; note=""
if ! docker build -t "$tag" "$svc" >/dev/null; then b="fail"; r="fail"; note="build failed"
else
  docker rm -f ticket-adapter-audit >/dev/null 2>&1 || true
  if ! docker run --rm -d --name ticket-adapter-audit -p ${port}:8081 "$tag" >/dev/null; then r="fail"; note="run failed"
  else
    sleep 3
    if curl -sf "http://localhost:${port}/actuator/health" >/dev/null; then h="ok"; else note="GET /actuator/health non-200"; fi
    docker rm -f ticket-adapter-audit >/dev/null 2>&1 || true
  fi
fi
row "$svc" "$tag" "$port" "$b" "$r" "$h" "${note:-}"

# Auditor (worker)
svc="services/auditor"; tag="astradesk-auditor-audit"; port="n/a"
b="ok"; r="ok"; h="n/a"; note=""
if ! docker build -t "$tag" "$svc" >/dev/null; then b="fail"; r="fail"; note="build failed"
else
  # one-shot; exit 0 => OK
  if ! docker run --rm --name auditor-audit "$tag" >/dev/null; then r="fail"; note="container exited non-zero"; fi
fi
row "$svc" "$tag" "$port" "$b" "$r" "$h" "${note:-}"

echo -e "\nReport saved to: $out"
