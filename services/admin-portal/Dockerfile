# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/admin-portal/Dockerfile
# Website: https://www.astradesk.dev
# Repository: https://github.com/SSobol77/astradesk
#
# Description: Builds the AstraDesk container image for the associated component.
#
# Copyright (c) 2026 Siergej Sobolewski
#
# This file is part of AstraDesk.
#
# AstraDesk is licensed under the GNU General Public License version 2 only.
# See the LICENSE file in the project root for the full license text.

ARG NEXT_PUBLIC_API_BASE_URL="http://localhost:8080/api/admin/v1"
ARG NEXT_PUBLIC_SIMULATION_MODE="false"

# node:22-alpine (pinned by digest)
FROM node@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS deps
WORKDIR /app
COPY services/admin-portal/package.json services/admin-portal/package-lock.json ./
RUN npm ci && npm cache clean --force

# node:22-alpine (pinned by digest)
FROM node@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_SIMULATION_MODE
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_SIMULATION_MODE=${NEXT_PUBLIC_SIMULATION_MODE}
COPY --from=deps /app/node_modules ./node_modules
COPY services/admin-portal/ ./
COPY openapi/astradesk-admin.v1.yaml ./OpenAPI.yaml
RUN npm run build

# node:22-alpine (pinned by digest)
FROM node@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_SIMULATION_MODE
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_SIMULATION_MODE=${NEXT_PUBLIC_SIMULATION_MODE}
COPY --from=build /app/.next/standalone ./standalone
COPY --from=build /app/.next/static ./standalone/.next/static
COPY --from=build /app/public ./standalone/public
COPY services/admin-portal/package.json ./standalone/package.json

# Runtime hardening (issue #40): CMD below only ever runs `node server.js`
# (the Next.js standalone server) and never npm/npx/corepack/yarn. The
# base image's global npm install carries its own vendored copies of
# picomatch and sigstore that trail upstream fixes (CVE-2026-33671,
# CVE-2026-48815); since the package manager is unreachable at runtime,
# drop it and corepack/yarn from this final stage rather than carry
# unused, vulnerable payload. The build/deps stages above still run
# `npm ci`/`npm run build` unaffected.
#
# Fixed numeric non-root UID/GID (INV-BUILD-3). The official node:22-alpine
# image already ships a `node` user/group at 1000:1000; reuse it explicitly.
RUN rm -rf \
      /usr/local/lib/node_modules/npm \
      /usr/local/lib/node_modules/corepack \
      /usr/local/bin/npm \
      /usr/local/bin/npx \
      /usr/local/bin/corepack \
      /usr/local/bin/yarn \
      /usr/local/bin/yarnpkg \
      /opt/yarn-v* \
    && chown -R 1000:1000 /app/standalone

WORKDIR /app/standalone
USER 1000:1000
EXPOSE 3000
CMD ["node", "server.js"]
