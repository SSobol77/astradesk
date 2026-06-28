// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/model/Ticket.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/model/Ticket.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Table;

/**
 * Niemutowalny model danych reprezentujący zgłoszenie (ticket).
 * Użycie `record` (Java 17+) automatycznie generuje konstruktor,
 * gettery, `equals()`, `hashCode()` i `toString()`, co znacząco
 * upraszcza kod i czyni go bezpieczniejszym.
 *
 * @param id      Unikalny identyfikator zgłoszenia (generowany przez bazę danych).
 * @param title   Tytuł zgłoszenia.
 * @param body    Treść zgłoszenia.
 */
@Table("tickets")
public record Ticket(
    @Id Long id,
    String title,
    String body
) {
    /**
     * Dodatkowy konstruktor używany do tworzenia nowych zgłoszeń,
     * gdzie `id` nie jest jeszcze znane (zostanie nadane przez bazę danych).
     */
    public Ticket(String title, String body) {
        this(null, title, body);
    }
}
