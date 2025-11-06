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
