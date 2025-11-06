package com.astradesk.ticket.service;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

/**
 * Exception thrown when a ticket id does not exist. Spring WebFlux maps it to a
 * 404 response via {@link org.springframework.web.bind.annotation.ResponseStatus}.
 */
@ResponseStatus(HttpStatus.NOT_FOUND)
public class TicketNotFoundException extends RuntimeException {

    public TicketNotFoundException(Long id) {
        super("Ticket with id %d not found".formatted(id));
    }
}
