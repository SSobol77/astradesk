
// services/ticket-adapter-java/src/main/java/com/astradesk/ticket/SecurityConfig.java
// Konfiguracja Spring Security dla aplikacji WebFlux z obsługą OAuth2 i JWT.
// Umożliwia dostęp do endpointów monitorujących bez uwierzytelniania,
// podczas gdy wszystkie inne żądania wymagają uwierzytelnienia.
// Plik ten jest częścią usługi Ticket Adapter w projekcie AstraDesk.
// Autor: Siergej Sobolewski
// Data: 2025-10-07
package com.astradesk.ticket;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
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