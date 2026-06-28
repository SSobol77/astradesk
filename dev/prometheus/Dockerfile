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
FROM prom/prometheus:v3.7.1
USER root
COPY prometheus.yml /etc/prometheus/
RUN chown nobody:nobody /etc/prometheus/prometheus.yml && chmod 644 /etc/prometheus/prometheus.yml
USER nobody
