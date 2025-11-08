// build.gradle.kts (w głównym katalogu)

// Ten plik definiuje wersje wtyczek dla całego AstraDesk Enterprise AI Agents Framework.
// build.gradle.kts — deklaracje pluginów dostępnych dla całego AstraDesk Enterprise AI Agents Framework
// Podprojekty same decydują, których wtyczek użyją (apply false).

plugins {
    id("org.springframework.boot") version "3.3.7" apply false
    id("io.spring.dependency-management") version "1.1.7" apply false
}
