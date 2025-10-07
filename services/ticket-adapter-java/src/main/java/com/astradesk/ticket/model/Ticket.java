/*
 * SPDX-License-Identifier: Apache-2.0
 * File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/model/Ticket.java
 * Project: AstraDesk Framework — Ticket Adapter
 * Description: Immutable domain model for a support ticket implemented as a Java record.
 * Author: Siergej Sobolewski
 * Since: 2025-10-07
 *
 * Notes (PL):
 *  - Mapowanie Spring Data Relational (@Table, @Id); współpracuje z R2DBC/JDBC.
 *  - Nowe encje zapisuj z id == null — klucz główny generuje baza danych.
 *  - Rozważ walidację (np. @NotBlank) oraz @Version dla optymistycznego blokowania.
 */

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
