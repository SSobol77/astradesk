import org.springframework.boot.gradle.tasks.bundling.BootJar
import org.springframework.boot.gradle.tasks.run.BootRun
import org.gradle.jvm.toolchain.JavaLanguageVersion

plugins {
    id("java")
    id("org.springframework.boot") version "3.3.2"
    id("io.spring.dependency-management") version "1.1.5"
}

java {
    toolchain { languageVersion.set(JavaLanguageVersion.of(21)) }
}

repositories {
    mavenCentral()
}

configurations {
    compileOnly { extendsFrom(configurations.annotationProcessor.get()) }
}

dependencies {
    // --- Spring Core ---
    implementation("org.springframework.boot:spring-boot-starter-webflux")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")

    // --- Actuator (health, metrics) ---
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    // Prometheus (opcjonalnie):
    // implementation("io.micrometer:micrometer-registry-prometheus")

    // --- DB (opcjonalnie, jeśli używasz reaktywnej bazy) ---
    implementation("org.springframework.boot:spring-boot-starter-data-r2dbc")
    runtimeOnly("io.asyncer:r2dbc-mysql:1.1.3")
    // Flyway + JDBC driver (jeśli chcesz migracje na starcie; w przeciwnym razie usuń):
    // implementation("org.flywaydb:flyway-core")
    // runtimeOnly("com.mysql:mysql-connector-j:8.4.0")

    // --- HTTP klient do Admin API ---
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // --- Anotacje/Procesory ---
    compileOnly("org.projectlombok:lombok:1.18.30")
    annotationProcessor("org.projectlombok:lombok:1.18.30")
    compileOnly("org.mapstruct:mapstruct:1.5.5.Final")
    annotationProcessor("org.mapstruct:mapstruct-processor:1.5.5.Final")
    annotationProcessor("org.springframework.boot:spring-boot-configuration-processor")

    // --- Testy ---
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
    // Testcontainers, gdy potrzebne:
    // testImplementation("org.testcontainers:testcontainers:1.20.1")
    // testImplementation("org.testcontainers:mysql:1.20.1")
    // Embedded R2DBC:
    // testImplementation("io.r2dbc:r2dbc-h2")
}

sourceSets {
    named("main") {
        java.srcDir("src/main/java-gen") // wygenerowane SDK/klient
    }
}

tasks.test {
    useJUnitPlatform()
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.addAll(listOf("-parameters"))
    // Jeśli używasz MapStruct i chcesz domyślny model Spring:
    // options.compilerArgs.add("-Amapstruct.defaultComponentModel=spring")
}

tasks.withType<BootJar>().configureEach {
    layered {
        enabled.set(true)
    }
}

// BootRun tylko na DEV; w produkcji używamy ENV w kontenerze/K8s
tasks.named<BootRun>("bootRun") {
    systemProperties(
        mapOf(
            "spring.profiles.active" to "dev",
            // DB (R2DBC) — ustaw jeśli używasz bazy
            "spring.r2dbc.url" to (System.getenv("MYSQL_URL_R2DBC") ?: "r2dbc:mysql://localhost:3306/tickets"),
            "spring.r2dbc.username" to (System.getenv("MYSQL_USER") ?: "tickets"),
            "spring.r2dbc.password" to (System.getenv("MYSQL_PASSWORD") ?: "tickets"),
            // Security (OIDC/JWT)
            "spring.security.oauth2.resourceserver.jwt.issuer-uri" to
                (System.getenv("OIDC_ISSUER") ?: "https://dummy-issuer.com")
        )
    )
}