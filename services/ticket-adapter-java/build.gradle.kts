// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/build.gradle.kts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/build.gradle.kts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

/* File: services/ticket-adapter-java/build.gradle.kts
 *  Module: Ticket Adapter (Spring Boot WebFlux + R2DBC MySQL), Gradle 9+, JDK 21 LTS.
*/

import org.gradle.jvm.toolchain.JavaLanguageVersion
import org.springframework.boot.gradle.tasks.bundling.BootJar
import org.springframework.boot.gradle.tasks.run.BootRun

plugins {
    id("java")
    id("jacoco")                              // test coverage report consumed by CI/Sonar
    id("org.springframework.boot")            // wersja przypięta w root build.gradle.kts
    id("io.spring.dependency-management")     // zarządzanie wersjami zależności przez BOM SB
}

group = "com.astradesk"
version = "0.3.0"
description = "AstraDesk Ticket Adapter Service"

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
    // Lepsze wsparcie dla refleksji (np. Jackson, Spring Validation)
    withJavadocJar()
    withSourcesJar()
}


configurations {
    compileOnly {
        extendsFrom(configurations.annotationProcessor.get())
    }
}

dependencies {
    // --- Web / Actuator / Security ---
    implementation("org.springframework.boot:spring-boot-starter-webflux")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")

    // --- R2DBC (Reactive MySQL) ---
    implementation("org.springframework.boot:spring-boot-starter-data-r2dbc")
    // Driver R2DBC dla MySQL (Asyncer)
    runtimeOnly("io.asyncer:r2dbc-mysql")
    // (opcjonalnie) Pula połączeń R2DBC:
    // implementation("io.r2dbc:r2dbc-pool")

    // --- Compile-only & annotation processing ---
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    annotationProcessor("org.springframework.boot:spring-boot-configuration-processor")

    // --- Testy ---
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher") // Required explicitly since Gradle 9
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    // Przekazuje nazwy parametrów do bytecode; ułatwia bindowanie/serializację
    options.compilerArgs.add("-parameters")
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
    finalizedBy(tasks.named("jacocoTestReport"))
}

tasks.named<JacocoReport>("jacocoTestReport") {
    dependsOn(tasks.named("test"))
    reports {
        // CI uploads build/reports/jacoco/test/jacocoTestReport.xml (the default path).
        xml.required.set(true)
        html.required.set(true)
    }
}

tasks.withType<BootJar>().configureEach {
    // Jawnie włączamy layery, żeby obraz/artefakt był warstwowy
    layered {
    // Opcjonalnie możemy dodać własne reguły warstw:
    // layers {
    //     includeLayer("dependencies") { intoLayer("dependencies") }
    //     includeLayer("spring-boot-loader") { intoLayer("spring-boot-loader") }
    //     includeLayer("snapshot-dependencies") { intoLayer("snapshot-dependencies") }
    //     includeLayer("application") { intoLayer("application") }
    }
}

tasks.withType<BootRun>().configureEach {
    // Ustawienia profili/DSN przez system properties (czytelne w Kotlin DSL)
    fun env(name: String, fallback: String) = System.getenv(name) ?: fallback

    systemProperty("spring.profiles.active", "dev")
    systemProperty("spring.r2dbc.url",      env("MYSQL_URL_R2DBC", "r2dbc:mysql://localhost:3306/tickets"))
    systemProperty("spring.r2dbc.username", env("MYSQL_USER", "tickets"))
    systemProperty("spring.r2dbc.password", env("MYSQL_PASSWORD", "tickets"))
    systemProperty("spring.security.oauth2.resourceserver.jwt.issuer-uri",
                   env("OIDC_ISSUER", "https://dummy-issuer.com"))
}
