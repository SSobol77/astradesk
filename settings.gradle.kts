// settings.gradle.kts (root)
// Author: Siergej Sobolewski
// Since: 2025-10-25

import org.gradle.api.GradleException
import org.gradle.util.GradleVersion

val requiredVersion = GradleVersion.version("8.7")
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
