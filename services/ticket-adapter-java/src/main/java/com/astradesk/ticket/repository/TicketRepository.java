// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/repository/TicketRepository.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/repository/TicketRepository.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

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
