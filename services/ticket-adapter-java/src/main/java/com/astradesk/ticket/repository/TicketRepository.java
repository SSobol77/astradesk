package com.astradesk.ticket.repository;

import org.springframework.data.repository.reactive.ReactiveCrudRepository;
import org.springframework.stereotype.Repository;

import com.astradesk.ticket.domain.Ticket;

/**
 * Reactive persistence gateway for tickets. Spring Data generates implementations
 * at runtime, keeping the adapter focused on orchestration logic.
 */
@Repository
public interface TicketRepository extends ReactiveCrudRepository<Ticket, Long> {

}
