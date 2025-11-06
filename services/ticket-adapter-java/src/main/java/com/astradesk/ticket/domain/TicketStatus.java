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
