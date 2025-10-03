package com.astradesk.ticket;

import com.astradesk.ticket.http.TicketController;
import com.astradesk.ticket.model.Ticket;
import com.astradesk.ticket.repo.TicketRepo;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Mono;

@WebFluxTest(controllers = TicketController.class)
public class TicketControllerTest {

  @Autowired
  private WebTestClient webClient;

  @MockBean
  private TicketRepo repo;

  @Test
  void createsTicket() {
    Mockito.when(repo.save(Mockito.any(Ticket.class)))
      .thenAnswer(inv -> {
        Ticket t = inv.getArgument(0);
        t.setId(1L);
        return Mono.just(t);
      });

    webClient.post().uri("/api/tickets")
      .bodyValue(new TicketReq("Tytul","Opis"))
      .exchange()
      .expectStatus().isOk()
      .expectBody()
      .jsonPath("$.id").isEqualTo(1)
      .jsonPath("$.title").isEqualTo("Tytul");
  }

  static record TicketReq(String title, String body) {}
}
