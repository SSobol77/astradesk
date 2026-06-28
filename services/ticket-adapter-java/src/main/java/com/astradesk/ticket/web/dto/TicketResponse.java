// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/dto/TicketResponse.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/dto/TicketResponse.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

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
