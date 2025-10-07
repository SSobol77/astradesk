plugins {
  id("java")
  id("org.springframework.boot") version "3.3.2"
  id("io.spring.dependency-management") version "1.1.5"
}
java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }
repositories { mavenCentral() }
dependencies {
  implementation("org.springframework.boot:spring-boot-starter-webflux")
  implementation("org.springframework.boot:spring-boot-starter-validation")
  implementation("org.springframework.boot:spring-boot-starter-actuator")
  implementation("org.springframework.boot:spring-boot-starter-json")
  implementation("org.springframework.data:spring-data-r2dbc")
  implementation("org.springframework.boot:spring-boot-starter-security")
  implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
  runtimeOnly("io.asyncer:r2dbc-mysql:1.1.3")
  runtimeOnly("mysql:mysql-connector-java:8.0.33")
  testImplementation("org.springframework.boot:spring-boot-starter-test")
  testImplementation("org.springframework.security:spring-security-test")
}

// Konfiguruje zadanie `bootRun`, uruchamia aplikację
// z  odpowiednimi właściwościami systemowymi.
tasks.withType<org.springframework.boot.gradle.tasks.run.BootRun> {
    systemProperties = mapOf(
        "spring.profiles.active" to "dev",
        "spring.r2dbc.url" to (System.getenv("MYSQL_URL_R2DBC") ?: "r2dbc:mysql://localhost:3306/tickets"),
        "spring.r2dbc.username" to (System.getenv("MYSQL_USER") ?: "tickets"),
        "spring.r2dbc.password" to (System.getenv("MYSQL_PASSWORD") ?: "tickets"),
        "spring.security.oauth2.resourceserver.jwt.issuer-uri" to (System.getenv("OIDC_ISSUER") ?: "https://dummy-issuer.com")
    )
}