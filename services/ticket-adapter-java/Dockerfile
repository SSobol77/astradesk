# SPDX-License-Identifier: GPL-2.0-only
# Project: AstraDesk
# File: services/ticket-adapter-java/Dockerfile
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

# gradle:9.2.0-jdk21 (pinned by digest)
FROM gradle@sha256:f73b9e12248ea459a1118f40da095c5305e90e2ebb22b790bcf0bfb9fcb1e39b AS build

WORKDIR /workspace

# Copy root Gradle wrapper and settings to resolve plugins shared across the AstraDesk Enterprise AI Agents Framework
COPY gradlew ./gradlew
COPY gradle ./gradle
COPY settings.gradle.kts ./settings.gradle.kts
COPY build.gradle.kts ./build.gradle.kts

# Copy the service sources
COPY services/ticket-adapter-java ./services/ticket-adapter-java

# Ensure wrapper is executable and build only the ticket adapter module
RUN chmod +x gradlew && \
    ./gradlew :services:ticket-adapter-java:bootJar --no-daemon

# eclipse-temurin:21-jre (pinned by digest)
FROM eclipse-temurin@sha256:d2b9f8f12212cadcfdf889461531784e8fd097feade954d65b31ee7a71c473ec
WORKDIR /app
COPY --from=build /workspace/services/ticket-adapter-java/build/libs/*.jar app.jar

# Fixed numeric non-root UID/GID (INV-BUILD-3); eclipse-temurin runs as root
# by default.
RUN groupadd -g 10001 astradesk && \
    useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin astradesk && \
    chown 10001:10001 app.jar

USER 10001:10001
EXPOSE 8081
ENTRYPOINT ["java","-jar","app.jar"]
