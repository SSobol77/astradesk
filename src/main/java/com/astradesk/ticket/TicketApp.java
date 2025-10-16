/* 
 * SPDX-License-Identifier: Apache-2.0
 * File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/TicketApp.java
 * Project: AstraDesk Framework
 * Description: Spring Boot entrypoint for the Ticket Adapter microservice (dev demo with Project Reactor).
 * Author: Siergej Sobolewski
 * Since: 2025-10-07
 */

package com.astradesk.ticket;

import java.time.Duration;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Profile;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Główna klasa aplikacji dla mikroserwisu Ticket Adapter.
 *
 * <p>Inicjalizuje aplikację Spring Boot i, w profilu deweloperskim,
 * uruchamia demonstrację możliwości Project Reactor.
 */
@SpringBootApplication
public class TicketApp {

    private static final Logger log = LoggerFactory.getLogger(TicketApp.class);

    public static void main(String[] args) {
        SpringApplication.run(TicketApp.class, args);
    }

    /**
     * Bean typu {@link CommandLineRunner}, który uruchamia się po starcie aplikacji.
     * Jest aktywny tylko w profilu "dev", aby nie zaśmiecać logów w środowisku produkcyjnym.
     *
     * <p><b>Jak to uruchomić?</b></p>
     * <p>Ustaw w `application.yml` profil `spring.profiles.active: dev`
     * lub uruchom aplikację z argumentem `--spring.profiles.active=dev`.</p>
     *
     * @return Implementacja CommandLineRunner z demonstracją Project Reactor.
     */
    @Bean
    @Profile("dev")
    public CommandLineRunner reactorDemo() {
        return args -> {
            log.info("--- ROZPOCZYNANIE DEMONSTRACJI PROJECT REACTOR ---");

            // Przykład 1: Prosty strumień (Flux) i transformacja (map)
            log.info(">>> Przykład 1: Transformacja liczb (map)");
            Flux<Integer> numbers = Flux.range(1, 5)
                .map(i -> i * 10); // Każdy element pomnóż przez 10

            numbers.subscribe(
                number -> log.info("Otrzymano liczbę: {}", number),
                error -> log.error("Wystąpił błąd!", error),
                () -> log.info("Strumień liczb zakończony.")
            );
            
            // Czekamy chwilę, aby dać czas na wykonanie asynchronicznych operacji
            Thread.sleep(100);

            // Przykład 2: Filtrowanie i operacje asynchroniczne (flatMap)
            log.info(">>> Przykład 2: Filtrowanie i symulacja operacji I/O (flatMap)");
            Flux<String> users = Flux.just("user1", "admin", "user2", "guest")
                .filter(user -> !user.equals("guest")) // Odrzuć "guest"
                .flatMap(user -> fetchPermissions(user)); // Dla każdego użytkownika, pobierz jego uprawnienia (operacja asynchroniczna)

            users.subscribe(
                permissionInfo -> log.info("Informacja o uprawnieniach: {}", permissionInfo),
                error -> log.error("Błąd podczas pobierania uprawnień!", error),
                () -> log.info("Strumień uprawnień zakończony.")
            );
            
            Thread.sleep(1000); // Dłuższe oczekiwanie, bo symulujemy I/O

            // Przykład 3: Łączenie dwóch strumieni (zip)
            log.info(">>> Przykład 3: Łączenie dwóch strumieni (zip)");
            Flux<String> ticketTitles = Flux.just("Problem z VPN", "Błąd drukarki");
            Flux<String> ticketPriorities = Flux.just("Wysoki", "Niski");

            Flux<String> combined = Flux.zip(ticketTitles, ticketPriorities)
                // Tuples.of() tworzy krotkę z dwóch wartości
                .map(tuple -> String.format("Zgłoszenie: '%s' ma priorytet: %s", tuple.getT1(), tuple.getT2()));

            combined.subscribe(
                result -> log.info(result),
                error -> log.error("Błąd podczas łączenia strumieni!", error),
                () -> log.info("Połączony strumień zakończony.")
            );

            log.info("--- DEMONSTRACJA ZAKOŃCZONA :) ---");
        };
    }

    /**
     * Pomocnicza metoda symulująca asynchroniczną operację,
     * np. zapytanie do innej usługi lub bazy danych.
     *
     * @param username Nazwa użytkownika.
     * @return Mono z informacją o uprawnieniach.
     */
    private Mono<String> fetchPermissions(String username) {
        // Symulujemy opóźnienie sieciowe
        return Mono.delay(Duration.ofMillis(100 + (long) (Math.random() * 200)))
            .map(ignored -> {
                if ("admin".equals(username)) {
                    return String.format("Użytkownik '%s' ma pełne uprawnienia (READ, WRITE, DELETE)", username);
                }
                return String.format("Użytkownik '%s' ma podstawowe uprawnienia (READ)", username);
            });
    }
}
