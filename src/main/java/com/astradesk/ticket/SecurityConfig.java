
/*
 * SPDX-License-Identifier: Apache-2.0
 * File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/SecurityConfig.java
 * Project: AstraDesk Framework — Ticket Adapter
 * Description: Spring Security configuration for WebFlux (OAuth2 Resource Server with JWT).
 *              Exposes actuator/monitoring endpoints without authentication; all other
 *              requests require a valid access token.
 * Author: Siergej Sobolewski
 * Since: 2025-10-07
 *
 * Notes (PL):
 *  - Tech stack: Spring Boot 3.x, Spring Security (WebFlux), OAuth2 Resource Server (JWT).
 *  - Dostęp publiczny: /actuator/health, /actuator/info (dostosuj wg potrzeb).
 *  - Reszta endpointów: wymaga uwierzytelnienia (Bearer JWT).
 *  - Rozważ CORS i CSRF (dla REST zwykle CSRF wyłączone).
 */

package com.astradesk.ticket;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.method.configuration.EnableReactiveMethodSecurity;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;

/**
 * Główna klasa konfiguracyjna dla Spring Security.
 *
 * <p>Ta klasa aktywuje i konfiguruje zabezpieczenia dla aplikacji WebFlux.
 * Włącza walidację tokenów JWT (OIDC Resource Server) i umożliwia
 * zabezpieczanie metod za pomocą adnotacji, takich jak {@code @PreAuthorize}.
 *
 * @see EnableWebFluxSecurity
 * @see EnableReactiveMethodSecurity
 */
@Configuration
@Profile("!no-db")
@EnableWebFluxSecurity
@EnableReactiveMethodSecurity
public class SecurityConfig {

    /**
     * Definiuje główny łańcuch filtrów bezpieczeństwa dla wszystkich żądań HTTP.
     *
     * @param http Obiekt do budowania konfiguracji bezpieczeństwa.
     * @return Skonfigurowany łańcuch filtrów bezpieczeństwa.
     */
    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        return http
            // Krok 1: Definiowanie reguł autoryzacji dla poszczególnych ścieżek
            .authorizeExchange(exchanges -> exchanges
                // Zezwalaj na anonimowy dostęp do endpointów monitorujących (health checks)
                .pathMatchers("/actuator/**").permitAll()
                // Wszystkie inne żądania muszą być uwierzytelnione
                .anyExchange().authenticated()
            )
            // Krok 2: Konfiguracja serwera zasobów OAuth2 do walidacji tokenów JWT
            // Użycie `Customizer.withDefaults()` włącza domyślną konfigurację,
            // która odczytuje ustawienia z `application.yml` (np. issuer-uri).
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            
            // Krok 3: Wyłączenie ochrony CSRF, co jest standardową praktyką
            // dla bezstanowych (stateless) API opartych na tokenach.
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            
            .build();
    }
}
