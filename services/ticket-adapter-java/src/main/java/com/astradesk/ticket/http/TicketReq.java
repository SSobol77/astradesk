// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/http/TicketReq.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/http/TicketReq.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

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
