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
  runtimeOnly("io.asyncer:r2dbc-mysql:1.1.3")
  runtimeOnly("mysql:mysql-connector-java:8.0.33")
  testImplementation("org.springframework.boot:spring-boot-starter-test")
}
