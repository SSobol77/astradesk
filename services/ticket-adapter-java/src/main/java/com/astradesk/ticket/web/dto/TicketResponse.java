package com.astradesk.ticket.web.dto;

import java.time.Instant;

import com.astradesk.ticket.domain.TicketStatus;

/**
 * API response returned to the frontend for ticket queries.
 */
public class TicketResponse {

    private final Long id;
    private final String title;
    private final String body;
    private final TicketStatus status;
    private final String jiraIssueKey;
    private final String slackChannel;
    private final Instant createdAt;
    private final Instant updatedAt;

    public TicketResponse(
        Long id,
        String title,
        String body,
        TicketStatus status,
        String jiraIssueKey,
        String slackChannel,
        Instant createdAt,
        Instant updatedAt
    ) {
        this.id = id;
        this.title = title;
        this.body = body;
        this.status = status;
        this.jiraIssueKey = jiraIssueKey;
        this.slackChannel = slackChannel;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public String getBody() {
        return body;
    }

    public TicketStatus getStatus() {
        return status;
    }

    public String getJiraIssueKey() {
        return jiraIssueKey;
    }

    public String getSlackChannel() {
        return slackChannel;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
