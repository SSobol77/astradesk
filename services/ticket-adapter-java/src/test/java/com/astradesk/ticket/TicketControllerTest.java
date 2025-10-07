// src/test/java/com/astradesk/ticket/TicketControllerTest.java
// Testy jednostkowe dla TicketController w aplikacji Ticket Adapter.
// Sprawdzają poprawność działania endpointów REST z uwzględnieniem zabezpieczeń.
// Plik ten jest częścią usługi Ticket Adapter w projekcie AstraDesk.
// Autor: Siergej Sobolewski
// Data: 2025-10-07
package com.astradesk.ticket;

import static org.assertj.core.api.Assertions.assertThat;
import org.junit.jupiter.api.DisplayName; // Importujemy DTO z kodu produkcyjnego
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import static org.mockito.Mockito.when;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser; // Do wczytania SecurityConfig
import org.springframework.test.web.reactive.server.WebTestClient;

import com.astradesk.ticket.http.TicketController;
import com.astradesk.ticket.http.TicketReq;
import com.astradesk.ticket.model.Ticket;
import com.astradesk.ticket.repo.TicketRepo;

import reactor.core.publisher.Mono;

/**
 * Testy jednostkowe dla {@link TicketController}.
 *
 * Używa {@link WebFluxTest} do testowania warstwy webowej w izolacji,
 * z mockowanym repozytorium i włączonym Spring Security.
 */
@WebFluxTest(controllers = TicketController.class)
@Import(SecurityConfig.class) // ZMIANA: Musimy zaimportować naszą konfigurację bezpieczeństwa
@DisplayName("Ticket Controller Tests")
class TicketControllerTest {

    @Autowired
    private WebTestClient webClient;

    @MockBean
    private TicketRepo repo;

    @Nested
    @DisplayName("Endpoint POST /api/tickets (Create Ticket)")
    class CreateTicketTests {

        @Test
        @WithMockUser // Symulujemy uwierzytelnionego użytkownika
        @DisplayName("Powinien utworzyć ticket i zwrócić status 201 dla poprawnego żądania")
        void shouldCreateTicketSuccessfully() {
            // Given
            var request = new TicketReq("Poprawny tytuł", "Poprawny opis");
            var ticketCaptor = ArgumentCaptor.forClass(Ticket.class);

            when(repo.save(ticketCaptor.capture())).thenAnswer(invocation -> {
                Ticket ticketToSave = invocation.getArgument(0);
                // Symulujemy, że baza danych nadała ID
                return Mono.just(new Ticket(1L, ticketToSave.title(), ticketToSave.body()));
            });

            // When & Then
            webClient.post().uri("/api/tickets")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .exchange()
                .expectStatus().isCreated()
                .expectBody()
                .jsonPath("$.id").isEqualTo(1)
                .jsonPath("$.title").isEqualTo("Poprawny tytuł")
                .jsonPath("$.body").isEqualTo("Poprawny opis");

            assertThat(ticketCaptor.getValue().title()).isEqualTo("Poprawny tytuł");
        }

        @Test
        @WithMockUser
        @DisplayName("Powinien zwrócić status 400 dla żądania z pustym tytułem")
        void shouldReturnBadRequestWhenTitleIsBlank() {
            // Given
            var requestWithBlankTitle = new TicketReq("", "Jakiś opis");

            // When & Then
            webClient.post().uri("/api/tickets")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(requestWithBlankTitle)
                .exchange()
                .expectStatus().isBadRequest();
        }

        @Test
        @DisplayName("Powinien zwrócić status 401 dla nieuwierzytelnionego użytkownika")
        void shouldReturnUnauthorizedForUnauthenticatedUser() {
            // Given
            var request = new TicketReq("Tytuł", "Opis");

            // When & Then
            webClient.post().uri("/api/tickets")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .exchange()
                .expectStatus().isUnauthorized(); // Sprawdzamy, czy zabezpieczenia działają
        }
    }

    @Nested
    @DisplayName("Endpoint GET /api/tickets/{id} (Get Ticket)")
    class GetTicketTests {

        @Test
        @WithMockUser
        @DisplayName("Powinien zwrócić ticket i status 200 dla istniejącego ID")
        void shouldReturnTicketById() {
            // Given
            var ticket = new Ticket(1L, "Test", "Opis");
            when(repo.findById(1L)).thenReturn(Mono.just(ticket));

            // When & Then
            webClient.get().uri("/api/tickets/1")
                .exchange()
                .expectStatus().isOk()
                .expectBody(Ticket.class).isEqualTo(ticket);
        }

        @Test
        @WithMockUser
        @DisplayName("Powinien zwrócić status 404 dla nieistniejącego ID")
        void shouldReturnNotFoundForUnknownId() {
            // Given
            when(repo.findById(99L)).thenReturn(Mono.empty());

            // When & Then
            webClient.get().uri("/api/tickets/99")
                .exchange()
                .expectStatus().isNotFound();
        }
        
        @Test
        @DisplayName("Powinien zwrócić status 401 dla nieuwierzytelnionego użytkownika")
        void shouldReturnUnauthorizedForUnauthenticatedUser() {
            // When & Then
            webClient.get().uri("/api/tickets/1")
                .exchange()
                .expectStatus().isUnauthorized();
        }
    }
}