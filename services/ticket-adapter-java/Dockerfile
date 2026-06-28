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

FROM gradle:9.2.0-jdk21 AS build

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

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /workspace/services/ticket-adapter-java/build/libs/*.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java","-jar","app.jar"]
