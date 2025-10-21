// settings.gradle.kts (w głównym katalogu)

import org.gradle.api.GradleException
import org.gradle.util.GradleVersion

// Sprawdzanie wersji Gradle jest dobrą praktyką.
val requiredVersion = GradleVersion.version("8.5") // Użyjmy stabilnej, powszechnie dostępnej wersji
val currentVersion = GradleVersion.current()
if (currentVersion < requiredVersion) {
    throw GradleException("Ten projekt wymaga Gradle w wersji >= ${requiredVersion.version} (obecna: ${currentVersion.version})")
}

// Zarządzanie repozytoriami dla wtyczek.
pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

// Zarządzanie repozytoriami dla zależności.
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        mavenCentral()
    }
}

// Definicja nazwy projektu głównego.
rootProject.name = "astradesk"

// Rejestracja wszystkich modułów, które używają Gradle.
include("services:ticket-adapter-java")
// W przyszłości:
// include("packages:domain-finance")