// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/http/TicketController.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/http/TicketController.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.http;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import com.astradesk.ticket.model.Ticket;
import com.astradesk.ticket.repo.TicketRepo;

import jakarta.validation.Valid;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Kontroler REST do zarządzania zgłoszeniami.
 * Udostępnia reaktywne endpointy do tworzenia, pobierania i listowania zgłoszeń.
 */
@RestController
@RequestMapping(path = "/api/tickets", produces = MediaType.APPLICATION_JSON_VALUE)
public class TicketController {
    private final TicketRepo repo;

    public TicketController(TicketRepo repo) {
        this.repo = repo;
    }

    /**
     * Tworzy nowe zgłoszenie na podstawie przesłanych danych.
     *
     * @param req Obiekt DTO z danymi zgłoszenia.
     * @return Zapisane zgłoszenie z nadanym ID.
     */
    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    @PreAuthorize("isAuthenticated()") // <- Tylko uwierzytelniony użytkownik może tworzyć ticket!!
    public Mono<Ticket> create(@Valid @RequestBody TicketReq req) {
        return repo.save(new Ticket(req.title(), req.body()));
    }

    /**
     * Pobiera pojedyncze zgłoszenie na podstawie jego ID.
     *
     * @param id Identyfikator zgłoszenia.
     * @return Zgłoszenie lub błąd 404, jeśli nie zostało znalezione.
     */
    @GetMapping("/{id}")
    @PreAuthorize("isAuthenticated()") // <- Tylko uwierzytelniony użytkownik może pobrać ticket!!
    public Mono<Ticket> get(@PathVariable Long id) {
        return repo.findById(id)
            .switchIfEmpty(Mono.error(new ResponseStatusException(HttpStatus.NOT_FOUND, "Zgłoszenie nie znalezione")));
    }

    /**
     * Zwraca listę wszystkich zgłoszeń.
     *
     * @return Strumień (Flux) wszystkich zgłoszeń.
     */
    @GetMapping
    @PreAuthorize("hasRole('SUPPORT_AGENT') or hasRole('ADMIN')") // <- PRZYKŁADOWE!! ZABEZPIECZENIE OPARTE NA ROLACH
    public Flux<Ticket> listAll() {
        return repo.findAll();
    }
}
