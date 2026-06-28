// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: packages/domain-supply/build.gradle.kts
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for packages/domain-supply/build.gradle.kts.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

plugins {
    id 'java'
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.fasterxml.jackson.core:jackson-databind:2.17.2'
    implementation 'io.github.resilience4j:resilience4j-retry:2.2.0'
    implementation 'org.slf4j:slf4j-api:2.0.16'  // Logging
    implementation 'io.grpc:grpc-netty:1.66.0'
    implementation 'io.grpc:grpc-protobuf:1.66.0'
    implementation 'io.grpc:grpc-stub:1.66.0'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.11.0'
    testImplementation 'com.squareup.okhttp3:mockwebserver:5.0.0-alpha.14'
    testImplementation 'io.grpc:grpc-testing:1.66.0'
}

tasks.withType(JavaCompile) {
    options.encoding = 'UTF-8'
}
