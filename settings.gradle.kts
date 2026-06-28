// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: settings.gradle.kts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for settings.gradle.kts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

// settings.gradle.kts (root)
// Author: Siergej Sobolewski
// Since: 2025-10-25

import org.gradle.api.GradleException
import org.gradle.util.GradleVersion

val requiredVersion = GradleVersion.version("9.2")
val currentVersion = GradleVersion.current()
if (currentVersion < requiredVersion) {
    throw GradleException("Project requires Gradle >= ${requiredVersion.version} (current: ${currentVersion.version})")
}

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        mavenCentral()
    }
}

rootProject.name = "astradesk"

include("services:ticket-adapter-java")
// In future:
// include("packages:domain-finance")
