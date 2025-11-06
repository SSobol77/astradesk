package com.astradesk.ticket.web;

import java.net.URI;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.astradesk.ticket.service.TicketService;
import com.astradesk.ticket.web.dto.TicketRequest;
import com.astradesk.ticket.web.dto.TicketResponse;
import com.astradesk.ticket.web.dto.TicketUpdateRequest;

import jakarta.validation.Valid;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * HTTP API exposed to the frontend. All endpoints are reactive and stream-friendly,
 * enabling the UI to receive updates without blocking.
 */
@RestController
@RequestMapping(path = "/api/tickets", produces = MediaType.APPLICATION_JSON_VALUE)
public class TicketController {

    private final TicketService ticketService;
    private final TicketMapper ticketMapper;

    public TicketController(TicketService ticketService, TicketMapper ticketMapper) {
        this.ticketService = ticketService;
        this.ticketMapper = ticketMapper;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public Mono<ResponseEntity<TicketResponse>> createTicket(@Valid @RequestBody TicketRequest request) {
        return ticketService.createTicket(request)
            .map(ticketMapper::toResponse)
            .map(response -> ResponseEntity
                .created(URI.create("/api/tickets/" + response.getId()))
                .body(response));
    }

    @GetMapping("/{id}")
    public Mono<TicketResponse> getTicket(@PathVariable Long id) {
        return ticketService.getTicket(id)
            .map(ticketMapper::toResponse);
    }

    @GetMapping
    public Flux<TicketResponse> listTickets() {
        return ticketService.listTickets()
            .map(ticketMapper::toResponse);
    }

    @PutMapping(path = "/{id}", consumes = MediaType.APPLICATION_JSON_VALUE)
    public Mono<TicketResponse> updateTicket(@PathVariable Long id, @Valid @RequestBody TicketUpdateRequest request) {
        return ticketService.updateTicket(id, request)
            .map(ticketMapper::toResponse);
    }
}
