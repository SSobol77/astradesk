// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/domain/TicketStatus.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/domain/TicketStatus.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.domain;

/**
 * Represents the high level lifecycle state of a support ticket.
 *
 * <p>The enum is intentionally small – the service acts as an adapter, so the
 * downstream systems (frontend UI, Jira) can map these values to their own
 * vocabularies. Additional states can be introduced later without breaking
 * persistence because the value is stored as plain text.</p>
 */
public enum TicketStatus {
    NEW,
    IN_PROGRESS,
    RESOLVED,
    CLOSED
}
