# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/auditor/Dockerfile
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

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

# Install core library first so dependent packages resolve
COPY core /opt/astradesk/core
RUN pip install --no-cache-dir /opt/astradesk/core

# Install auditor service (packaged via pyproject)
COPY services/auditor /opt/astradesk/auditor
RUN pip install --no-cache-dir /opt/astradesk/auditor

WORKDIR /opt/astradesk/auditor
CMD ["python", "main.py"]
