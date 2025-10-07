// src/main/java/com/astradesk/ticket/repo/TicketRepo.java
// Repozytorium do zarządzania encjami Ticket w sposób reaktywny
// Projekt: AstraDesk
// Autor: Siergej Sobolewski
// Data: 2025-10-07
package com.astradesk.ticket.repo;

import org.springframework.data.repository.reactive.ReactiveCrudRepository;
import org.springframework.stereotype.Repository;

import com.astradesk.ticket.model.Ticket;

/**
 * Repozytorium do zarządzania encjami Ticket w sposób reaktywny.
 * Rozszerza ReactiveCrudRepository, aby automatycznie uzyskać
 * podstawowe operacje CRUD (save, findById, findAll, etc.).
 */
@Repository
public interface TicketRepo extends ReactiveCrudRepository<Ticket, Long> {}
