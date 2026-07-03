# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: dev/prometheus/Dockerfile
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

# dev/prometheus/Dockerfile
# prom/prometheus:v3.7.1 (pinned by digest)
FROM prom/prometheus@sha256:ff7e389acbe064a4823212a500393d40a28a8f362e4b05cbf6742a9a3ef736b2
USER root
COPY prometheus.yml /etc/prometheus/
# Fixed numeric non-root UID/GID (INV-BUILD-3): 65534 is the base image's
# "nobody" account, referenced numerically so it does not depend on
# username resolution at runtime.
RUN chown 65534:65534 /etc/prometheus/prometheus.yml && chmod 644 /etc/prometheus/prometheus.yml
USER 65534:65534
