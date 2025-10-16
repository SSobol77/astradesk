/*
 * SPDX-License-Identifier: Apache-2.0
 * File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/http/TicketReq.java
 * Project: AstraDesk Framework — Ticket Adapter
 * Description: DTO for creating a new ticket with validation annotations.
 * Author: Siergej Sobolewski
 * Since: 2025-10-07
 */
package com.astradesk.ticket.http;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Rekord DTO (Data Transfer Object) dla żądania utworzenia nowego zgłoszenia.
 * Używa adnotacji walidacyjnych do zapewnienia integralności danych.
 *
 * @param title Tytuł zgłoszenia (musi mieć od 3 do 255 znaków).
 * @param body  Treść zgłoszenia (nie może być pusta).
 */
public record TicketReq( // <-- DODAJEMY SŁOWO KLUCZOWE 'public'
    @NotBlank(message = "Tytuł nie może być pusty.")
    @Size(min = 3, max = 255, message = "Tytuł musi mieć od 3 do 255 znaków.")
    String title,

    @NotBlank(message = "Treść nie może być pusta.")
    String body
) {}
