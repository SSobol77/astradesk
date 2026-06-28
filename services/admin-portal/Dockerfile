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

FROM node:22-alpine AS deps
WORKDIR /app
COPY services/admin-portal/package.json services/admin-portal/package-lock.json* ./
RUN npm install && npm cache clean --force

FROM node:22-alpine AS build
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

FROM node:22-alpine AS runner
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
WORKDIR /app/standalone
EXPOSE 3000
CMD ["node", "server.js"]
