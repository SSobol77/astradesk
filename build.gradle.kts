// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: build.gradle.kts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for build.gradle.kts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

// build.gradle.kts (w głównym katalogu)

// Ten plik definiuje wersje wtyczek dla całego AstraDesk Enterprise AI Agents Framework.
// build.gradle.kts — deklaracje pluginów dostępnych dla całego AstraDesk Enterprise AI Agents Framework
// Podprojekty same decydują, których wtyczek użyją (apply false).

plugins {
    id("org.springframework.boot") version "3.3.7" apply false
    id("io.spring.dependency-management") version "1.1.7" apply false
}
