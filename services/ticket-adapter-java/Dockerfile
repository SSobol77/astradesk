FROM gradle:9.2.0-jdk25 AS build

WORKDIR /workspace

# Copy root Gradle wrapper and settings to resolve plugins shared across the AstraDesk Enterprise AI Agents Framework
COPY gradlew ./gradlew
COPY gradle ./gradle
COPY settings.gradle.kts ./settings.gradle.kts
COPY build.gradle.kts ./build.gradle.kts

# Copy the service sources
COPY services/ticket-adapter-java ./services/ticket-adapter-java

# Ensure wrapper is executable and build only the ticket adapter module
RUN chmod +x gradlew && \
    ./gradlew :services:ticket-adapter-java:bootJar --no-daemon

FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=build /workspace/services/ticket-adapter-java/build/libs/*.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java","-jar","app.jar"]