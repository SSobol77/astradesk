/*
 * SPDX-License-Identifier: Apache-2.0
 * File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/repo/TicketRepo.java
 * Project: AstraDesk Framework — Ticket Adapter
 * Description: Reactive repository for Ticket entities (Spring Data, non-blocking access).
 * Author: Siergej Sobolewski
 * Since: 2025-10-07
 *
 * Notes (PL):
 *  - Zalecane użycie reaktywnego stosu (np. R2DBC / ReactiveMongo) bez blokowania wątków.
 *  - Definiuj zapytania metodami pochodnymi (query derivation) lub @Query przy złożonych przypadkach.
 *  - Nie mieszaj z blokującymi driverami JDBC w tym samym przepływie.
 */

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
