package com.astradesk.ticket.repo;

import com.astradesk.ticket.model.Ticket;
import org.springframework.data.repository.reactive.ReactiveCrudRepository;

public interface TicketRepo extends ReactiveCrudRepository<Ticket, Long> {}
