// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/TicketApp.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/TicketApp.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket;

import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

import com.astradesk.ticket.integration.props.IntegrationProperties;
import com.astradesk.ticket.repository.TicketRepository;

/**
 * Spring Boot entry point for the AstraDesk Ticket Adapter service.
 *
 * <p>The application exposes a reactive API that persists tickets, opens Jira
 * issues, and fan-outs notifications to Slack.</p>
 */
@SpringBootApplication
@EnableConfigurationProperties(IntegrationProperties.class)
public class TicketApp {

    public static void main(String[] args) {
        SpringApplication.run(TicketApp.class, args);
    }

    /**
     * Performs a lightweight startup check by counting existing records. This gives
     * operators a hint that the database connection is alive before any traffic hits
     * the service.
     */
    @Bean
    public ApplicationRunner databaseProbe(TicketRepository repository) {
        return args -> repository.count()
            .map(count -> "Ticket adapter started. Existing ticket count: %d".formatted(count))
            .doOnNext(System.out::println)
            .subscribe();
    }
}
