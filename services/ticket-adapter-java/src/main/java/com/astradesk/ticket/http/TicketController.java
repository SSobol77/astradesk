package com.astradesk.ticket.http;

import com.astradesk.ticket.model.Ticket;
import com.astradesk.ticket.repo.TicketRepo;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

record TicketReq(String title, String body) {}

@RestController
@RequestMapping(path="/api/tickets", produces=MediaType.APPLICATION_JSON_VALUE)
@Validated
public class TicketController {
  private final TicketRepo repo;
  public TicketController(TicketRepo repo) { this.repo = repo; }

  @PostMapping(consumes=MediaType.APPLICATION_JSON_VALUE)
  public Mono<Ticket> create(@RequestBody TicketReq req) {
    Ticket t = new Ticket(req.title(), req.body());
    return repo.save(t);
  }

  @GetMapping("/{id}")
  public Mono<Ticket> get(@PathVariable Long id) {
    return repo.findById(id);
  }
}
