// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/TicketMapper.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/TicketMapper.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.web;

import org.springframework.stereotype.Component;

import com.astradesk.ticket.domain.Ticket;
import com.astradesk.ticket.web.dto.TicketResponse;

/**
 * Centralises conversion between persistence objects and API DTOs so the shape of
 * responses stays consistent across controllers.
 */
@Component
public class TicketMapper {

    public TicketResponse toResponse(Ticket ticket) {
        return new TicketResponse(
            ticket.getId(),
            ticket.getTitle(),
            ticket.getBody(),
            ticket.getStatus(),
            ticket.getJiraIssueKey(),
            ticket.getSlackChannel(),
            ticket.getCreatedAt(),
            ticket.getUpdatedAt()
        );
    }
}
