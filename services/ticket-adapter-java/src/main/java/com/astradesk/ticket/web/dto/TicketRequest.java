// SPDX-License-Identifier: GPL-2.0-only
// Project: AstraDesk
// File: services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/dto/TicketRequest.java
// Website: https://www.astradesk.dev
// Repository: https://github.com/SSobol77/astradesk
//
// Description: Implements AstraDesk functionality for services/ticket-adapter-java/src/main/java/com/astradesk/ticket/web/dto/TicketRequest.java.
//
// Copyright (c) 2026 Siergej Sobolewski
//
// This file is part of AstraDesk.
//
// AstraDesk is licensed under the GNU General Public License version 2 only.
// See the LICENSE file in the project root for the full license text.

package com.astradesk.ticket.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Payload received from the frontend when a ticket should be created.
 */
public class TicketRequest {

    @NotBlank
    @Size(max = 255)
    private String title;

    @NotBlank
    private String body;

    @Size(max = 32)
    private String priority;

    @Size(max = 255)
    private String slackChannel;

    public TicketRequest() {
    }

    public TicketRequest(String title, String body, String priority, String slackChannel) {
        this.title = title;
        this.body = body;
        this.priority = priority;
        this.slackChannel = slackChannel;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getBody() {
        return body;
    }

    public void setBody(String body) {
        this.body = body;
    }

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public String getSlackChannel() {
        return slackChannel;
    }

    public void setSlackChannel(String slackChannel) {
        this.slackChannel = slackChannel;
    }
}
