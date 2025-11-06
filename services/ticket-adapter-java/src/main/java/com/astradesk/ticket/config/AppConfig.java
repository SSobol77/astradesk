package com.astradesk.ticket.config;

import java.time.Clock;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Miscellaneous application-wide beans that don't belong in specific features
 * (e.g. utility infrastructure shared across services).
 */
@Configuration
public class AppConfig {

    @Bean
    public Clock clock() {
        return Clock.systemUTC();
    }
}
