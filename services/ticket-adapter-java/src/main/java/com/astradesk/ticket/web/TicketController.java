// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/TicketController.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/TicketController.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

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
