// build.gradle.kts (w głównym katalogu)

// Ten plik definiuje wersje wtyczek dla całego monorepo.
// build.gradle.kts — deklaracje pluginów dostępnych dla całego monorepo
// Podprojekty same decydują, których wtyczek użyją (apply false).

plugins {
    id("org.springframework.boot") version "3.3.5" apply false
    id("io.spring.dependency-management") version "1.1.5" apply false
}
