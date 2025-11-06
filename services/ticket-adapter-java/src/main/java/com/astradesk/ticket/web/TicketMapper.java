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
