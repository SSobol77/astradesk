// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/dto/TicketUpdateRequest.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/dto/TicketUpdateRequest.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.web.dto;

import com.astradesk.ticket.domain.TicketStatus;

/**
 * Payload for updating status or metadata on an existing ticket.
 */
public class TicketUpdateRequest {

    private TicketStatus status;

    private String slackChannel;

    public TicketUpdateRequest() {
    }

    public TicketUpdateRequest(TicketStatus status, String slackChannel) {
        this.status = status;
        this.slackChannel = slackChannel;
    }

    public TicketStatus getStatus() {
        return status;
    }

    public void setStatus(TicketStatus status) {
        this.status = status;
    }

    public String getSlackChannel() {
        return slackChannel;
    }

    public void setSlackChannel(String slackChannel) {
        this.slackChannel = slackChannel;
    }
}
